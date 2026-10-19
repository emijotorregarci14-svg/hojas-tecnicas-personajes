#!/usr/bin/env python3
"""
Genera librerias compartidas "stub" para las dependencias de sistema que faltan
a los wheels de Blender (bpy) en el sandbox de Arena.

Por que funciona:
  1) El binario de Blender declara DT_NEEDED hacia libGL/libX11/... Si esos
     ficheros no existen, el enlazador dinamico se niega a cargar el binario.
     -> Se crean 7 .so vacios con el SONAME exacto.
  2) Los simbolos que esas librarias aportarian quedan sin resolver.
     -> Se recopilan con `ldd -r` y se exportan desde una libreria real de
        stubs (libxstub.so) que se inyecta con LD_PRELOAD.
  3) Blender en modo background (bpy) nunca invoca la API de X11/GL: las
     fuentes de ventana y el backend GPU solo se inicializan en modo ventana.
     Los stubs no-op nunca llegan a ejecutarse.

Uso:
    python3 make_stubs.py            # genera stubs + smoke test
    python3 make_stubs.py --report   # solo informa del estado
"""

import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent          # raiz del repo (contiene tools/blender_env/)
VENV = REPO / ".venv-blender"
BPY_SO = VENV / "lib/python3.11/site-packages/bpy/__init__.so"
OUT = HERE / "xlibs"
SRC = HERE / "_stub_build"
VERSION_TAG = "5.0.1"
# STUB_SO se resuelve en tiempo de ejecucion: OUT puede cambiar por CLI


def stub_so():
    return OUT / "libxstub.so"

# SONAME -> paquete Debian equivalente (documentativo)
STUB_LIBS = {
    "libGL.so.1": "libgl1",
    "libICE.so.6": "libice6",
    "libSM.so.6": "libsm6",
    "libXfixes.so.3": "libxfixes3",
    "libXi.so.6": "libxi6",
    "libXrender.so.1": "libxrender1",
    "libxkbcommon.so.0": "libxkbcommon0",
}

VALID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def sh(cmd, env=None, check=True):
    return subprocess.run(cmd, capture_output=True, text=True, env=env, check=check)


def ldd_env():
    env = dict(os.environ)
    pylib = VENV / "lib"
    env["LD_LIBRARY_PATH"] = f"{OUT}:{pylib}:{env.get('LD_LIBRARY_PATH', '')}"
    return env


def discover_missing_libs():
    """Detecta dinamicamente las librerias del sistema ausentes (DT_NEEDED).

    En vez de mantener una lista fija (que se queda corta entre versiones de
    bpy: 4.3 pide libXxf86vm y 5.0 no), se consulta al enlazador.
    """
    found = set()
    for so in bpy_shared_objects():
        res = sh(["ldd", str(so)], env=ldd_env(), check=False)
        for line in (res.stdout + res.stderr).splitlines():
            if "=> not found" in line:
                soname = line.split("=>")[0].strip()
                if soname and ".so" in soname:
                    found.add(soname)
    return sorted(found)


def build_empty_stubs(sonames=None):
    """Crea los .so vacios con el SONAME que el binario espera."""
    OUT.mkdir(parents=True, exist_ok=True)
    SRC.mkdir(parents=True, exist_ok=True)
    targets = sonames if sonames is not None else list(STUB_LIBS)
    for soname in targets:
        c = SRC / f"empty_{soname.replace('.', '_')}.c"
        c.write_text("/* stub vacio: solo satisface DT_NEEDED */\n")
        so = OUT / soname
        sh(["gcc", "-shared", "-fPIC", "-O0", "-w",
            f"-Wl,-soname,{soname}", "-o", str(so), str(c)])
    print(f"  [1/4] {len(targets)} stubs vacios creados: {targets}")


def bpy_shared_objects():
    """Todas las .so del paquete bpy (la principal + las de bpy/lib)."""
    pkg = BPY_SO.parent
    objs = [BPY_SO]
    for so in sorted(pkg.rglob("*.so")):
        if so not in objs:
            objs.append(so)
    return objs


def find_unresolved():
    """Simbolos que el enlazador no encuentra en TODAS las .so de bpy.

    Devuelve (lista_simbolos, {simbolo: version}).
    """
    missing, versions = [], {}
    for so in bpy_shared_objects():
        res = sh(["ldd", "-r", str(so)], env=ldd_env(), check=False)
        text = res.stdout + res.stderr
        for m in re.finditer(r"undefined symbol:\s*([A-Za-z0-9_]+),?\s*(?:version\s+([A-Za-z0-9_.]+))?", text):
            name, ver = m.group(1), m.group(2)
            if name not in missing:
                missing.append(name)
            if ver:
                versions[name] = ver
    return missing, versions


def classify_types(binary):
    """Mapa simbolo -> 'FUNC'|'OBJECT' leyendo la tabla dinamica."""
    out = sh(["readelf", "--dyn-syms", "--wide", str(binary)]).stdout
    types = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 8 or parts[6] != "UND":
            continue
        types[parts[7]] = "FUNC" if parts[3] in ("FUNC", "IFUNC") else "OBJECT"
    return types


