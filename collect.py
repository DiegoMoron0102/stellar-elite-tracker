"""Baja commits de GitHub para los repos de teams.json y los cachea en data/commits.json.

Incremental: un commit ya cacheado (por SHA) nunca se vuelve a pedir.
Uso: python collect.py    (opcional: export GH_TOKEN=ghp_... para 5000 req/hora)
"""
import json
from pathlib import Path

from gh import API, get, normalizar

ROOT = Path(__file__).parent
CACHE = ROOT / "data" / "commits.json"


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
