import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama

DATA_PATH = "data"
VECTOR_PATH = "vectorstore"

# Embeddings 
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# 🔥 LLM local
llm = ChatOllama(model="llama3")


# ==============================
# PROCESAR PDF
# ==============================
def process_pdf(file_path):
    try:
        print("Cargando PDF...")
        loader = PyPDFLoader(file_path)
        documents = loader.load()

        print("Dividiendo texto...")
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150
        )
        docs = splitter.split_documents(documents)

        print("Generando embeddings...")

        index_file = os.path.join(VECTOR_PATH, "index.faiss")

        if os.path.exists(index_file):
            db = FAISS.load_local(
                VECTOR_PATH,
                embeddings,
                allow_dangerous_deserialization=True
            )
            db.add_documents(docs)
        else:
            db = FAISS.from_documents(docs, embeddings)

        db.save_local(VECTOR_PATH)

        print("PDF procesado correctamente ✅")

    except Exception as e:
        print("ERROR PROCESANDO PDF:", e)
        raise e


# ==============================
# HACER PREGUNTA
# ==============================
def ask_question(question):
    index_file = os.path.join(VECTOR_PATH, "index.faiss")

    if not os.path.exists(index_file):
        return {
            "answer": "No hay documentos cargados.",
            "sources": ""
        }

    db = FAISS.load_local(
        VECTOR_PATH,
        embeddings,
        allow_dangerous_deserialization=True
    )

    retriever = db.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 6,
            "fetch_k": 12,
            "lambda_mult": 0.7
        }
    )

    docs = retriever.invoke(question)

    # ==============================
    # FILTROS
    # ==============================
    keywords = ["jornada", "horas", "semanal", "máxima", "duración"]

    filtered_docs = [
        doc for doc in docs
        if any(k in doc.page_content.lower() for k in keywords)
    ]

    if len(filtered_docs) >= 2:
        docs = filtered_docs

    context = "\n\n".join([doc.page_content for doc in docs])

    # ==============================
    # VALIDACIÓN
    # ==============================
    if not any("jornada" in doc.page_content.lower() for doc in docs):
        return {
            "answer": "No tengo suficiente información.",
            "sources": context
        }

    # ==============================
    # PROMPT
    # ==============================
    prompt = f"""
    Eres un asistente legal experto en legislación chilena.

    REGLAS:
    - Responde SOLO usando el contexto.
    - NO inventes información.
    - NO completes con conocimiento externo.
    - Si hay varias normas, prioriza la que define la regla general.
    - Si no estás seguro, responde: "No tengo suficiente información".

    Contexto:
    {context}

    Pregunta:
    {question}

    Respuesta clara y directa:
    """

    response = llm.invoke(prompt)

    return {
        "answer": response.content.strip(),
        "sources": context
    }