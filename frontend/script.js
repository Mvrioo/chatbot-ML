const API_URL = "http://127.0.0.1:8000";

const chat = document.getElementById("chat");
const input = document.getElementById("input");
const fileInput = document.getElementById("fileInput");
const dropzone = document.getElementById("dropzone");
const fileList = document.getElementById("fileList");
const fileListEmpty = document.getElementById("fileListEmpty");
const refreshFiles = document.getElementById("refreshFiles");
const uploadStatus = document.getElementById("uploadStatus");
const previewModal = document.getElementById("previewModal");
const previewTitle = document.getElementById("previewTitle");
const previewFrame = document.getElementById("previewFrame");
const previewFallback = document.getElementById("previewFallback");
const previewDownload = document.getElementById("previewDownload");
const previewBackdrop = document.getElementById("previewBackdrop");
const previewClose = document.getElementById("previewClose");
const fileSelectionToolbar = document.getElementById("fileSelectionToolbar");
const selectAllUserDocs = document.getElementById("selectAllUserDocs");
const selectNoneUserDocs = document.getElementById("selectNoneUserDocs");

let knownIndexable = new Set();
const selectedUserDocs = new Set();

function updateSelectionState(files) {
    const indexableNames = files.filter((f) => f.indexable).map((f) => f.name);
    const incoming = new Set(indexableNames);
    for (const n of indexableNames) {
        if (!knownIndexable.has(n)) {
            selectedUserDocs.add(n);
        }
    }
    for (const x of [...selectedUserDocs]) {
        if (!incoming.has(x)) {
            selectedUserDocs.delete(x);
        }
    }
    knownIndexable = incoming;
}

function formatBytes(n) {
    if (n < 1024) return n + " B";
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
    return (n / (1024 * 1024)).toFixed(1) + " MB";
}

function fileIcon(name) {
    const ext = name.split(".").pop().toLowerCase();
    if (ext === "pdf") return "📄";
    if (ext === "md") return "📝";
    return "📃";
}

function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}

function escapeAttr(s) {
    return String(s)
        .replace(/&/g, "&amp;")
        .replace(/"/g, "&quot;")
        .replace(/</g, "&lt;");
}

function parseErrorDetail(data) {
    if (!data || data.detail === undefined) return null;
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
        return data.detail.map((d) => (typeof d === "object" && d.msg ? d.msg : String(d))).join("; ");
    }
    return String(data.detail);
}

async function loadFileList() {
    fileListEmpty.hidden = false;
    fileListEmpty.textContent = "Cargando…";
    fileList.innerHTML = "";

    try {
        const res = await fetch(`${API_URL}/files`);
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        const files = data.files || [];

        if (files.length === 0) {
            fileSelectionToolbar.hidden = true;
            knownIndexable = new Set();
            selectedUserDocs.clear();
            fileListEmpty.textContent =
                "No hay archivos tuyos aún. Sube contratos o documentos (PDF, TXT, MD). Si en el servidor hay PDF/TXT/MD en uploads/, el modelo también los usa como base de conocimiento.";
            return;
        }

        updateSelectionState(files);

        const indexableCount = files.filter((f) => f.indexable).length;
        fileSelectionToolbar.hidden = indexableCount === 0;

        fileListEmpty.hidden = true;

        for (const f of files) {
            const checked = f.indexable && selectedUserDocs.has(f.name);
            const li = document.createElement("li");
            li.className = "file-list__item" + (f.indexable && !checked ? " file-list__item--inactive" : "");
            const checkDisabled = !f.indexable ? " disabled" : "";
            const checkChecked = checked ? " checked" : "";
            const checkTitle = f.indexable ? "Incluir en la consulta" : "No indexado (solo PDF, TXT, MD)";
            li.innerHTML = `
                <label class="file-list__select" title="${escapeAttr(checkTitle)}">
                    <input type="checkbox" class="file-list__check" value="${escapeAttr(f.name)}"${checkDisabled}${checkChecked} />
                </label>
                <span class="file-list__icon" aria-hidden="true">${fileIcon(f.name)}</span>
                <div class="file-list__main">
                    <span class="file-list__name">${escapeHtml(f.name)}</span>
                    <span class="file-list__meta">${formatBytes(f.size)}${
                f.indexable ? "" : " · no indexado"
            }</span>
                </div>
                <div class="file-list__actions">
                    <button type="button" class="file-list__action" data-preview="${escapeAttr(
                        f.name
                    )}" title="Vista previa">👁</button>
                    <a class="file-list__action" href="${API_URL}/data-files/${encodeURIComponent(
                f.name
            )}" download="${escapeAttr(f.name)}" title="Descargar">⬇</a>
                    <button type="button" class="file-list__action file-list__action--danger" data-delete="${escapeAttr(
                        f.name
                    )}" title="Eliminar">🗑</button>
                </div>
            `;
            fileList.appendChild(li);
        }

        fileList.querySelectorAll("input.file-list__check:not(:disabled)").forEach((inp) => {
            inp.addEventListener("change", () => {
                if (inp.checked) {
                    selectedUserDocs.add(inp.value);
                } else {
                    selectedUserDocs.delete(inp.value);
                }
                const row = inp.closest(".file-list__item");
                if (row) {
                    row.classList.toggle("file-list__item--inactive", !inp.checked);
                }
            });
        });

        fileList.querySelectorAll("[data-preview]").forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                openPreview(btn.getAttribute("data-preview"));
            });
        });
        fileList.querySelectorAll("[data-delete]").forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                deleteFile(btn.getAttribute("data-delete"));
            });
        });
    } catch (e) {
        console.error(e);
        fileListEmpty.hidden = false;
        fileListEmpty.textContent =
            "No se pudo cargar la lista. ¿Está el backend activo en " + API_URL + "?";
    }
}

