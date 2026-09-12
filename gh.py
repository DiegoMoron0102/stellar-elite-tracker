"""Helpers compartidos para la API de GitHub (stdlib only)."""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
API = "https://api.github.com"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

if not TOKEN and (ROOT / ".env").exists():
    for linea in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        if "=" in linea and not linea.startswith("GH_TOKEN"):
            continue
        TOKEN = linea.split("=", 1)[-1].strip().strip("\"'")
        break


def get(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "stellar-elite-tracker",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r), r.headers
    except urllib.error.HTTPError as e:
        if e.code in (403, 429) and e.headers.get("X-RateLimit-Remaining") == "0":
            reset = int(e.headers.get("X-RateLimit-Reset", 0))
            raise SystemExit(
                f"Rate limit agotado. Se reinicia en {max(0, reset - int(time.time())) // 60} min."
                f"{'' if TOKEN else ' Configura GH_TOKEN para 5000 req/hora.'}"
            )
        if e.code == 404:
            print(f"  ! 404 (repo inexistente o privado sin acceso): {url}", file=sys.stderr)
            return None, e.headers
        if e.code == 409:
            return [], e.headers
        raise


def normalizar(repo):
    """Acepta 'owner/repo' o cualquier link de GitHub y devuelve 'owner/repo'."""
    r = repo.strip().rstrip("/").removesuffix(".git")
    if "github.com" in r:
        r = r.split("github.com", 1)[1].lstrip(":/")
    parts = r.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError(f"Repo invalido: {repo!r}. Usa owner/nombre o una URL de GitHub.")
    return "/".join(parts[:2])


def list_contributors(repo, limit=30):
    """Logins de contribuidores del repo (max `limit`)."""
    out, page = [], 1
    while len(out) < limit:
        batch, _ = get(f"{API}/repos/{repo}/contributors?per_page=100&page={page}")
        if batch is None:
            raise ValueError(f"No se pudo leer contribuidores de {repo}.")
        if not batch:
            break
        for c in batch:
            login = c.get("login")
            if login and login not in out:
                out.append(login)
            if len(out) >= limit:
                break
        if len(batch) < 100:
            break
        page += 1
    return out
