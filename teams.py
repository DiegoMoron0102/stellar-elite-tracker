"""Lógica compartida para gestionar teams.json."""
import json
import subprocess
import sys
from pathlib import Path

from gh import ROOT, list_contributors, normalizar

TEAMS = ROOT / "teams.json"


def cargar_teams():
    return json.loads(TEAMS.read_text(encoding="utf-8"))


def guardar_teams(cfg):
    TEAMS.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def buscar_equipo_por_repo(cfg, repo):
    repo = normalizar(repo)
    for team in cfg["teams"]:
        if repo in map(normalizar, team.get("repos", [])):
            return team
    return None


def parse_members(raw):
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(m).strip().lstrip("@") for m in raw if str(m).strip()]
    return [m.strip().lstrip("@") for m in str(raw).split(",") if m.strip()]


def agregar_equipo(cfg, repo, members, name=""):
    repo = normalizar(repo)
    members = [m for m in members if m]

    if not members:
        members = list_contributors(repo)
        if not members:
            raise ValueError(f"No se encontraron contribuidores en {repo}.")

    existente = buscar_equipo_por_repo(cfg, repo)
    if existente:
        previos = set(existente.get("members", []))
        nuevos = sorted(set(members) - previos)
        existente["members"] = sorted(previos | set(members))
        return {
            "team": existente,
            "created": False,
            "members_added": nuevos,
            "message": (
                f"Miembros añadidos: {', '.join(nuevos)}"
                if nuevos else "Repo ya registrado. Sin miembros nuevos."
            ),
        }

    team = {
        "name": (name or "").strip() or repo.split("/")[-1],
        "members": sorted(set(members)),
        "repos": [repo],
    }
    cfg["teams"].append(team)
    return {
        "team": team,
        "created": True,
        "members_added": team["members"],
        "message": f"Equipo '{team['name']}' registrado.",
    }


def ejecutar_pipeline():
    subprocess.run([sys.executable, str(ROOT / "collect.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "score.py")], check=True)
