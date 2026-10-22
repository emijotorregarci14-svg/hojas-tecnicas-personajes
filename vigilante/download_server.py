from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
FILES = {
    "front": ("1 · Turnaround · Frontal (corregido)", "turnaround_cuerpo_frontal.png"),
    "45": ("1 · Turnaround · 45° (corregido)", "turnaround_cuerpo_45.png"),
    "profile": ("1 · Turnaround · Perfil (corregido)", "turnaround_cuerpo_perfil.png"),
    "back": ("1 · Turnaround · Espalda (corregido)", "turnaround_cuerpo_trasera.png"),
    "chihuahua": ("2 · Equipo con mochila y perro · 3/4 trasera (corregido)", "equipo_mochila_chihuahua_3-4_trasera.png"),
    "motorcycle": ("3 · Moto con walkie-talkie · 21:9 apaisado (corregido)", "moto_walkie_desierto_21x9.png"),
}

cards = []
for key, (label, filename) in FILES.items():
    mtime = int((ROOT / filename).stat().st_mtime)
    cards.append(f'''<section class="card">
  <h2>{label}</h2>
  <img src="/image/{key}?v={mtime}" alt="{label}">
  <a class="download" href="/download/{key}?v={mtime}" download="{filename}">↓ DESCARGAR {label.upper()} (PNG)</a>
</section>''')
PAGE = ('''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hugo adulto (Vigilante) — Correcciones aplicadas</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;padding:24px 16px;background:#101412;color:#e8eee9;font:16px/1.5 system-ui,sans-serif}main{max-width:850px;margin:0 auto}h1{font-size:1.45rem;margin:0 0 8px}.card{margin:20px 0 30px;padding:18px;border:1px solid #3b5145;border-radius:12px;background:#18211c}.card h2{font-size:1.1rem;margin:0 0 12px}.card img{display:block;width:100%;max-height:80vh;object-fit:contain;background:#f5f5f0;border:1px solid #3b5145;margin-bottom:14px}.download{display:inline-flex;align-items:center;gap:8px;padding:12px 18px;border:1px solid #819a88;border-radius:6px;color:#f4f7f4;background:#26372c;text-decoration:none;font-weight:800;letter-spacing:.035em}.download:hover{background:#344a3a}p{color:#bdc9c0}
</style></head><body><main><h1>Hugo adulto (Vigilante) — Correcciones aplicadas</h1><p>Puedes arrastrar cualquiera de las imágenes directamente o usar su botón individual de descarga PNG (sin ZIP).</p>''' + "\n".join(cards) + '''
</main></body></html>''').encode("utf-8")

class Handler(BaseHTTPRequestHandler):
    def _send(self, status, content_type, body, extra_headers=()):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in extra_headers:
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", PAGE)
            return
        if path == "/health":
            self._send(200, "text/plain; charset=utf-8", b"ok")
            return
        parts = path.strip("/").split("/")
        if len(parts) == 2 and parts[0] in ("image", "download") and parts[1] in FILES:
            label, filename = FILES[parts[1]]
            body = (ROOT / filename).read_bytes()
            disposition = "attachment" if parts[0] == "download" else "inline"
            headers = (("Content-Disposition", f'{disposition}; filename="{filename}"'),)
            self._send(200, "image/png", body, headers)
            return
        self.send_error(404)

    def do_HEAD(self):
        self.do_GET()

    def log_message(self, fmt, *args):
        pass

if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8765), Handler).serve_forever()
