from __future__ import annotations

import os
import shutil
from typing import Any, List, Optional

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(_BACKEND_DIR, "data")
UPLOADS_PATH = os.path.join(_BACKEND_DIR, "uploads")
VECTOR_USER_PATH = os.path.join(_BACKEND_DIR, "vectorstore_user")
VECTOR_KB_PATH = os.path.join(_BACKEND_DIR, "vectorstore_kb")

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}

RAG_USER_TOP_K = int(os.environ.get("RAG_USER_TOP_K", "6"))
RAG_KB_TOP_K = int(os.environ.get("RAG_KB_TOP_K", "4"))
RAG_USER_FETCH_K = int(os.environ.get("RAG_USER_FETCH_K", "40"))
RAG_SNIPPET_LEN = int(os.environ.get("RAG_SNIPPET_LEN", "720"))
RAG_NUM_CTX = int(os.environ.get("RAG_NUM_CTX", "8192"))
RAG_NUM_PREDICT = int(os.environ.get("RAG_NUM_PREDICT", "900"))
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

llm = ChatOllama(
    model=OLLAMA_MODEL,
    num_ctx=RAG_NUM_CTX,
    num_predict=RAG_NUM_PREDICT,
    temperature=float(os.environ.get("RAG_TEMPERATURE", "0.15")),
)

_VECTORSTORE_CACHE: dict[str, tuple[float, Any]] = {}


def _load_raw_documents(file_path: str):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return PyPDFLoader(file_path).load()
    if ext in (".txt", ".md"):
        return TextLoader(file_path, encoding="utf-8").load()
    raise ValueError(f"Formato no soportado: {ext}")


def load_and_split(file_path: str):
    documents = _load_raw_documents(file_path)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )
    return splitter.split_documents(documents)


def _tag_documents(docs, collection: str, file_path: Optional[str] = None):
    base = os.path.basename(file_path) if file_path else None
    for d in docs:
        d.metadata["collection"] = collection
        if base:
            d.metadata["filename"] = base
    return docs


def _doc_filename_key(doc) -> str:
    fn = doc.metadata.get("filename")
    if fn:
        return str(fn).lower()
    src = doc.metadata.get("source") or ""
    return os.path.basename(str(src)).lower()


def _persist_add_documents(docs, vector_path: str):
    os.makedirs(vector_path, exist_ok=True)
    index_file = os.path.join(vector_path, "index.faiss")
    if os.path.exists(index_file):
        db = FAISS.load_local(
            vector_path,
            embeddings,
            allow_dangerous_deserialization=True
        )
        db.add_documents(docs)
    else:
        db = FAISS.from_documents(docs, embeddings)
    db.save_local(vector_path)


def process_document(file_path: str):
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Solo se indexan: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

        print(f"Cargando {ext} (usuario)...")
        docs = _tag_documents(load_and_split(file_path), "user", file_path)
        print("Generando embeddings (usuario)...")
        _persist_add_documents(docs, VECTOR_USER_PATH)
        print("Documento de usuario indexado ✅")
    except Exception as e:
        print("ERROR PROCESANDO DOCUMENTO:", e)
        raise e


def process_pdf(file_path: str):
    return process_document(file_path)


def _rebuild_folder_vector_index(source_dir: str, vector_path: str, collection: str) -> int:
    if os.path.isdir(vector_path):
        shutil.rmtree(vector_path)
    os.makedirs(vector_path, exist_ok=True)

    all_chunks = []
    if not os.path.isdir(source_dir):
        return 0

    for name in sorted(os.listdir(source_dir)):
        path = os.path.join(source_dir, name)
        if not os.path.isfile(path):
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue
        try:
            docs = _tag_documents(load_and_split(path), collection, path)
            all_chunks.extend(docs)
        except Exception as e:
            print(f"Omitido {name}: {e}")

    if not all_chunks:
        return 0

    db = FAISS.from_documents(all_chunks, embeddings)
    db.save_local(vector_path)
    return len(all_chunks)


def rebuild_knowledge_index() -> int:
    return _rebuild_folder_vector_index(UPLOADS_PATH, VECTOR_KB_PATH, "kb")


def rebuild_user_index() -> int:
    return _rebuild_folder_vector_index(DATA_PATH, VECTOR_USER_PATH, "user")


def rebuild_all_indices():
    kb_n = rebuild_knowledge_index()
    user_n = rebuild_user_index()
    return kb_n, user_n


