// content.js — Inyecta un botón flotante en páginas de YouTube Watch

const API_URL = "http://localhost:8502/api/add_url";

(function init() {
  // Evitar duplicados si el script se reinjecta
  if (document.getElementById("ytdl-float-btn")) return;

  const btn = document.createElement("button");
  btn.id = "ytdl-float-btn";
  btn.innerHTML = "🎵 MP3";
  btn.title = "Añadir a la cola de descarga";

  Object.assign(btn.style, {
    position:     "fixed",
    bottom:       "24px",
    right:        "24px",
    zIndex:       "99999",
    background:   "#ff0000",
    color:        "#fff",
    border:       "none",
    borderRadius: "24px",
    padding:      "9px 18px",
    fontSize:     "13px",
    fontWeight:   "700",
    cursor:       "pointer",
    boxShadow:    "0 4px 16px rgba(0,0,0,0.4)",
    fontFamily:   "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    transition:   "transform 0.15s, opacity 0.15s",
    letterSpacing: "0.3px",
  });

  btn.addEventListener("mouseenter", () => {
    btn.style.transform = "scale(1.06)";
  });
  btn.addEventListener("mouseleave", () => {
    btn.style.transform = "scale(1)";
  });

  btn.addEventListener("click", async () => {
    const url   = cleanUrl(window.location.href);
    const title = document.title.replace(" - YouTube", "").trim();

    btn.textContent = "⏳";
    btn.style.opacity = "0.7";

    try {
      const res = await fetch(API_URL, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ url, title }),
      });

      if (res.ok) {
        btn.innerHTML   = "✓ En cola";
        btn.style.background = "#1a7340";
        btn.style.opacity    = "1";
        setTimeout(() => {
          btn.innerHTML        = "🎵 MP3";
          btn.style.background = "#ff0000";
        }, 3000);
      } else {
        throw new Error(`HTTP ${res.status}`);
      }
    } catch (e) {
      btn.innerHTML        = "❌ Sin conexión";
      btn.style.background = "#7a1010";
      btn.style.opacity    = "1";
      setTimeout(() => {
        btn.innerHTML        = "🎵 MP3";
        btn.style.background = "#ff0000";
      }, 4000);
    }
  });

  document.body.appendChild(btn);
})();

function cleanUrl(raw) {
  const m = raw.match(/https?:\/\/(?:www\.)?youtube\.com\/watch\?v=([\w-]+)/);
  return m ? `https://www.youtube.com/watch?v=${m[1]}` : raw;
}
