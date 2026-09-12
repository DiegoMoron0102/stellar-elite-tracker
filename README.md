# Stellar Elite — Registro de commits

Rastrea el desarrollo de los equipos vía la API de GitHub, calcula un puntaje y lo publica
en un dashboard estático. Sin servidor, sin base de datos, sin dependencias.

## Agregar un equipo

Desde la UI (recomendado en local):

```bash
python serve.py    # dashboard + formulario en http://localhost:8000
```

En el dashboard, botón **Agregar equipo** → pantalla con link del repo y nombre del equipo (opcional).
Los miembros se detectan automáticamente desde los contribuidores del repo.

También podés usar el CLI:

```bash
python add_team.py --repo owner/nombre --members ana,beto --name "Los Astronautas"
python add_team.py --repo https://github.com/owner/nombre          # members = contribuidores del repo
python add_team.py --repo owner/nombre --fetch                       # además corre collect + score
```

También podés editar `teams.json` a mano:

```json
{"name": "Los Astronautas", "members": ["ana", "beto"], "repos": ["ana/proyecto-x"]}
```

`repos` en formato `owner/nombre`. `members` son handles de GitHub y se usan solo para el ranking per cápita.
Si el repo ya está registrado, `add_team.py` fusiona miembros nuevos sin duplicar la entrada.

**Los repos de los equipos deben ser públicos.** No le pedimos token a cada participante — el
sistema lee todo con la API pública de GitHub (o el único `GH_TOKEN` del proyecto, que solo
aumenta el límite de requests, no da acceso a repos privados ajenos). Si un equipo tiene su
repo en privado, que lo pase a público o el commit no se va a poder leer (queda un `404` en el
log de `collect.py`).

## Correr

```bash
# token: crear un archivo .env con  GH_TOKEN=ghp_...  (ya esta en .gitignore)
#         obligatorio si algun repo es privado; sin token son 60 req/hora
python collect.py              # baja commits nuevos (incremental, cachea por SHA)
python score.py                # calcula puntajes + tabla por consola
python serve.py                # dashboard + UI para agregar equipos (http://localhost:8000)
```

`python score.py --test` corre el self-check de la fórmula.

## Puntaje

Solo cuentan los commits con fecha posterior a `start_date` en `teams.json` (2026-09-02).
Los proyectos ya avanzados arrancan todos en cero.

```
por commit:  min(10, 1 + log2(1 + líneas_efectivas))
por equipo:  Σ commits  +  5 × días_activos  +  3 × contribuidores_activos
```

No puntúan: merge commits, lockfiles, `dist/`, `node_modules/`, imágenes y binarios.
Commits con más de 50 archivos útiles se capean a 1 punto (import masivo, no desarrollo).
El `log2` hace que el volumen importe con rendimientos decrecientes: 5000 líneas valen
el doble que 100, no cincuenta veces más.

Los parámetros están arriba de `score.py` como constantes.

## Automatización

`.github/workflows/update.yml` corre cada 6 horas, actualiza `data/` y lo commitea.
Para publicar: **Settings → Pages → Deploy from branch → main / (root)**.

Si algún repo de equipo es privado, crear un PAT con scope `repo` y guardarlo como
secret `GH_TOKEN` — el token por defecto de Actions solo ve este repositorio.
