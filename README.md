## Chatbot-ML — RAG para documentos legales (Chile)

Proyecto de chatbot que permite **subir archivos PDF** (por ejemplo: *Código del Trabajo*, contratos, anexos) y realizar **consultas basadas únicamente en el contenido de esos documentos** usando técnicas de *Retrieval-Augmented Generation (RAG)*.

La idea es que el sistema sea capaz de **conectar información entre múltiples archivos**, por ejemplo: cargar el PDF del *Código del Trabajo* y un contrato de un empleado, y consultar si el contrato **cumple** con lo indicado por la normativa (según el contenido cargado).

---

## Tecnologías
- **Backend**: FastAPI + Uvicorn
- **RAG / NLP**: LangChain
- **Vector store**: FAISS
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2`
- **LLM local**: Ollama (ej: `llama3`)

---

## Estructura del proyecto
```bash
Chatbot-ML/
├── backend/                         # API + motor RAG (indexación y consultas)
│   ├── main.py                      # FastAPI: endpoints /upload y /ask + CORS
│   ├── rag.py                       # RAG: carga PDF, chunking, FAISS, embeddings, consultas
│   ├── requirements.txt             # Dependencias del backend
│   ├── data/                        # Archivos usados por el backend 
│   └── uploads/                     # Carpeta de subidas 
├── frontend/                        # Interfaz web 
│   ├── index.html                   # UI para cargar PDF y chatear
│   ├── script.js                    # Lógica del frontend (fetch al backend)
│   └── styles.css                   # Estilos
└── .gitignore                       # Archivos excluidos del control de versiones 
```
---

## Requisitos
- **Python 3.11+**
- **Ollama** instalado y funcionando
- Modelo de Ollama descargado (ejemplo con `llama3`)

Para descargar el modelo (ejemplo):

```bash
ollama pull llama3
```
Instalación y ejecución (backend)
Desde la carpeta backend/:
```bash
pip install -r requirements.txt
```
```bash
python -m uvicorn main:app --reload
```
La API quedará disponible en:

http://127.0.0.1:8000
Frontend (Live Server)
Este frontend es estático. Puedes servirlo con la extensión Live Server.

Inicia el backend (si no lo hiciste):

```bash
cd backend
```
```bash
python -m uvicorn main:app --reload
```
En VS Code/Cursor, abre frontend/index.html y usa Open with Live Server.

Live Server normalmente levanta el frontend en un puerto como http://127.0.0.1:5500.
El frontend debe llamar al backend en http://127.0.0.1:8000.

Nota: Como son puertos distintos, se requiere CORS. El backend ya lo permite en backend/main.py.

Endpoints
1) Subir e indexar PDF
POST /upload

Recibe un archivo PDF.
Lo guarda en el backend.
Lo procesa (divide en fragmentos y genera embeddings).
Actualiza/crea el índice vectorial FAISS.

2) Consultar
POST /ask

Body ejemplo:

{
  "question": "¿Qué dice el documento sobre la jornada laboral máxima?"
}
Devuelve:

answer: respuesta basada en el contenido recuperado
sources: contexto recuperado desde los documentos indexados

Notas importantes
El chatbot está pensado para responder basándose en el contenido de los documentos cargados.
Para comparar “contrato vs ley”, se deben cargar ambos documentos (por ejemplo: contrato + Código del Trabajo) para que el sistema pueda recuperar fragmentos relevantes de cada uno.

Se recomienda NO versionar en GitHub:
PDFs (por tamaño y posibles restricciones de uso)
índices de FAISS (se regeneran)
datos cargados/temporales
Para eso se sugiere usar un .gitignore.

Próximos pasos (roadmap)
Soporte para múltiples documentos por caso (contrato + normas + anexos)
Separación por tipo de documento (ley/contrato) y/o por caso/sesión
Respuestas con citas (archivo y página) para trazabilidad
Mejoras en la interfaz (selección de documentos, historial de consultas, etc.)
