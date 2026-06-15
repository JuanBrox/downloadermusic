"""
api_server.py — Servidor FastAPI mínimo que recibe URLs desde la extensión Chrome
y las pasa a la app Streamlit vía un archivo de cola compartido (queue.json).

Ejecutar en paralelo con la app:
  python api_server.py          (puerto 8503 por defecto)
  streamlit run yt_downloader.py

La app Streamlit lee queue.json al inicio y cuando se pulsa "Actualizar cola".
"""

import json
import os
from pathlib import Path
from datetime import datetime

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("Instala dependencias: pip install fastapi uvicorn pydantic")
    raise

QUEUE_FILE = Path(__file__).parent / "queue.json"
API_PORT   = 8503

app = FastAPI(title="YT Downloader API", version="1.0")

# Permitir peticiones desde la extensión Chrome (origen: chrome-extension://)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

class AddUrlRequest(BaseModel):
    url:   str
    title: str = ""

def load_queue() -> list:
    if QUEUE_FILE.exists():
        try:
            return json.loads(QUEUE_FILE.read_text())
        except Exception:
            return []
    return []

def save_queue(q: list):
    QUEUE_FILE.write_text(json.dumps(q, ensure_ascii=False, indent=2))

@app.get("/health")
def health():
    return {"status": "ok", "queue_size": len(load_queue())}

@app.post("/api/add_url")
def add_url(req: AddUrlRequest):
    url = req.url.strip()
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="URL no válida")

    q = load_queue()

    # Evitar duplicados de URLs pendientes
    if any(e["url"] == url and e["estado"] == "pendiente" for e in q):
        return {"ok": True, "message": "Ya está en la cola", "duplicate": True}

    q.append({
        "url":    url,
        "titulo": req.title or url,
        "estado": "pendiente",
        "log":    "",
        "inicio": None,
        "fin":    None,
        "added":  datetime.now().isoformat(),
    })
    save_queue(q)
    return {"ok": True, "message": "Añadido a la cola", "queue_size": len(q)}

@app.get("/api/queue")
def get_queue():
    return {"queue": load_queue()}

if __name__ == "__main__":
    print(f"▶  API escuchando en http://localhost:{API_PORT}")
    print(f"▶  Cola en: {QUEUE_FILE}")
    uvicorn.run(app, host="0.0.0.0", port=API_PORT, log_level="warning")
