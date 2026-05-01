const API_URL = "http://127.0.0.1:8000";

// 🔹 ELEMENTOS
const chat = document.getElementById("chat");
const input = document.getElementById("input");
const fileInput = document.getElementById("fileInput");
const dropzone = document.getElementById("dropzone");

// -----------------------------
// 💬 AGREGAR MENSAJE AL CHAT
// -----------------------------
function addMessage(text, sender = "bot") {
    const msg = document.createElement("div");
    msg.className = `msg msg--${sender}`;

    msg.innerHTML = `
        <div class="msg__bubble">
            <span class="msg__label">${sender === "user" ? "Tú" : "Bot"}</span>
            ${text}
        </div>
    `;

    chat.appendChild(msg);
    chat.scrollTop = chat.scrollHeight;
}

// -----------------------------
// 📄 SUBIR ARCHIVO
// -----------------------------
async function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    addMessage("Subiendo archivo...", "bot");

    try {
        const res = await fetch(`${API_URL}/upload`, {
            method: "POST",
            body: formData
        });

        const data = await res.json();

        addMessage("✅ " + data.message, "bot");

    } catch (err) {
        console.error(err);
        addMessage("❌ Error al subir archivo", "bot");
    }
}

// Click en zona
dropzone.addEventListener("click", () => fileInput.click());

// Cambio de archivo
fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (file) uploadFile(file);
});

// Drag & drop
dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("upload-panel--drag");
});

dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("upload-panel--drag");
});

dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("upload-panel--drag");

    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
});

// -----------------------------
// 🤖 HACER PREGUNTA
// -----------------------------
async function enviar() {
    const question = input.value.trim();
    if (!question) return;

    addMessage(question, "user");
    input.value = "";

    addMessage("Pensando...", "bot");

    try {
        const res = await fetch(`${API_URL}/ask`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ question })
        });

        const data = await res.json();

        // eliminar "Pensando..."
        chat.removeChild(chat.lastChild);

        addMessage(data.answer, "bot");

        // 🔥 EXTRA: mostrar fuentes (te sube nota)
        if (data.sources) {
            addMessage("📚 Contexto usado:\n" + data.sources, "bot");
        }

    } catch (err) {
        console.error(err);
        addMessage("❌ Error al consultar", "bot");
    }
}

// Enter para enviar
input.addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
        enviar();
    }
});