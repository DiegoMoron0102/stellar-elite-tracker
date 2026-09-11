"""Baja commits de GitHub para los repos de teams.json y los cachea en data/commits.json.

Incremental: un commit ya cacheado (por SHA) nunca se vuelve a pedir.
Uso: python collect.py    (opcional: export GH_TOKEN=ghp_... para 5000 req/hora)
"""
import json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).parent
CACHE = ROOT / "data" / "commits.json"
API = "https://api.github.com"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

if not TOKEN and (ROOT / ".env").exists():  # token local, fuera de git
    for linea in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        if "=" in linea and not linea.startswith("GH_TOKEN"):
            continue  # otra variable, no es la nuestra
        TOKEN = linea.split("=", 1)[-1].strip().strip("\"'")  # "GH_TOKEN=abc" o solo "abc"
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
                f"Rate limit agotado. Se reinicia en {max(0, reset - int(time.time())) // 60} min. "
                f"Lo bajado hasta ahora quedo guardado.{'' if TOKEN else ' Configura GH_TOKEN para 5000 req/hora.'}"
            )
        if e.code == 404:
            print(f"  ! 404 (repo inexistente o privado sin acceso): {url}", file=sys.stderr)
            return None, e.headers
        if e.code == 409:  # repositorio vacio
            return [], e.headers
        raise


def normalizar(repo):
    """Acepta 'owner/repo' o cualquier link de GitHub y devuelve 'owner/repo'."""
    r = repo.strip().rstrip("/").removesuffix(".git")
    if "github.com" in r:
        r = r.split("github.com", 1)[1].lstrip(":/")
    return "/".join(r.split("/")[:2])


def list_commits(repo, since, until):
    """Todos los commits del repo en la ventana del programa."""
    out, page = [], 1
    while True:
        url = f"{API}/repos/{repo}/commits?since={since}&per_page=100&page={page}"
        if until:
            url += f"&until={until}"
        batch, _ = get(url)
        if not batch:
            break
        out += batch
        if len(batch) < 100:
            break
        page += 1
    return out


def main():
    cfg = json.loads((ROOT / "teams.json").read_text(encoding="utf-8"))
    since, until = cfg["start_date"], cfg.get("end_date")

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    nuevos = 0

    for team in cfg["teams"]:
        for repo in map(normalizar, team["repos"]):
            print(f"{team['name']} :: {repo}")
            for c in list_commits(repo, since, until):
                sha = c["sha"]
                if sha in cache:
                    continue
                detail, _ = get(f"{API}/repos/{repo}/commits/{sha}")
                if detail is None:
                    continue
                cache[sha] = {
                    "team": team["name"],
                    "repo": repo,
                    "author": (detail.get("author") or {}).get("login")
                              or detail["commit"]["author"]["name"],
                    "date": detail["commit"]["author"]["date"],
                    "message": detail["commit"]["message"].split("\n")[0][:120],
                    "parents": len(detail.get("parents", [])),
                    "files": [
                        {"f": f["filename"], "a": f.get("additions", 0), "d": f.get("deletions", 0)}
                        for f in detail.get("files", [])
                    ],
                }
                nuevos += 1
                print(f"  + {sha[:7]} {cache[sha]['message'][:60]}")

    CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n{nuevos} commits nuevos. Total en cache: {len(cache)}.")


if __name__ == "__main__":
    main()
