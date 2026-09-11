"""Calcula el puntaje de cada equipo desde data/commits.json -> data/scores.json.

Formula por commit:  min(10, 1 + log2(1 + lineas_efectivas))
Bonus por equipo:    5 * dias_activos + 3 * contribuidores_activos

Uso: python score.py          (escribe data/scores.json y muestra la tabla)
     python score.py --test   (self-check de la formula)
"""
import json, math, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent

# Archivos que no cuentan como desarrollo: generados, dependencias, binarios.
RUIDO = (
    "node_modules/", "vendor/", "dist/", "build/", "target/", ".next/",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock",
    "poetry.lock", "composer.lock", "Gemfile.lock", "go.sum",
)
RUIDO_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".pdf", ".zip",
             ".mp4", ".woff", ".woff2", ".ttf", ".min.js", ".min.css", ".map")

MAX_PTS_COMMIT = 10      # techo por commit: nadie gana con un solo commit gigante
MAX_ARCHIVOS = 50        # mas que esto = probable import masivo, no desarrollo
PTS_DIA_ACTIVO = 5
PTS_CONTRIBUIDOR = 3


def es_ruido(nombre):
    return nombre.startswith(RUIDO) or any(p in nombre for p in RUIDO) or nombre.endswith(RUIDO_EXT)


def puntuar_commit(c):
    """(puntos, motivo). Un commit descartado vale 0 y dice por que."""
    if c["parents"] >= 2:
        return 0.0, "merge"
    utiles = [f for f in c["files"] if not es_ruido(f["f"])]
    if not utiles:
        return 0.0, "solo archivos generados"
    if len(utiles) > MAX_ARCHIVOS:
        return 1.0, f"import masivo ({len(utiles)} archivos)"
    lineas = sum(f["a"] + f["d"] for f in utiles)
    if lineas == 0:
        return 0.0, "sin cambios de lineas"
    return round(min(MAX_PTS_COMMIT, 1 + math.log2(1 + lineas)), 2), ""


def calcular(commits, cfg):
    inicio = datetime.fromisoformat(cfg["start_date"].replace("Z", "+00:00"))
    miembros = {t["name"]: t.get("members", []) for t in cfg["teams"]}

    base = defaultdict(float)
    dias = defaultdict(set)
    autores = defaultdict(set)
    n_commits = defaultdict(int)
    serie = defaultdict(lambda: defaultdict(float))  # equipo -> dia -> puntos
    detalle = []

    for sha, c in commits.items():
        fecha = datetime.fromisoformat(c["date"].replace("Z", "+00:00")).astimezone(timezone.utc)
        if fecha < inicio:
            continue  # proyectos ya avanzados: solo cuenta lo hecho dentro del programa
        pts, motivo = puntuar_commit(c)
        eq, dia = c["team"], fecha.date().isoformat()
        base[eq] += pts
        n_commits[eq] += 1
        if pts > 0:
            dias[eq].add(dia)
            autores[eq].add(c["author"])
        serie[eq][dia] += pts
        detalle.append({"sha": sha[:7], "team": eq, "repo": c["repo"], "author": c["author"],
                        "date": c["date"], "msg": c["message"], "pts": pts, "nota": motivo})

    equipos = []
    for t in cfg["teams"]:
        eq = t["name"]
        total = round(base[eq] + PTS_DIA_ACTIVO * len(dias[eq]) + PTS_CONTRIBUIDOR * len(autores[eq]), 2)
        tam = len(miembros[eq]) or len(autores[eq]) or 1
        equipos.append({
            "name": eq, "total": total, "per_capita": round(total / tam, 2),
            "commits": n_commits[eq], "pts_commits": round(base[eq], 2),
            "dias_activos": len(dias[eq]), "contribuidores": sorted(autores[eq]),
            "tamano": tam, "repos": t["repos"],
        })

    equipos.sort(key=lambda e: -e["total"])
    for i, e in enumerate(equipos, 1):
        e["rank"] = i

    return {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "programa": cfg.get("program", "Programa"),
        "start_date": cfg["start_date"],
        "teams": equipos,
        "serie": {eq: dict(sorted(d.items())) for eq, d in serie.items()},
        "commits": sorted(detalle, key=lambda d: d["date"], reverse=True)[:300],
    }


def demo():
    """Self-check: las reglas que importan no se pueden romper en silencio."""
    f = lambda n, a: {"f": n, "a": a, "d": 0}
    assert puntuar_commit({"parents": 2, "files": [f("a.js", 100)]})[0] == 0, "merge no puntua"
    assert puntuar_commit({"parents": 1, "files": [f("package-lock.json", 9000)]})[0] == 0, "lockfile no puntua"
    assert puntuar_commit({"parents": 1, "files": [f("dist/app.min.js", 500)]})[0] == 0, "build no puntua"
    chico = puntuar_commit({"parents": 1, "files": [f("a.js", 10)]})[0]
    grande = puntuar_commit({"parents": 1, "files": [f("a.js", 5000)]})[0]
    assert 0 < chico < grande <= MAX_PTS_COMMIT, "mas lineas = mas puntos, con techo"
    assert grande / chico < 3, "rendimientos decrecientes: 500x lineas no da 500x puntos"
    assert puntuar_commit({"parents": 1, "files": [f(f"src/{i}.js", 50) for i in range(200)]})[0] == 1.0, "import masivo capeado"
    assert puntuar_commit({"parents": 1, "files": [f("a.js", 0)]})[0] == 0, "commit vacio no puntua"

    cfg = {"start_date": "2026-09-02T00:00:00Z", "program": "t",
           "teams": [{"name": "A", "members": ["x", "y"], "repos": ["o/r"]}]}
    commits = {
        "viejo": {"team": "A", "repo": "o/r", "author": "x", "date": "2026-08-01T10:00:00Z",
                  "message": "previo", "parents": 1, "files": [f("a.js", 900)]},
        "s1": {"team": "A", "repo": "o/r", "author": "x", "date": "2026-09-03T10:00:00Z",
               "message": "m", "parents": 1, "files": [f("a.js", 100)]},
        "s2": {"team": "A", "repo": "o/r", "author": "y", "date": "2026-09-04T10:00:00Z",
               "message": "m", "parents": 1, "files": [f("b.js", 100)]},
    }
    r = calcular(commits, cfg)["teams"][0]
    assert r["commits"] == 2, "el commit anterior al inicio del programa se ignora"
    assert r["dias_activos"] == 2 and len(r["contribuidores"]) == 2
    esperado = round(r["pts_commits"] + 5 * 2 + 3 * 2, 2)
    assert r["total"] == esperado, "bonus de dias y contribuidores"
    assert r["per_capita"] == round(r["total"] / 2, 2)
    print("self-check ok")


def main():
    cfg = json.loads((ROOT / "teams.json").read_text(encoding="utf-8"))
    path = ROOT / "data" / "commits.json"
    commits = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    res = calcular(commits, cfg)
    (ROOT / "data" / "scores.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"{'#':<3}{'EQUIPO':<24}{'TOTAL':>8}{'/PERS':>8}{'COMMITS':>9}{'DIAS':>6}{'DEVS':>6}")
    print("-" * 64)
    for e in res["teams"]:
        print(f"{e['rank']:<3}{e['name'][:23]:<24}{e['total']:>8}{e['per_capita']:>8}"
              f"{e['commits']:>9}{e['dias_activos']:>6}{len(e['contribuidores']):>6}")
    print(f"\ndata/scores.json actualizado ({len(commits)} commits analizados).")


if __name__ == "__main__":
    demo() if "--test" in sys.argv else main()
