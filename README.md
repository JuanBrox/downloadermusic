# YT Downloader — Setup

## Requisitos previos

```bash
brew install yt-dlp ffmpeg
pip install -r requirements.txt
```

---

## 1 · App Streamlit

```bash
streamlit run yt_downloader.py --server.port 8502
```

Abre http://localhost:8502

---

## 2 · API para la extensión Chrome (opcional)

En otra terminal:

```bash
python api_server.py
```

Escucha en http://localhost:8503  
La extensión Chrome envía las URLs aquí → se guardan en `queue.json`  
La app Streamlit lee ese archivo al pulsar **"Actualizar cola desde extensión"**.

---

## 3 · Extensión Chrome

1. Abre Chrome → `chrome://extensions`
2. Activa **Modo desarrollador** (arriba a la derecha)
3. Pulsa **"Cargar descomprimida"** → selecciona la carpeta `yt_downloader_extension/`
4. Ve a cualquier vídeo de YouTube
5. Aparecerá un botón rojo **🎵 MP3** abajo a la derecha, o usa el icono de la extensión en la barra del navegador

> **Nota sobre los iconos:** la extensión funciona sin iconos PNG, pero Chrome mostrará un icono genérico. Puedes añadir `icon16.png`, `icon48.png` e `icon128.png` en la carpeta de la extensión si quieres un icono personalizado.

---

## Arquitectura

```
YouTube (Chrome)
    │
    ├─ Botón flotante (content.js)  ──┐
    └─ Popup extensión (popup.js)   ──┤
                                      │ POST /api/add_url
                                   api_server.py (puerto 8503)
                                      │ escribe queue.json
                                   yt_downloader.py (Streamlit)
                                      │ ejecuta yt-dlp
                                   ~/Downloads/YT_Music/
```
