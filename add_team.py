"""Registra un repo y cuentas de GitHub en teams.json.

Uso:
  python add_team.py --repo owner/nombre --members user1,user2 --name "Los Astronautas"
  python add_team.py --repo https://github.com/owner/nombre --fetch
  python add_team.py --repo owner/nombre   # members desde contribuidores del repo
"""
import argparse
import json
import sys

from gh import normalizar
from teams import agregar_equipo, cargar_teams, ejecutar_pipeline, guardar_teams, parse_members


def main():
    p = argparse.ArgumentParser(description="Añade cuentas de GitHub y un repo a teams.json")
    p.add_argument("--repo", required=True, help="owner/nombre o URL de GitHub")
    p.add_argument("--members", default="", help="handles separados por coma (default: contribuidores del repo)")
    p.add_argument("--name", default="", help="nombre del equipo (default: nombre del repo)")
    p.add_argument("--fetch", action="store_true", help="correr collect.py y score.py despues de guardar")
    args = p.parse_args()

    try:
        normalizar(args.repo)
    except ValueError as e:
        raise SystemExit(str(e)) from e

    cfg = cargar_teams()
    try:
        result = agregar_equipo(cfg, args.repo, parse_members(args.members), args.name.strip())
    except ValueError as e:
        raise SystemExit(str(e)) from e

    guardar_teams(cfg)
    print(result["message"])
    print("\nEquipo registrado:")
    print(json.dumps(result["team"], indent=2, ensure_ascii=False))

    if args.fetch:
        print("\n--- collect.py ---")
        ejecutar_pipeline()
    else:
        print("\nSiguiente: python collect.py && python score.py")


if __name__ == "__main__":
    main()