function openPreview(filename) {
    const url = `${API_URL}/data-files/${encodeURIComponent(filename)}`;
    const ext = filename.split(".").pop().toLowerCase();
    previewTitle.textContent = filename;
    previewModal.hidden = false;
    document.body.classList.add("is-modal-open");

    if (ext === "pdf" || ext === "txt" || ext === "md") {
        previewFrame.hidden = false;
        previewFallback.hidden = true;
        previewFrame.src = url;
    } else {
        previewFrame.hidden = true;
        previewFallback.hidden = false;
        previewDownload.href = url;
    }
}

function closePreview() {
    previewModal.hidden = true;
    document.body.classList.remove("is-modal-open");
    previewFrame.removeAttribute("src");
}

async function deleteFile(filename) {
    if (!confirm(`¿Eliminar «${filename}» del servidor y actualizar el índice?`)) return;

    try {
        const res = await fetch(`${API_URL}/files/${encodeURIComponent(filename)}`, {
            method: "DELETE",
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(parseErrorDetail(data) || res.statusText);
        addMessage("🗑 " + (data.message || "Archivo eliminado"), "bot");
        await loadFileList();
    } catch (e) {
        console.error(e);
        addMessage("❌ No se pudo eliminar: " + (e.message || "error"), "bot");
    }
}

function addMessage(text, sender = "bot") {
    const msg = document.createElement("div");
    msg.className = `msg msg--${sender}`;
    const bubble = document.createElement("div");
    bubble.className = "msg__bubble";
    const label = document.createElement("span");
    label.className = "msg__label";
    label.textContent = sender === "user" ? "Tú" : "Bot";
    bubble.appendChild(label);
    bubble.appendChild(document.createTextNode(text));
    msg.appendChild(bubble);
    chat.appendChild(msg);
    chat.scrollTop = chat.scrollHeight;
}

function addUploadStatusItem(text, ok) {
    uploadStatus.hidden = false;
    const li = document.createElement("li");
    li.className = ok ? "ok" : "err";
    li.textContent = text;
    uploadStatus.appendChild(li);
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch(`${API_URL}/upload`, {
            method: "POST",
            body: formData,
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            throw new Error(parseErrorDetail(data) || res.statusText || "Error al subir");
        }
        addUploadStatusItem(`✅ ${data.message || file.name}`, true);
        await loadFileList();
    } catch (err) {
        console.error(err);
        addUploadStatusItem(`❌ ${file.name}: ${err.message}`, false);
        addMessage("❌ " + file.name + ": " + err.message, "bot");
    }
}

function uploadFilesList(files) {
    const list = Array.from(files || []).filter(Boolean);
    if (!list.length) return;

    uploadStatus.innerHTML = "";
    uploadStatus.hidden = false;
    list.forEach((f) => uploadFile(f));
    fileInput.value = "";
}

dropzone.addEventListener("click", (e) => {
    if (e.target.closest(".file-list__action")) return;
    fileInput.click();
});

fileInput.addEventListener("change", () => {
    uploadFilesList(fileInput.files);
});

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
    uploadFilesList(e.dataTransfer.files);
});

refreshFiles.addEventListener("click", loadFileList);
previewClose.addEventListener("click", closePreview);
previewBackdrop.addEventListener("click", closePreview);

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !previewModal.hidden) closePreview();
});

selectAllUserDocs.addEventListener("click", () => {
    fileList.querySelectorAll("input.file-list__check:not(:disabled)").forEach((inp) => {
        inp.checked = true;
        selectedUserDocs.add(inp.value);
        const row = inp.closest(".file-list__item");
        if (row) row.classList.remove("file-list__item--inactive");
    });
});

selectNoneUserDocs.addEventListener("click", () => {
    fileList.querySelectorAll("input.file-list__check:not(:disabled)").forEach((inp) => {
        inp.checked = false;
        selectedUserDocs.delete(inp.value);
        const row = inp.closest(".file-list__item");
        if (row) row.classList.add("file-list__item--inactive");
    });
});

document.addEventListener("DOMContentLoaded", loadFileList);

async function enviar() {
    const question = input.value.trim();
    if (!question) return;

    const checks = fileList.querySelectorAll("input.file-list__check:not(:disabled)");
    if (checks.length > 0) {
        let nSelected = 0;
        checks.forEach((inp) => {
            if (inp.checked) nSelected++;
        });
        if (nSelected === 0) {
            addMessage(
                "Selecciona al menos un documento en el panel izquierdo (casillas) para acotar la consulta.",
                "bot"
            );
            return;
        }
    }

    addMessage(question, "user");
    input.value = "";

    const thinking = document.createElement("div");
    thinking.className = "msg msg--bot";
    thinking.innerHTML = `
        <div class="msg__bubble">
            <span class="msg__label">Bot</span>
            Pensando…
        </div>
    `;
    chat.appendChild(thinking);
    chat.scrollTop = chat.scrollHeight;

    const payload = { question };
    if (checks.length > 0) {
        const picked = [];
        checks.forEach((inp) => {
            if (inp.checked) picked.push(inp.value);
        });
        payload.user_documents = picked;
    }

    try {
        const res = await fetch(`${API_URL}/ask`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
        });

        const data = await res.json();
        thinking.remove();

        addMessage(data.answer, "bot");

        if (data.sources) {
            addMessage("📚 Contexto usado:\n" + data.sources, "bot");
        }
    } catch (err) {
        console.error(err);
        thinking.remove();
        addMessage("❌ Error al consultar", "bot");
    }
}

input.addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
        enviar();
    }
});
