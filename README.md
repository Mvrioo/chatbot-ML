# Chatbot-ML — RAG sobre documentos legales

Chat web con **FastAPI** + **LangChain** + **FAISS** que permite subir **PDF, TXT y MD**, indexarlos y hacer **preguntas** usando solo el contenido recuperado más un **LLM local (Ollama)**.

Hay dos orígenes de documentos:

| Ubicación | Uso |
|-----------|-----|
| `backend/data/` | Archivos que **sube el usuario** desde el frontend. Aparecen en el panel izquierdo (vista previa, selección para consultar). |
| `backend/uploads/` | **Base de conocimiento** en el servidor (normativa, manuales). No se listan en el UI; se indexan y el modelo las usa como apoyo. |

El chat **prioriza** los documentos del usuario; la base en `uploads/` aporta contexto normativo sin contradecir el texto del contrato cuando es explícito.

---

## Tecnologías

- **Backend:** FastAPI, Uvicorn  
- **RAG:** LangChain (PyPDF / TextLoader, chunking, FAISS)  
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2`  
- **LLM:** Ollama (por defecto `llama3`)  
- **Frontend:** HTML estático + JS (sin framework)

---

## Estructura del proyecto

```text
chatbot-ML/
├── backend/
│   ├── main.py              # API REST + CORS + archivos estáticos /data-files
│   ├── rag.py               # Índices, embeddings, consulta RAG
│   ├── requirements.txt
│   ├── data/                # Documentos del usuario (no versionar)
│   ├── uploads/             # Base de conocimiento (no versionar)
│   ├── vectorstore_user/    # Índice FAISS usuario (no versionar)
│   └── vectorstore_kb/      # Índice FAISS base (no versionar)
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── styles.css
├── .gitignore
└── README.md
```

---

## Requisitos previos

- **Python 3.10+** (recomendado 3.11+)
- **Ollama** instalado: [https://ollama.com](https://ollama.com)
- Navegador moderno

---

## Paso a paso: poner en marcha el proyecto

### 1. Clonar el repositorio

```bash
git clone <url-de-tu-repo>
cd <nombre-de-la-carpeta-del-repo>
```

### 2. Crear y activar un entorno virtual (recomendado)

**Windows (PowerShell):**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias del backend

Con el entorno virtual activado y estando en `backend/`:

```bash
pip install -r requirements.txt
```

La primera ejecución puede descargar el modelo de embeddings desde Hugging Face (requiere red).

### 4. Instalar y preparar Ollama

Instala Ollama según tu sistema. Luego descarga un modelo (el código usa por defecto `llama3`):

```bash
ollama pull llama3
```

Para usar otro modelo, define la variable de entorno `OLLAMA_MODEL` (ver sección **Variables de entorno**).

Asegúrate de que el servicio de Ollama esté en ejecución antes de hacer preguntas.

### 5. (Opcional) Base de conocimiento

Coloca PDF/TXT/MD en `backend/uploads/` (por ejemplo el Código del Trabajo). Luego, con el backend ya levantado, reconstruye índices:

```bash
curl -X POST http://127.0.0.1:8000/reindex
```

O usa Postman / Thunder Client con `POST http://127.0.0.1:8000/reindex`.

### 6. Arrancar el backend

Desde `backend/` (con venv activado):

```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Documentación interactiva: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 7. Abrir el frontend

El frontend es estático. Opciones:

- **VS Code / Cursor:** extensión *Live Server* → abrir `frontend/index.html` con “Open with Live Server”.
- **Python rápido** (desde la raíz `chatbot-ML/`):

  ```bash
  cd frontend
  python -m http.server 5500
  ```

  Luego abre [http://127.0.0.1:5500](http://127.0.0.1:5500).

El `script.js` apunta por defecto a `http://127.0.0.1:8000`. Si cambias el puerto del API, edita `API_URL` en `frontend/script.js`.

**CORS:** el backend ya permite orígenes `*` para desarrollo.

---

## Uso de la interfaz

1. Sube archivos (arrastrar o clic) → se guardan en `data/` e indexan en el vectorstore de usuario.
2. En el panel izquierdo, **marca los archivos** que quieres incluir en cada pregunta (obligatorio si hay archivos indexables).
3. Escribe la pregunta y envía. Opcionalmente revisa el bloque “Contexto usado” en el chat.

---

## API (resumen)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/files` | Lista archivos en `data/`. |
| `POST` | `/upload` | Sube un archivo (multipart `file`). |
| `DELETE` | `/files/{filename}` | Elimina un archivo de `data/` y reconstruye índices. |
| `POST` | `/ask` | Cuerpo JSON: `question` (string), opcional `user_documents` (lista de nombres de archivo seleccionados). |
| `POST` | `/reindex` | Reconstruye ambos índices desde `uploads/` + `data/`. |

**Ejemplo `POST /ask`:**

```json
{
  "question": "¿Qué plazo de aviso indica el contrato?",
  "user_documents": ["contrato.pdf"]
}
```

Si no envías `user_documents` y no hay casillas en el UI, el comportamiento legacy es considerar todos los documentos de usuario en el índice; el frontend actual envía la lista cuando hay archivos indexables marcados.

---

## Variables de entorno (rendimiento / modelo)

Definir antes de arrancar Uvicorn (opcional):

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `OLLAMA_MODEL` | Modelo en Ollama | `llama3` |
| `RAG_NUM_CTX` | Contexto máximo del modelo | `8192` |
| `RAG_NUM_PREDICT` | Tope de tokens de salida | `900` |
| `RAG_USER_TOP_K` | Chunks usuario a enviar al LLM | `6` |
| `RAG_KB_TOP_K` | Chunks base de conocimiento | `4` |
| `RAG_SNIPPET_LEN` | Caracteres máx. por fragmento en el prompt | `720` |
| `RAG_TEMPERATURE` | Temperatura del LLM | `0.15` |

---

## Notas importantes

- Las respuestas son **orientativas**; no sustituyen asesoría legal. Pueden fallar citas o matices: contrastar siempre con los PDF originales.
- No subas datos personales sensibles sin evaluar riesgo y cumplimiento.
- `.gitignore` excluye `data/`, `uploads/`, vectorstores y entornos virtuales: cada entorno regenera índices desde los archivos locales.

---

## Licencia

Indica aquí la licencia del proyecto si la defines en el repo.
