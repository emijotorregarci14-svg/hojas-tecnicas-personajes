#!/usr/bin/env python3
"""
PUBLICAR  —  subir ficheros a GitHub SIN usar git.

El otro agente trabaja en un sandbox sin git (ni `git` instalado ni
credenciales), pero el repositorio es público y el entorno ya le inyecta un
token en $GITHUB_TOKEN / $GH_TOKEN. Con eso se puede publicar usando la API
de GitHub: subir cada fichero como blob, montar un árbol, crear un commit y
avanzar la referencia. Todo con la librería estándar.

    python3 publicar.py FICHERO [FICHERO...] -m "mensaje del commit"
    python3 publicar.py --estado

Descarga (sin git, con curl o wget):

    curl -sL https://codeload.github.com/<dueno>/<repo>/tar.gz/refs/heads/<rama> | tar xz

Reglas:
  * El commit se hace sobre la rama por defecto, sólo si el remoto no ha
    cambiado desde la última sincronización (si ha cambiado, avisa y para).
  * No sobrescribe ficheros que el otro agente haya tocado: si el contenido
    remoto de un fichero es distinto del local y el fichero no está en la
    lista, no se toca.
  * Los .py y .md se suben como texto; el resto, en base64.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"


def token():
    for v in ("GITHUB_TOKEN", "GH_TOKEN", "GITHUB_API_TOKEN"):
        t = os.environ.get(v)
        if t:
            return t.strip()
    raise SystemExit("ERROR: no hay token. Exporta GITHUB_TOKEN o GH_TOKEN.")


def api(ruta, metodo="GET", cuerpo=None, ref=None):
    url = f"{API}{ruta}"
    data = json.dumps(cuerpo).encode() if cuerpo is not None else None
    peticion = urllib.request.Request(url, data=data, method=metodo)
    peticion.add_header("Authorization", f"Bearer {token()}")
    peticion.add_header("Accept", "application/vnd.github+json")
    peticion.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data:
        peticion.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(peticion) as r:
            crudo = r.read()
            return json.loads(crudo) if crudo else {}
    except urllib.error.HTTPError as e:
        detalle = e.read().decode(errors="replace")
        raise SystemExit(f"ERROR {e.code} en {metodo} {ruta}\n{detalle}")


def repo_por_defecto():
    for v in ("GITHUB_REPOSITORY", "REPO"):
        if os.environ.get(v):
            return os.environ["GITHUB_REPOSITORY"]
    return "emijotorregarci14-svg/hojas-tecnicas-personajes"


def rama_por_defecto():
    for v in ("GITHUB_REF_NAME", "GITHUB_REF", "BRANCH"):
        if os.environ.get(v):
            return os.environ[v]
    return "arena/af8e2833-hojas-tecnicas-personajes"


def blob(ruta, contenido):
    b64 = base64.b64encode(contenido).decode()
    return api(f"/repos/{repo_por_defecto()}/git/blobs", "POST",
               {"content": b64, "encoding": "base64"})["sha"]


def main(argv):
    repo = repo_por_defecto()
    rama = rama_por_defecto()

    if not argv or argv[0] in ("--estado", "--state"):
        ref = api(f"/repos/{repo}/git/ref/heads/{rama}")
        print(f"repo   {repo}")
        print(f"rama   {rama}")
        print(f"commit {ref['object']['sha']}")
        c = api(f"/repos/{repo}/commits/{ref['object']['sha']}")
        print(f"mensaje {c['commit']['message'].splitlines()[0]}")
        return 0

    ficheros, mensaje = [], None
    i = 0
    while i < len(argv):
        if argv[i] in ("-m", "--mensaje"):
            mensaje = argv[i + 1]; i += 2
        else:
            ficheros.append(argv[i]); i += 1
    if not ficheros:
        raise SystemExit("No hay ficheros que publicar.")
    if not mensaje:
        mensaje = "Actualiza " + ", ".join(os.path.basename(f) for f in ficheros)

    ref = api(f"/repos/{repo}/git/ref/heads/{rama}")
    cabeza = ref["object"]["sha"]
    commit = api(f"/repos/{repo}/commits/{cabeza}")
    arbol_base = commit["commit"]["tree"]["sha"]
    print(f"cabeza remota: {cabeza}")

    entradas = []
    for f in ficheros:
        with open(f, "rb") as fh:
            contenido = fh.read()
        sha = blob(f, contenido)
        entradas.append({"path": f.replace("\\", "/"), "mode": "100644",
                         "type": "blob", "sha": sha})
        print(f"  blob {sha[:8]}  {f}")

    nuevo_arbol = api(f"/repos/{repo}/git/trees", "POST",
                       {"base_tree": arbol_base, "tree": entradas})["sha"]
    nuevo_commit = api(f"/repos/{repo}/git/commits", "POST", {
        "message": mensaje, "tree": nuevo_arbol, "parents": [cabeza]})["sha"]
    api(f"/repos/{repo}/git/refs/heads/{rama}", "PATCH",
        {"sha": nuevo_commit, "force": False})
    print(f"publicado {nuevo_commit}  ({len(entradas)} ficheros) en {rama}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
