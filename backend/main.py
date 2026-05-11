from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import shutil
import os

from rag import (
    ask_question,
    process_document,
    rebuild_all_indices,
    SUPPORTED_EXTENSIONS,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_BACKEND_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(_BACKEND_ROOT, "data")
UPLOADS_PATH = os.path.join(_BACKEND_ROOT, "uploads")

os.makedirs(DATA_PATH, exist_ok=True)
os.makedirs(UPLOADS_PATH, exist_ok=True)


def _safe_filename(name: str) -> str:
    base = os.path.basename(name or "")
    if not base or base in (".", "..") or os.path.sep in name.replace("\\", "/"):
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")
    return base


@app.get("/files")
async def list_files():
    if not os.path.isdir(DATA_PATH):
        return {"files": []}

    files = []
    for name in sorted(os.listdir(DATA_PATH)):
        path = os.path.join(DATA_PATH, name)
        if not os.path.isfile(path):
            continue
        stat = os.stat(path)
        ext = os.path.splitext(name)[1].lower()
        files.append({
            "name": name,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "indexable": ext in SUPPORTED_EXTENSIONS,
        })
    return {"files": files}


@app.delete("/files/{filename}")
async def delete_file(filename: str):
    safe = _safe_filename(filename)
    path = os.path.join(DATA_PATH, safe)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    os.remove(path)
    rebuild_all_indices()
    return {"message": f"«{safe}» eliminado. Índices (usuario + base) actualizados."}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    safe = _safe_filename(file.filename or "")
    ext = os.path.splitext(safe)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no permitido. Usa: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    file_path = os.path.join(DATA_PATH, safe)
    replacing = os.path.isfile(file_path)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        if replacing:
            rebuild_all_indices()
        else:
            process_document(file_path)
    except Exception as e:
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        raise HTTPException(status_code=500, detail=f"No se pudo indexar el archivo: {e!s}") from e

    return {"message": f"«{safe}» subido e indexado"}


@app.post("/ask")
async def ask(data: dict):
    question = data.get("question")
    raw_docs = data.get("user_documents")
    user_documents = None
    if raw_docs is not None:
        if not isinstance(raw_docs, list):
            raise HTTPException(
                status_code=400,
                detail="user_documents debe ser una lista de nombres de archivo o null.",
            )
        user_documents = [str(x) for x in raw_docs]
    result = ask_question(question, user_documents=user_documents)
    return result


@app.post("/reindex")
async def reindex():
    kb_n, user_n = rebuild_all_indices()
    return {
        "message": "Índices reconstruidos.",
        "knowledge_chunks": kb_n,
        "user_chunks": user_n,
    }


app.mount("/data-files", StaticFiles(directory=DATA_PATH), name="data_files")