def _load_vectorstore(vector_path: str):
    index_file = os.path.join(vector_path, "index.faiss")
    if not os.path.exists(index_file):
        _VECTORSTORE_CACHE.pop(vector_path, None)
        return None
    mtime = os.path.getmtime(index_file)
    cached = _VECTORSTORE_CACHE.get(vector_path)
    if cached and cached[0] == mtime:
        return cached[1]
    db = FAISS.load_local(
        vector_path,
        embeddings,
        allow_dangerous_deserialization=True
    )
    _VECTORSTORE_CACHE[vector_path] = (mtime, db)
    return db


def _retrieve_user_docs_filtered(
    db_u,
    query_embedding: List[float],
    user_documents: Optional[List[str]],
):
    if not db_u:
        return []

    if user_documents is not None and len(user_documents) == 0:
        return []

    fetch_k = max(RAG_USER_FETCH_K, RAG_USER_TOP_K * 6)
    raw = db_u.similarity_search_by_vector(query_embedding, k=fetch_k)

    if user_documents is None:
        return raw[: RAG_USER_TOP_K]

    allow = {str(n).strip().lower() for n in user_documents if str(n).strip()}
    if not allow:
        return []

    filtered = [d for d in raw if _doc_filename_key(d) in allow]
    return filtered[: RAG_USER_TOP_K]


def ask_question(question, user_documents: Optional[List[str]] = None):
    db_u = _load_vectorstore(VECTOR_USER_PATH)
    db_k = _load_vectorstore(VECTOR_KB_PATH)

    if not db_u and not db_k:
        return {
            "answer": (
                "No hay índice disponible. Sube documentos en la app (carpeta data) "
                "y/o coloca PDF/TXT/MD en la base de conocimiento del servidor (carpeta uploads) "
                "y ejecuta reindexado si hace falta."
            ),
            "sources": "",
        }

    query_embedding = embeddings.embed_query(question)

    user_docs = _retrieve_user_docs_filtered(db_u, query_embedding, user_documents)
    kb_docs = (
        db_k.similarity_search_by_vector(query_embedding, k=RAG_KB_TOP_K)
        if db_k
        else []
    )

    if user_documents and len(user_documents) > 0 and db_u and not user_docs:
        return {
            "answer": (
                "No encontré fragmentos relevantes en los documentos que seleccionaste. "
                "Prueba con otra pregunta, selecciona más archivos o verifica que estén indexados."
            ),
            "sources": "",
        }

    if not user_docs and not kb_docs:
        return {
            "answer": "No encontré fragmentos relevantes en los documentos indexados.",
            "sources": "",
        }

    def _snippet(doc, label_prefix: str, max_len: int = RAG_SNIPPET_LEN):
        text = doc.page_content.strip()
        if len(text) > max_len:
            text = text[: max_len - 1] + "…"
        src = doc.metadata.get("source") or ""
        base = os.path.basename(src) if src else "documento"
        return f"[{label_prefix}: {base}]\n{text}"

    parts = []
    if user_docs:
        parts.append("— Documentos del usuario (contratos, archivos subidos) —\n\n")
        parts.append("\n\n---\n\n".join(_snippet(d, "Usuario") for d in user_docs))
    if kb_docs:
        parts.append("\n\n— Base de conocimiento (normativa y referencia) —\n\n")
        parts.append("\n\n---\n\n".join(_snippet(d, "Base") for d in kb_docs))

    context = "".join(parts)

    if len(context.strip()) < 30:
        return {
            "answer": "No tengo suficiente información en los documentos para responder con seguridad.",
            "sources": context,
        }

    scope_user = ""
    if user_documents and len(user_documents) > 0:
        scope_user = (
            f"\nNota: el usuario restringió la consulta a estos archivos propios: "
            f"{', '.join(user_documents)}. No asumas contenido de otros documentos suyos.\n"
        )

    prompt = f"""Asistente de documentos legales. Responde en español, con precisión y brevedad.
{scope_user}
Prioridad: (1) hechos del contrato del usuario con "Documentos del usuario"; (2) normativa con "Base de conocimiento" sin contradecir el texto del usuario si es explícito.
Reglas: solo contexto dado; no inventes; si falta información, dilo; aviso no sustituye abogado.

Contexto:
{context}

Pregunta: {question}

Respuesta directa:
"""

    response = llm.invoke(prompt)

    return {
        "answer": response.content.strip(),
        "sources": context,
    }
