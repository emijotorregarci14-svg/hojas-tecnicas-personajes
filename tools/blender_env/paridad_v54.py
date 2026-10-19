#!/usr/bin/env python3
"""
Arnes de paridad de version para la medicion de la v54.

El agente de vehiculos mide el Shuttle v54 con Blender 4.3.2 (apt, /usr/bin/blender)
y ha publicado:
    - ancho total medido:      1,2974 m
    - holgura del arco trasero: -0,188 m
Para que esos numeros sean comparables, la MISMA medicion tiene que correr en otro
entorno (bpy 4.3.0 de PyPI, aqui) con el MISMO script: `medir_v54.py`.

Este arnes NO reimplementa la medicion: ejecuta el script del otro agente tal cual,
en un Blender headless, y normaliza la salida para poder compararla campo a campo.

Uso:
    # 1) en el workspace de vehiculos, conseguir:
    #      COCHE_MODULAR_v54_SHUTTLE_FINAL.py  (el maestro)
    #      medir_v54.py                        (el script de medicion)
    #      novu_lib.py                         (si medir_v54.py lo importa)
    #
    # 2) aqui, con el venv de bpy 4.3.0:
    BL_VENV=.../ .venv-blender43 \
    BL_XLIB=.../xlibs_43 \
      ./tools/blender_env/bl tools/blender_env/paridad_v54.py \
          --dir /ruta/al/workspace/tools/blender

Salida: JSON con los valores normalizados + las lineas crudas del script.
"""

import argparse
import io
import json
import os
import re
import runpy
import sys
import contextlib
from pathlib import Path

# Palabras clave con las que se detectan los valores que se comparan.
# Tolerante: admite separadores variables ("ANCHO_TOTAL:", "ancho total =", "ancho=1.29").
KEY_PATTERNS = {
    "ancho_m": r"(?:ancho|width|bbox_x|largo_x)[A-Za-z0-9_\s]*?[:=]?\s*(-?[0-9]+[.,][0-9]+)",
    "holgura_m": r"(?:holgura|clearance|gap|arco)[A-Za-z0-9_\s]*?[:=]?\s*(-?[0-9]+[.,][0-9]+)",
    "ruedas_x_m": r"(?:ruedas?_x|wheel_x)[A-Za-z0-9_\s]*?[:=]?\s*(-?[0-9]+[.,][0-9]+)",
}


def parse_valores(raw: str) -> dict:
    """Extrae los valores medidos de la salida del script.

    Primero por patrones de texto; si el script emite JSON, tambien por clave.
    """
    valores = {}
    for campo, patron in KEY_PATTERNS.items():
        m = re.search(patron, raw, re.IGNORECASE)
        if m:
            valores[campo] = float(m.group(1).replace(",", "."))

    # Fallback: el script podria emitir JSON
    for bloque in re.findall(r"\{[^{}]*\}", raw, re.DOTALL):
        try:
            obj = json.loads(bloque)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        for clave, valor in obj.items():
            if not isinstance(valor, (int, float)):
                continue
            k = clave.lower()
            if "ancho" in k and "ancho_m" not in valores:
                valores["ancho_m"] = float(valor)
            elif ("holgura" in k or "clearance" in k) and "holgura_m" not in valores:
                valores["holgura_m"] = float(valor)
    return valores


def parse_args():
    ap = argparse.ArgumentParser(description="Ejecuta medir_v54.py y normaliza su salida")
    ap.add_argument("--dir", required=True,
                    help="Directorio con medir_v54.py y el maestro de la v54")
    ap.add_argument("--script", default="medir_v54.py",
                    help="Script de medicion a ejecutar (por defecto medir_v54.py)")
    ap.add_argument("--args", default="",
                    help="Argumentos extra para el script de medicion")
    return ap.parse_args()


def main():
    args = parse_args()
    workdir = Path(args.dir).resolve()
    script = workdir / args.script

    if not script.exists():
        print(json.dumps({
            "status": "FALTA_FICHERO",
            "esperado": str(script),
            "pista": "El script de medicion vive en el workspace del agente de vehiculos. "
                     "Copiarlo (y el maestro .py que importa) a esta ruta.",
        }, indent=2, ensure_ascii=False))
        return 2

    # El maestro y sus librerias deben ser importables
    sys.path.insert(0, str(workdir))
    sys.path.insert(0, str(workdir.parent))
    sys.path.insert(0, str(Path.cwd()))

    # Guardar y restaurar el estado global de Blender
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)

    argv = sys.argv
    sys.argv = [str(script)] + ([a for a in args.args.split(" ") if a] or [])
    cwd = os.getcwd()
    os.chdir(workdir)

    buf = io.StringIO()
    error = None
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            runpy.run_path(str(script), run_name="__main__")
    except SystemExit as e:
        if e.code not in (0, None):
            error = f"SystemExit({e.code})"
    except Exception as e:  # noqa: BLE001
        error = f"{type(e).__name__}: {e}"
    finally:
        os.chdir(cwd)
        sys.argv = argv

    raw = buf.getvalue()
    print(raw)
    if error:
        print(f"ERROR ejecutando la medicion: {error}", file=sys.stderr)

    valores = parse_valores(raw)

    # Referencia publicada por el agente de vehiculos (Blender 4.3.2, apt)
    REFERENCIA = {"ancho_m": 1.2974, "holgura_m": -0.188}

    comparativa = {}
    for campo, ref in REFERENCIA.items():
        got = valores.get(campo)
        if got is None:
            comparativa[campo] = {"estado": "NO_DETECTADO", "referencia": ref}
        else:
            delta = round(got - ref, 6)
            comparativa[campo] = {
                "estado": "COINCIDE" if abs(delta) < 0.0005 else "DIFIERE",
                "medido": got,
                "referencia_4.3.2_apt": ref,
                "delta": delta,
            }

    print(json.dumps({
        "status": "ERROR" if error else "OK",
        "entorno": {
            "bpy": bpy.app.version_string,
            "background": bpy.app.background,
            "python": sys.version.split()[0],
            "numpy": __import__("numpy").__version__,
        },
        "script": str(script),
        "valores": valores,
        "comparativa_con_4.3.2_apt": comparativa,
        "error": error,
    }, indent=2, ensure_ascii=False))

    return 1 if error else 0


if __name__ == "__main__":
    sys.exit(main())
