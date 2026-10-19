# blender_env — Blender headless (bpy) en sandbox sin X11

Toolkit verificado para ejecutar **Blender como módulo de Python** (`bpy`) en entornos
sin servidor gráfico y sin red a los repositorios de sistema (apt no funciona).

Verificado en este sandbox: **bpy 4.3.0** y **bpy 5.0.1**, ambos con render
**Cycles CPU** completo.

> **Alcance:** entorno de pruebas del agente de **hojas de personajes**. El entorno de
> vehículos no usa stubs (instala Blender con apt). Reglas canónicas de coordinación:
> `tools/blender/COORDINACION_AGENTES.md`.

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

---

## Matriz de compatibilidad 4.3 → 5.0 (medida, no supuesta)

Ejecuté `api_probe.py` en ambas versiones. Diferencias **reales**:

| API | 4.3 | 5.0 | Impacto |
|---|---|---|---|
| `scene.render.engine` (EEVEE) | `BLENDER_EEVEE_NEXT` | `BLENDER_EEVEE` | Rompe si el script fija el string. Con Cycles, no afecta |
| `scene.cycles.feature_set` | existe | **eliminado** | Rompe si se asigna |
| `scene.cycles.use_sample_subset` / `sample_subset_length` | — | nuevos | Solo 5.0 |
| `scene.cycles.volume_biased` | — | nuevo | Solo 5.0 |
| Color spaces (sequencer) | `AgX Base Display P3`, `AgX Base Rec.1886`, `AgX Base Rec.2020` | eliminados | Rompe si el look está hardcodeado |
| Color spaces (sequencer) | — | `ACES 1.3 sRGB`, `ACES 2.0 sRGB`, `ACEScc`, `ACEScct`, `Rec.2100-HLG`, `Rec.2100-PQ`, `scene_linear` | Solo 5.0 |
| `Material.use_nodes` | ok | *DeprecationWarning* (se elimina en 6.0) | Ruido, no rompe |
| Sockets del Principled BSDF | — | **idénticos** | Los scripts de materiales son seguros |
| `shade_auto_smooth` / `shade_smooth_by_angle` | ambos | ambos | Sin cambios |
| `use_auto_smooth` (Mesh) | ausente | ausente | Eliminado en 4.1, no vuelve |
| Formatos de salida (`WEBP` incluido) | idénticos | idénticos | WebP q90 funciona igual |
| `cycles.device` (`CPU`/`GPU`) | idénticos | idénticos | Sin cambios |

**Conclusión:** el riesgo real de versionado está en (a) el identificador de EEVEE y
(b) los color spaces por nombre. El resto es estable.

### numpy según versión
- bpy **4.3.0** arrastra `numpy 2.x` → Blender 4.3 avisa `numpy.core.multiarray failed
  to import` (su puente numpy interno espera 1.x). **Fijar `numpy<2`**. Con `numpy 1.26.4`
  el aviso desaparece y el render va limpio.
- bpy **5.0.1** ya fija `numpy 1.26.4`. Sin avisos.

### Activar Cycles
El enum de motores no se refresca tras `addon_enable`. Asignar directamente:

```python
bpy.ops.preferences.addon_enable(module="cycles")
scene.render.engine = 'CYCLES'   # no elegir del enum
```

EEVEE **no** funciona en headless (necesita contexto GPU/GL). Cycles CPU sí.

---

## Paridad de medición con el entorno de vehículos (4.3.2 apt)

El agente de vehículos mide el Shuttle v54 con **Blender 4.3.2 de apt** y ha publicado:
**ancho 1,2974 m** y **holgura del arco trasero −0,188 m**.

Aquí no hay apt con red, así que la versión disponible es **bpy 4.3.0 de PyPI**.
*bpy 4.3.0 ≠ binario apt 4.3.2*: para darlo por equivalente hay que **correr la misma
medición en ambos entornos y comparar números**, no asumir equivalencia.

**Protocolo:**

1. Conseguir del workspace de vehículos: `medir_v54.py` + `COCHE_MODULAR_v54_SHUTTLE_FINAL.py`
   (+ `novu_lib.py` si `medir_v54.py` lo importa).
2. Ejecutar el arnés, que corre ese script tal cual en bpy 4.3.0 headless:

```bash
BL_VENV="$PWD/.venv-blender43" \
BL_XLIB="/home/user/blender_env/xlibs_43" \
  ./tools/blender_env/bl tools/blender_env/paridad_v54.py \
      --dir /ruta/al/workspace/tools/blender
```

3. El arnés imprime un JSON con `ancho_m` y `holgura_m` medidos aquí, y los compara
   con la referencia (1,2974 m / −0,188 m): `COINCIDE` si la diferencia < 0,5 mm.
4. Si coinciden → **bpy 4.3.0 queda certificado como equivalente de medición**: puedo
   trabajar con él y sus resultados son válidos también para el equipo de vehículos.
5. Si difieren → reportar la delta y **no** usar bpy 4.3.0 para nada que afecte al
   maestro de la v54.

El arnés **no reimplementa** la medición: ejecuta el script del otro agente tal cual y
solo normaliza la salida. Si le falta el fichero, responde `{"status": "FALTA_FICHERO"}`
con la ruta que espera.
