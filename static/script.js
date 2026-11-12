const qrInput = document.getElementById("qrInput");
const scanBtn = document.getElementById("scanBtn");
const message = document.getElementById("message");
const selectedFile = document.getElementById("selectedFile");
const dropZone = document.getElementById("dropZone");
const resultSection = document.getElementById("resultSection");

qrInput.addEventListener("change", () => {
    const file = qrInput.files[0];
    selectedFile.hidden = !file;
    selectedFile.textContent = file ? `Selected: ${file.name}` : "";
    message.textContent = "";
});

["dragenter", "dragover"].forEach(type => {
    dropZone.addEventListener(type, event => {
        event.preventDefault();
        dropZone.classList.add("drag-over");
    });
});
["dragleave", "drop"].forEach(type => {
    dropZone.addEventListener(type, event => {
        event.preventDefault();
        dropZone.classList.remove("drag-over");
    });
});
dropZone.addEventListener("drop", event => {
    const file = event.dataTransfer.files[0];
    if (file) {
        const transfer = new DataTransfer();
        transfer.items.add(file);
        qrInput.files = transfer.files;
        qrInput.dispatchEvent(new Event("change"));
    }
});

scanBtn.addEventListener("click", async () => {
    const file = qrInput.files[0];
    message.textContent = "";
    if (!file) {
        message.textContent = "Please choose a QR image first.";
        return;
    }
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
        message.textContent = "Please choose a PNG, JPG, or WEBP image.";
        return;
    }
    if (file.size > 5 * 1024 * 1024) {
        message.textContent = "The image must be smaller than 5 MB.";
        return;
    }
    if (typeof jsQR !== "function") {
        message.textContent = "QR reading library did not load. Check your internet connection and refresh.";
        return;
    }

    scanBtn.disabled = true;
    scanBtn.querySelector("span").textContent = "Scanning...";
    try {
        const imageData = await loadImageData(file);
        const qr = jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: "attemptBoth"
        });
        if (!qr) throw new Error("No QR code was found. Try a sharper, well-lit image.");

        const response = await fetch("/api/analyze", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({content: qr.data})
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "The server could not analyze this QR code.");

        showResult(data, qr.data);
        await Promise.all([loadHistory(), loadStats()]);
    } catch (error) {
        message.textContent = error.message || "Something went wrong while scanning.";
    } finally {
        scanBtn.disabled = false;
        scanBtn.querySelector("span").textContent = "Scan QR code";
    }
});

function loadImageData(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = () => reject(new Error("Could not read this image file."));
        reader.onload = () => {
            const image = new Image();
            image.onerror = () => reject(new Error("Could not open this image."));
            image.onload = () => {
                const maxSide = 1800;
                const scale = Math.min(1, maxSide / Math.max(image.naturalWidth, image.naturalHeight));
                const canvas = document.createElement("canvas");
                canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
                canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
                const context = canvas.getContext("2d", {willReadFrequently: true});
                context.drawImage(image, 0, 0, canvas.width, canvas.height);
                resolve(context.getImageData(0, 0, canvas.width, canvas.height));
                URL.revokeObjectURL(image.src);
            };
            image.src = URL.createObjectURL(file);
        };
        reader.readAsArrayBuffer(file);
    });
}

function showResult(data, originalContent) {
    resultSection.hidden = false;
    document.getElementById("riskScore").textContent = data.risk_score;
    document.getElementById("resultTitle").textContent = data.is_url ? (data.host || "URL analyzed") : "Text QR code analyzed";
    document.getElementById("resultSummary").textContent = data.summary;
    document.getElementById("destination").textContent = originalContent;

    const badge = document.getElementById("riskBadge");
    badge.textContent = `${data.risk_level.toUpperCase()} RISK`;
    badge.className = "result-badge " + data.risk_level.toLowerCase();

    const ring = document.getElementById("scoreRing");
    const colors = {Low: "var(--green)", Medium: "var(--yellow)", High: "var(--red)", Unknown: "var(--muted)"};
    ring.style.background = `conic-gradient(${colors[data.risk_level] || colors.Unknown} ${data.risk_score * 3.6}deg, rgba(130,155,184,.13) 0deg)`;

    const list = document.getElementById("findingsList");
    list.replaceChildren();
    data.findings.forEach(item => {
        const li = document.createElement("li");
        li.textContent = item;
        list.appendChild(li);
    });
    resultSection.scrollIntoView({behavior: "smooth", block: "start"});
}

async function loadHistory() {
    const response = await fetch("/api/history");
    const items = await response.json();
    const container = document.getElementById("historyList");
    container.replaceChildren();
    if (!items.length) {
        const empty = document.createElement("div");
        empty.className = "empty-state";
        empty.textContent = "No scans yet. Your recent checks will appear here.";
        container.appendChild(empty);
        return;
    }
    items.forEach(item => {
        const row = document.createElement("div");
        row.className = "history-item";
        const content = document.createElement("div");
        content.className = "history-content";
        content.textContent = item.content;
        content.title = item.content;
        const date = document.createElement("div");
        date.className = "history-date";
        date.textContent = new Date(item.scanned_at).toLocaleString();
        const risk = document.createElement("div");
        risk.className = "history-risk " + item.risk_level.toLowerCase();
        risk.textContent = `${item.risk_level.toUpperCase()} · ${item.risk_score}/100`;
        row.append(content, date, risk);
        container.appendChild(row);
    });
}

async function loadStats() {
    const response = await fetch("/api/stats");
    const stats = await response.json();
    document.getElementById("totalScans").textContent = stats.total;
    document.getElementById("highScans").textContent = stats.high;
}

document.getElementById("clearHistory").addEventListener("click", async () => {
    if (!confirm("Are you sure you want to clear all scan history?")) return;
    await fetch("/api/history/clear", {method: "POST"});
    await Promise.all([loadHistory(), loadStats()]);
});

loadHistory();
loadStats();
