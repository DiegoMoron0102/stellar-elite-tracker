"""Sirve el dashboard y expone API para registrar equipos desde la UI.

Uso: python serve.py [puerto]
"""
import json
import subprocess
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

from teams import agregar_equipo, cargar_teams, ejecutar_pipeline, guardar_teams, parse_members

ROOT = Path(__file__).parent


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        if args and args[0].startswith("GET /data/"):
            return
        super().log_message(fmt, *args)

    def _json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        n = int(self.headers.get("Content-Length", 0))
        if not n:
            return {}
        return json.loads(self.rfile.read(n).decode("utf-8"))

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/teams":
            cfg = cargar_teams()
            self._json(200, {"teams": cfg.get("teams", []), "program": cfg.get("program")})
            return
        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            if path == "/api/teams":
                data = self._read_json()
                repo = (data.get("repo") or "").strip()
                if not repo:
                    self._json(400, {"ok": False, "error": "Falta el repo."})
                    return

                cfg = cargar_teams()
                result = agregar_equipo(
                    cfg,
                    repo,
                    parse_members(data.get("members")),
                    (data.get("name") or "").strip(),
                )
                guardar_teams(cfg)

                if data.get("fetch"):
                    ejecutar_pipeline()

                self._json(200, {"ok": True, **result})
                return

            if path == "/api/refresh":
                ejecutar_pipeline()
                self._json(200, {"ok": True, "message": "Ranking actualizado."})
                return

            self._json(404, {"ok": False, "error": "Ruta no encontrada."})
        except ValueError as e:
            self._json(400, {"ok": False, "error": str(e)})
        except subprocess.CalledProcessError as e:
            self._json(500, {"ok": False, "error": f"Error al actualizar datos (exit {e.returncode})."})
        except Exception as e:
            self._json(500, {"ok": False, "error": str(e)})


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server = HTTPServer(("", port), Handler)
    print(f"Dashboard: http://localhost:{port}")
    print("API: POST /api/teams · GET /api/teams · POST /api/refresh")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDetenido.")


if __name__ == "__main__":
    main()