def build_stub_lib(symbols, types, versions):
    """Compila libxstub.so exportando todos los simbolos resueltos.

    Se emite ensamblador puro: evita los alias `__asm__` de C, que producen
    directivas .size inconsistentes al enlazar. Los simbolos versionados
    (p.ej. xkbcommon @V_0.5.0) se resuelven con .symver + script de versiones.
    """
    skipped = [s for s in symbols if not VALID.match(s)]
    funcs = [s for s in symbols if VALID.match(s) and types.get(s, "FUNC") == "FUNC"]
    objs = [s for s in symbols if VALID.match(s) and types.get(s, "FUNC") == "OBJECT"]

    s = SRC / "xstub.s"
    with open(s, "w") as f:
        f.write("/* Stubs no-op para el sandbox sin X11/OpenGL (Blender headless). */\n")
        f.write(".text\n")
        for name in funcs:
            f.write(f".globl {name}\n.type {name}, @function\n{name}:\n\tret\n"
                    f".size {name}, .-{name}\n")
            if name in versions:
                f.write(f".symver {name}, {name}@{versions[name]}\n")
        f.write(".bss\n.align 8\n")
        for name in objs:
            f.write(f".globl {name}\n.type {name}, @object\n{name}:\n\t.zero 4096\n"
                    f".size {name}, .-{name}\n")

    # Script de versiones: un nodo por version detectada.
    # OJO 1: la lista de simbolos necesita el prefijo `global:`; si se escribe
    #         suelta, ld aborta con "syntax error in VERSION script".
    # OJO 2: NO se usa `local: *;` -> eso ocultaria TODOS los simbolos no
    #         listados (glX, X11...) de la tabla dinamica y el runtime fallaria
    #         con "undefined symbol" aunque ldd -r diga que esta resuelto.
    nodes = sorted(set(versions.values()))
    vfile = SRC / "xstub.map"
    with open(vfile, "w") as f:
        for ver in nodes:
            syms = [n for n, v in versions.items() if v == ver]
            f.write(f"{ver} {{\n  global:\n")
            for n in syms:
                f.write(f"    {n};\n")
            f.write("};\n")

    obj = SRC / "xstub.o"
    sh(["gcc", "-c", "-fPIC", "-w", "-o", str(obj), str(s)])
    cmd = ["gcc", "-shared", "-o", str(stub_so()), str(obj)]
    if nodes:
        cmd += ["-Wl,--version-script", str(vfile)]
    sh(cmd)
    if skipped:
        print(f"  (omitidos {len(skipped)} simbolos no-ASCII: {skipped[:5]})")
    print(f"  [2/4] libxstub.so: {len(funcs)} funciones + {len(objs)} datos "
          f"({len(nodes)} nodos de version: {nodes})")


def verify():
    env = ldd_env()
    env["LD_PRELOAD"] = str(stub_so())
    still = []
    for so in bpy_shared_objects():
        res = sh(["ldd", "-r", str(so)], env=env, check=False)
        text = res.stdout + res.stderr
        for m in re.finditer(r"undefined symbol:\s*([A-Za-z0-9_]+)", text):
            if m.group(1) not in still:
                still.append(m.group(1))
    return still, ""


def smoke():
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = str(OUT)
    env["LD_PRELOAD"] = str(stub_so())
    code = (
        "import bpy;"
        "bpy.ops.wm.read_factory_settings(use_empty=True);"
        "print('BPY_IMPORT_OK', bpy.app.version_string, 'background=', bpy.app.background);"
        "print('ENGINES', [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items])"
    )
    res = sh([str(VENV / "bin/python"), "-c", code], env=env, check=False)
    print("  [3/4] smoke test:")
    for line in res.stdout.strip().splitlines():
        print("       ", line)
    if res.returncode != 0:
        print(res.stderr.strip()[-4000:])
        return False
    return True


def set_target(venv_path: str, out_path: str, tag: str):
    """Apunta el generador a otro venv/versi\u00f3n de bpy."""
    global VENV, BPY_SO, OUT, SRC, VERSION_TAG
    VENV = Path(venv_path).resolve()
    BPY_SO = VENV / "lib/python3.11/site-packages/bpy/__init__.so"
    OUT = Path(out_path).resolve()
    SRC = OUT.parent / (OUT.name + "_build")
    VERSION_TAG = tag
    print(f"Objetivo: bpy en {VENV}  ->  stubs en {OUT}  (tag {tag})")


def main():
    if not BPY_SO.exists():
        print(f"ERROR: no encuentro {BPY_SO}")
        return 1

    print(f"Analizando {BPY_SO}")
    missing_libs = discover_missing_libs()
    build_empty_stubs(missing_libs)

    missing, versions = find_unresolved()
    print(f"  simbolos sin resolver tras los stubs vacios: {len(missing)}")
    if versions:
        print(f"  (versionados: {len(versions)} -> {sorted(set(versions.values()))})")

    types = classify_types(BPY_SO)
    build_stub_lib(missing, types, versions)

    still, text = verify()
    print(f"  [3/4] simbolos aun sin resolver: {len(still)}")
    for s in still[:30]:
        print("        !", s)

    ok = smoke()
    if ok:
        print("  [4/4] OK")
    return 0 if ok and not still else 1


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Genera stubs de sistema para bpy headless")
    ap.add_argument("--venv", default=str(REPO / ".venv-blender"))
    ap.add_argument("--out", default=str(HERE / "xlibs"))
    ap.add_argument("--tag", default="bpy")
    a = ap.parse_args()
    set_target(a.venv, a.out, a.tag)
    sys.exit(main())
