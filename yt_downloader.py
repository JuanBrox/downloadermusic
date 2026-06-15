import streamlit as st
import subprocess
import threading
import queue
import json
import os
import re
from datetime import datetime
from pathlib import Path

# ── Configuración de página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="YT Downloader",
    page_icon="🎵",
    layout="wide",
)

# ── Estilos ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Fondo y tipografía general */
  .stApp { background: #0f0f0f; color: #e8e8e8; }

  /* Cabecera */
  .header-box {
    background: linear-gradient(135deg, #1a1a1a 0%, #111 100%);
    border: 1px solid #222;
    border-left: 4px solid #ff0000;
    border-radius: 8px;
    padding: 20px 28px;
    margin-bottom: 24px;
  }
  .header-box h1 { margin: 0; font-size: 1.7rem; letter-spacing: -0.5px; color: #fff; }
  .header-box p  { margin: 4px 0 0; color: #888; font-size: 0.85rem; }

  /* Tarjetas de cola */
  .url-card {
    background: #161616;
    border: 1px solid #242424;
    border-radius: 6px;
    padding: 10px 14px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.82rem;
  }
  .url-card .badge {
    font-size: 0.7rem;
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 20px;
    white-space: nowrap;
  }
  .badge-pending  { background:#2a2a2a; color:#aaa; }
  .badge-done     { background:#0d2d1a; color:#3fb950; }
  .badge-error    { background:#2d0d0d; color:#f85149; }
  .badge-running  { background:#1a1a2e; color:#58a6ff; }
  .url-text { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#ccc; }

  /* Área de log */
  .log-box {
    background: #0a0a0a;
    border: 1px solid #222;
    border-radius: 6px;
    padding: 12px 16px;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 0.75rem;
    color: #7ee787;
    max-height: 320px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-all;
  }

  /* Métricas */
  .metric-row { display:flex; gap:16px; margin-bottom:20px; }
  .metric-box {
    flex:1;
    background:#161616;
    border:1px solid #242424;
    border-radius:6px;
    padding:12px 16px;
    text-align:center;
  }
  .metric-box .val { font-size:1.6rem; font-weight:700; color:#fff; }
  .metric-box .lbl { font-size:0.72rem; color:#666; margin-top:2px; }

  /* Inputs */
  div[data-testid="stTextInput"] input {
    background: #161616 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 6px !important;
    color: #e8e8e8 !important;
  }
  div[data-testid="stTextInput"] input:focus {
    border-color: #ff0000 !important;
    box-shadow: 0 0 0 2px rgba(255,0,0,0.15) !important;
  }

  /* Botones */
  .stButton > button {
    background: #161616 !important;
    border: 1px solid #333 !important;
    color: #e8e8e8 !important;
    border-radius: 6px !important;
    font-size: 0.82rem !important;
  }
  .stButton > button:hover {
    border-color: #ff0000 !important;
    color: #fff !important;
  }
  .stButton > button[kind="primary"] {
    background: #ff0000 !important;
    border-color: #ff0000 !important;
    color: #fff !important;
  }

  /* Divider */
  hr { border-color: #222 !important; margin: 20px 0 !important; }

  /* Ocultar elementos Streamlit */
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding-top: 20px !important; }
</style>
""", unsafe_allow_html=True)

# ── Estado de sesión ───────────────────────────────────────────────────────────
if "cola" not in st.session_state:
    st.session_state.cola = []          # [{url, titulo, estado, log, inicio, fin}]
if "descargando" not in st.session_state:
    st.session_state.descargando = False
if "log_activo" not in st.session_state:
    st.session_state.log_activo = ""
if "carpeta" not in st.session_state:
    st.session_state.carpeta = str(Path.home() / "Downloads" / "YT_Music")

# ── Helpers ────────────────────────────────────────────────────────────────────
YT_RE = re.compile(
    r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w\-]+"
)

def es_url_valida(url: str) -> bool:
    return bool(YT_RE.match(url.strip()))

def limpiar_url(url: str) -> str:
    """Quitar parámetros extra salvo v="""
    m = re.search(r"(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w\-]+)", url)
    return m.group(1) if m else url.strip()

def obtener_titulo(url: str) -> str:
    try:
        r = subprocess.run(
            ["yt-dlp", "--print", "%(title)s", "--no-playlist", url],
            capture_output=True, text=True, timeout=15
        )
        titulo = r.stdout.strip().split("\n")[0]
        return titulo if titulo else url
    except Exception:
        return url

def descargar_url(entrada: dict, carpeta: str, log_q: queue.Queue):
    os.makedirs(carpeta, exist_ok=True)
    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--embed-metadata",
        "--embed-thumbnail",
        "--no-playlist",
        "-o", os.path.join(carpeta, "%(artist)s - %(title)s.%(ext)s"),
        entrada["url"],
    ]
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
        for linea in proc.stdout:
            log_q.put(("log", linea.rstrip()))
        proc.wait()
        ok = proc.returncode == 0
        log_q.put(("done", ok))
    except FileNotFoundError:
        log_q.put(("log", "❌  yt-dlp no encontrado. Instálalo con: brew install yt-dlp"))
        log_q.put(("done", False))
    except Exception as e:
        log_q.put(("log", f"❌  Error: {e}"))
        log_q.put(("done", False))

# ── Cabecera ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-box">
  <h1>🎵 YT Downloader</h1>
  <p>Descarga audio MP3 desde YouTube · cola con historial · API list via <code>localhost:8502/api/add_url</code></p>
</div>
""", unsafe_allow_html=True)

# ── Layout principal ───────────────────────────────────────────────────────────
col_izq, col_der = st.columns([1.1, 1.8], gap="large")

# ════════════════════════════════════════════════════════════════════════════════
# COLUMNA IZQUIERDA — Añadir URLs
# ════════════════════════════════════════════════════════════════════════════════
with col_izq:
    st.markdown("#### Añadir a la cola")

    url_input = st.text_input(
        "URL de YouTube",
        placeholder="https://www.youtube.com/watch?v=...",
        label_visibility="collapsed",
        key="url_input",
    )

    c1, c2 = st.columns([2, 1])
    with c1:
        if st.button("➕ Añadir URL", use_container_width=True):
            url = url_input.strip()
            if not url:
                st.warning("Introduce una URL.")
            elif not es_url_valida(url):
                st.error("URL de YouTube no válida.")
            elif any(e["url"] == limpiar_url(url) for e in st.session_state.cola):
                st.warning("Ya está en la cola.")
            else:
                url_limpia = limpiar_url(url)
                with st.spinner("Obteniendo título…"):
                    titulo = obtener_titulo(url_limpia)
                st.session_state.cola.append({
                    "url": url_limpia,
                    "titulo": titulo,
                    "estado": "pendiente",
                    "log": "",
                    "inicio": None,
                    "fin": None,
                })
                st.rerun()

    with c2:
        if st.button("🗑 Limpiar", use_container_width=True):
            st.session_state.cola = [
                e for e in st.session_state.cola if e["estado"] == "descargando"
            ]
            st.rerun()

    st.markdown("---")
    st.markdown("#### Carpeta de destino")
    nueva_carpeta = st.text_input(
        "Carpeta",
        value=st.session_state.carpeta,
        label_visibility="collapsed",
        key="carpeta_input",
    )
    if nueva_carpeta != st.session_state.carpeta:
        st.session_state.carpeta = nueva_carpeta

    # Opciones adicionales
    with st.expander("⚙️ Opciones yt-dlp"):
        formato = st.selectbox("Formato de audio", ["mp3", "m4a", "opus", "flac", "wav"], index=0)
        calidad = st.selectbox("Calidad (VBR)", ["0 (máx)", "2", "4", "6", "8 (mín)"], index=0)
        playlist = st.checkbox("Permitir playlists completas", value=False)

    # ── API endpoint hint ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### API para la extensión Chrome")
    st.code(
        'curl -X POST http://localhost:8502/api/add_url \\\n'
        '  -H "Content-Type: application/json" \\\n'
        '  -d \'{"url":"https://youtu.be/XXXX"}\'',
        language="bash"
    )
    st.caption("La extensión usará este endpoint para añadir URLs sin abrir la app.")

# ════════════════════════════════════════════════════════════════════════════════
# COLUMNA DERECHA — Cola + descarga
# ════════════════════════════════════════════════════════════════════════════════
with col_der:

    # Métricas
    total   = len(st.session_state.cola)
    hechos  = sum(1 for e in st.session_state.cola if e["estado"] == "hecho")
    errores = sum(1 for e in st.session_state.cola if e["estado"] == "error")
    pend    = sum(1 for e in st.session_state.cola if e["estado"] == "pendiente")

    st.markdown(f"""
    <div class="metric-row">
      <div class="metric-box"><div class="val">{total}</div><div class="lbl">En cola</div></div>
      <div class="metric-box"><div class="val" style="color:#3fb950">{hechos}</div><div class="lbl">Descargados</div></div>
      <div class="metric-box"><div class="val" style="color:#aaa">{pend}</div><div class="lbl">Pendientes</div></div>
      <div class="metric-box"><div class="val" style="color:#f85149">{errores}</div><div class="lbl">Errores</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Botón de descarga
    hay_pendientes = pend > 0
    btn_label = "⏳ Descargando…" if st.session_state.descargando else f"⬇️ Descargar ({pend} pendientes)"
    iniciar = st.button(
        btn_label,
        disabled=not hay_pendientes or st.session_state.descargando,
        type="primary",
        use_container_width=True,
    )

    st.markdown("---")
    st.markdown("#### Cola de descargas")

    # Renderizar tarjetas
    badge_map = {
        "pendiente":   ("badge-pending",  "⏸ pendiente"),
        "descargando": ("badge-running",  "▶ descargando"),
        "hecho":       ("badge-done",     "✓ listo"),
        "error":       ("badge-error",    "✗ error"),
    }

    if not st.session_state.cola:
        st.markdown('<p style="color:#555;font-size:0.85rem;text-align:center;padding:24px 0">Sin URLs en cola. Añade una a la izquierda.</p>', unsafe_allow_html=True)
    else:
        for i, entrada in enumerate(st.session_state.cola):
            cls, texto_badge = badge_map.get(entrada["estado"], ("badge-pending", "?"))
            titulo_corto = entrada["titulo"][:72] + "…" if len(entrada["titulo"]) > 72 else entrada["titulo"]
            st.markdown(f"""
            <div class="url-card">
              <span class="badge {cls}">{texto_badge}</span>
              <span class="url-text" title="{entrada['url']}">{titulo_corto}</span>
            </div>
            """, unsafe_allow_html=True)

    # ── Log en tiempo real ──────────────────────────────────────────────────────
    if st.session_state.log_activo or st.session_state.descargando:
        st.markdown("---")
        st.markdown("#### Progreso")
        log_placeholder = st.empty()
        log_placeholder.markdown(
            f'<div class="log-box">{st.session_state.log_activo or "Iniciando…"}</div>',
            unsafe_allow_html=True
        )

# ── Lógica de descarga secuencial ─────────────────────────────────────────────
if iniciar and not st.session_state.descargando:
    st.session_state.descargando = True
    calidad_val = calidad.split(" ")[0]

    for i, entrada in enumerate(st.session_state.cola):
        if entrada["estado"] != "pendiente":
            continue

        # Marcar como descargando
        st.session_state.cola[i]["estado"] = "descargando"
        st.session_state.cola[i]["inicio"] = datetime.now().isoformat()
        st.session_state.log_activo = f"▶ Descargando: {entrada['titulo']}\n"
        st.rerun()

    # La lógica real se ejecuta tras el rerun — ver bloque abajo
    st.session_state.descargando = False

# Procesar el primero en estado "descargando"
activo = next((e for e in st.session_state.cola if e["estado"] == "descargando"), None)
if activo:
    idx = st.session_state.cola.index(activo)
    log_q: queue.Queue = queue.Queue()
    carpeta = st.session_state.carpeta

    hilo = threading.Thread(
        target=descargar_url, args=(activo, carpeta, log_q), daemon=True
    )
    hilo.start()

    log_lines = [f"▶ {activo['titulo']}"]
    log_ph = st.empty()

    while hilo.is_alive() or not log_q.empty():
        try:
            tipo, val = log_q.get(timeout=0.3)
            if tipo == "log":
                log_lines.append(val)
                st.session_state.log_activo = "\n".join(log_lines[-60:])
                log_ph.markdown(
                    f'<div class="log-box">{st.session_state.log_activo}</div>',
                    unsafe_allow_html=True
                )
            elif tipo == "done":
                estado_final = "hecho" if val else "error"
                st.session_state.cola[idx]["estado"] = estado_final
                st.session_state.cola[idx]["fin"] = datetime.now().isoformat()
                break
        except queue.Empty:
            continue

    hilo.join()

    # Si quedan pendientes, seguir
    hay_mas = any(e["estado"] == "pendiente" for e in st.session_state.cola)
    st.session_state.descargando = hay_mas
    st.rerun()
