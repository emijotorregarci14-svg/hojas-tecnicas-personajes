# blender_env — Blender headless (bpy) en sandbox sin X11

Toolkit verificado para ejecutar **Blender como módulo de Python** (`bpy`) en entornos
sin servidor gráfico y sin red a los repositorios de sistema (apt no funciona).

Verificado en este sandbox: **bpy 4.3.0** y **bpy 5.0.1**, ambos con render
**Cycles CPU** completo.

---

## Instalación (3 comandos)

```bash
python3 -m venv .venv-blender
.venv-blender/bin/pip install bpy==4.3.0        # o bpy==5.0.1
.venv-blender/bin/pip install "numpy<2"         # solo para bpy 4.3.x
```

> `numpy<2` es obligatorio en 4.3.x: el puente numpy interno de Blender 4.3 espera
> la API 1.x y avisa `numpy.core.multiarray failed to import`. Con 1.26.4, limpio.

## Stubs de librerías del sistema

```bash
python3 tools/blender_env/make_stubs.py \
        --venv "$PWD/.venv-blender" \
        --out  "$PWD/blender_env/xlibs"
```

Genera:
- `xlibs/libGL.so.1`, `libXrender.so.1`, `libXi.so.6`, `libXfixes.so.3`, `libICE.so.6`,
  `libSM.so.6`, `libxkbcommon.so.0`, `libXxf86vm.so.1` → stubs vacíos con el SONAME
  exacto (satisfacen `DT_NEEDED`).
- `xlibs/libxstub.so` → librería real con los ~500 símbolos que faltaban, inyectada
  con `LD_PRELOAD`.

El script **auto-descubre** qué librerías faltan (no hay lista fija: 4.3 pide
`libXxf86vm` y 5.0 no).

## Uso

```bash
./tools/blender_env/bl script.py
./tools/blender_env/bl -c "import bpy; print(bpy.app.version_string, bpy.app.background)"
BL_VENV=/ruta/.venv-blender43 BL_XLIB=/ruta/xlibs_43 ./tools/blender_env/bl script.py
```

El wrapper `bl` se encarga de `LD_LIBRARY_PATH` + `LD_PRELOAD`.

## Sonda de compatibilidad entre versiones

```bash
./tools/blender_env/bl tools/blender_env/api_probe.py > probe_4.3.json
BL_VENV=... ./tools/blender_env/bl tools/blender_env/api_probe.py > probe_5.0.json
diff probe_4.3.json probe_5.0.json
```

Compara motores de render, sockets del Principled BSDF, props de Cycles, formatos de
salida, espacios de color, modificadores y primitivas. La tabla de diferencias
4.3 → 5.0 está en `COORDINACION_AGENTES.md` §4.

---

## Por qué hace falta (y por qué es seguro)

El wheel `bpy` de PyPI enlaza contra `libGL`, `libX11`, `libXrender`, `libXi`,
`libXfixes`, `libICE`, `libSM`, `libxkbcommon` (y `libXxf86vm` en 4.3). En un sandbox
sin X11:

```
ImportError: libXrender.so.1: cannot open shared object file
ImportError: bpy/lib/libusd_ms.so: undefined symbol: glXGetProcAddress
```

Blender en **modo background** (`bpy.app.background == True`) no inicializa la ventana
ni el backend GPU, así que las funciones stub **nunca se ejecutan**: solo existen para
que el enlazador dinámico resuelva las referencias en tiempo de carga.

**Si tu entorno tiene las librerías reales** (p. ej. `apt install blender`), no uses
los stubs: `blender -b -P script.py` es más limpio. Los stubs son el plan B.

### Trampas del generador (resueltas, pero no las borres)

1. **No usar `local: *;`** en el version script de GNU ld: oculta TODOS los símbolos
   no listados de la tabla dinámica. `ldd -r` dice "resuelto" pero en runtime falla.
2. **La lista de símbolos del version script necesita el prefijo `global:`**; suelta
   aborta con `syntax error in VERSION script`.
3. **Los símbolos versionados** (21 de xkbcommon, `@V_0.5.0`) necesitan `.symver` en
   ensamblador + nodo de versión en el script de ld.
4. **Hay que escanear todas las `.so` del paquete** (53 ficheros), no solo
   `bpy/__init__.so`: `libusd_ms.so` es la que pide los símbolos de GLX.

## Nota sobre Cycles

El enum de motores no se refresca tras `addon_enable`:

```python
bpy.ops.preferences.addon_enable(module="cycles")
scene.render.engine = 'CYCLES'   # asignar directamente; no elegir del enum
```

EEVEE **no** funciona en headless (necesita contexto GPU/GL). Cycles CPU sí.
