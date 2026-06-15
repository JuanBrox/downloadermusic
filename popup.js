const API_URL = "http://localhost:8502/api/add_url";
const YT_RE   = /youtube\.com\/watch\?.*v=([\w-]+)/;

// Obtener la pestaña activa
chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
  const content = document.getElementById("main-content");

  if (!tab || !YT_RE.test(tab.url || "")) {
    // No es una página de YouTube Watch
    content.innerHTML = `
      <div class="no-yt">
        <div class="icon">📺</div>
        <p>Navega a un vídeo de YouTube<br>para añadirlo a la cola.</p>
      </div>
    `;
    return;
  }

  const url   = cleanUrl(tab.url);
  const title = tab.title?.replace(" - YouTube", "").trim() || url;

  content.innerHTML = `
    <div class="body">
      <div class="video-info">
        <div class="label">Vídeo actual</div>
        <div class="title">${escHtml(title)}</div>
        <div class="url">${escHtml(url)}</div>
      </div>

      <button class="btn btn-primary" id="btn-add">
        ⬇️ Añadir a la cola de descarga
      </button>
      <button class="btn btn-secondary" id="btn-open">
        🔗 Abrir la app
      </button>

      <div class="status" id="status"></div>
    </div>
  `;

  document.getElementById("btn-add").addEventListener("click", () => addToQueue(url, title));
  document.getElementById("btn-open").addEventListener("click", () => {
    chrome.tabs.create({ url: "http://localhost:8502" });
  });
});

// ── Helpers ────────────────────────────────────────────────────────────────────

function cleanUrl(raw) {
  const m = raw.match(/https?:\/\/(?:www\.)?youtube\.com\/watch\?v=([\w-]+)/);
  return m ? `https://www.youtube.com/watch?v=${m[1]}` : raw;
}

function escHtml(str) {
  return str.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

function setStatus(type, msg) {
  const el = document.getElementById("status");
  if (!el) return;
  el.className = `status ${type}`;
  el.textContent = msg;
}

async function addToQueue(url, title) {
  const btn = document.getElementById("btn-add");
  btn.disabled = true;
  btn.textContent = "⏳ Añadiendo…";
  setStatus("info", "Conectando con la app local…");

  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, title }),
    });

    if (res.ok) {
      const data = await res.json();
      setStatus("ok", `✓ Añadido a la cola: "${title.slice(0,40)}…"`);
      btn.textContent = "✓ En cola";
    } else {
      const err = await res.text();
      throw new Error(err || `HTTP ${res.status}`);
    }
  } catch (e) {
    if (e.message.includes("Failed to fetch") || e.message.includes("NetworkError")) {
      setStatus("error", "❌ No se puede conectar. ¿Está corriendo la app en localhost:8502?");
    } else {
      setStatus("error", `❌ Error: ${e.message}`);
    }
    btn.disabled = false;
    btn.textContent = "⬇️ Añadir a la cola de descarga";
  }
}
