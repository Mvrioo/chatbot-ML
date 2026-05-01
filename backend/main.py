from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os

from rag import process_pdf, ask_question

app = FastAPI()

# 🔥 Permitir conexión con frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = "data"

os.makedirs(DATA_PATH, exist_ok=True)


# ==============================
# 📥 SUBIR ARCHIVO
# ==============================
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(DATA_PATH, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    process_pdf(file_path)

    return {"message": "Archivo subido e indexado"}


# ==============================
# 🤖 PREGUNTAR
# ==============================
@app.post("/ask")
async def ask(data: dict):
    question = data.get("question")

    result = ask_question(question)

    return result