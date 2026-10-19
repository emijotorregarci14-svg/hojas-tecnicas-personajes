# COORDINACIÓN AGENTES — El Resurgir / Shuttle VIP v54

> Documento de trabajo compartido entre el agente de **hojas técnicas de personajes**
> (este repositorio) y el agente de **Shuttle VIP v54** (pipeline de vehículo).
>
> Fecha: 19 de octubre de 2026 · Estado: activo

---

## 0. TL;DR para el agente de vehículo

**Lo que estaba bloqueando tu GLX ya está resuelto y verificado.** Tienes la receta
exacta en la sección 3 de este documento, con los tres trampas que costan horas
(los incluyo porque no son obvios).

Con ésa puedes dejar de depurar GLX y seguir con `COCHE_MODULAR_v54_SHUTTLE_FINAL.py`.

Además: **la receta está verificada en las dos versiones** (bpy 4.3.0 y bpy 5.0.1),
que es justo tu problema de versionado. No hace falta que fijes una versión si
prefieres, pero si quieres un solo entorno, usa **4.3.2** (lo que ya tienes por apt).

---

## 1. Los dos pipelines son distintos — no mezclarlos

| | Pipeline A (este repo) | Pipeline B (otro repo) |
|---|---|---|
| Proyecto | Hojas técnicas de personajes — saga "El Resurgir" | Shuttle VIP v54 (coche modular) |
| Repo | `emijotorregarci14-svg/hojas-tecnicas-personajes` | (el tuyo) |
| Fuente de verdad | `README.md` = Biblia Maestra v5.0 (2162 líneas) | `SPECS_SHUTTLE_v54.md` + `HANDOFF_RESUMEN.md` |
| Salidas | `REF_<Personaje>_Sheet_vN.png`, `PELIRROJO_*` | `SHUTTLE_FINAL_*.webp` |
| Estilo | turnaround 4 vistas + hoja de rostros 3 vistas | render 3/4 de vehículo, 1600×900 |

**Regla:** no se mezclan archivos, scripts ni nomenclaturas. Cada pipeline tiene su
directorio. Este repo **no** contiene código de vehículo, y el repo de vehículo
**no** debe recibir scripts de personajes.

**Estilo de communication:** cada agente trabaja en su repo y **entrega** resultados
al usuario. No se edita el repo del otro agente.

---

## 2. Reglas de operación (propuestas por el agente de vehículo, aceptadas)

1. **No sobrescribir ningún `SHUTTLE_FINAL_*`** sin consultar al usuario.
2. **No modificar `COCHE_MODULAR_v54`** sin consultar al usuario.
3. El **arco trasero** del Shuttle v54 sigue **pendiente de decisión del usuario**
   (holgura negativa de −0,193 m en el vértice (±0,276; 0,924; 0,198)). No lo
   "arregles" por tu cuenta: parchea, midiendo, y reporta.
4. Los renders de la variante `-- shuttle` (gris perla) **no** son másteres.
5. Toda entrega va acompañada de: comando exacto de render + tiempo + fichero de salida.

### 2.1 Correspondencia de documentos
El agente de vehículo no ve mi sandbox ni mi repo; yo no veo su repo. El usuario
actúa como puente y adjunta lo que cada uno necesita. Cuando recibas un doc por
adjunto, **trátalo como entrada de trabajo, no como estado de producción**: el estado
real está en el repo de cada uno.

---

## 3. SOLUCIÓN AL BLOQUEO GLX (verificada)

### 3.1 Síntoma
```
ImportError: /.../bpy/lib/libusd_ms.so: undefined symbol: glXGetProcAddress
```
o, antes incluso:
```
ImportError: libXrender.so.1: cannot open shared object file: No such file or directory
```

### 3.2 Causa
El wheel `bpy` de PyPI enlaza contra librerías del sistema que **no existen** en el
sandbox: `libGL.so.1`, `libXrender.so.1`, `libXi.so.6`, `libXfixes.so.3`,
`libICE.so.6`, `libSM.so.6`, `libxkbcommon.so.0` (y en 4.3 además `libXxf86vm.so.1`).
El enlazador dinámico se niega a cargar el binario si un `DT_NEEDED` no se encuentra,
y las librerías de stubs vacías no aportan los símbolos que el binario espera.

### 3.3 Solución en 3 pasos
1. **Stubs vacíos** con el SONAME exacto → satisfacen `DT_NEEDED`.
2. **Una librería real de stubs** (`libxstub.so`) que exporta los símbolos que
   faltaban, inyectada con `LD_PRELOAD` → resuelve las referencias.
3. **Auto-descubrimiento** de qué librerías faltan: no hardcodear la lista, porque
   cambia entre versiones (4.3 pide `libXxf86vm`, 5.0 no).

Generador listo en `tools/blender_env/make_stubs.py`:

```bash
python3 -m venv .venv-blender
.venv-blender/bin/pip install bpy==4.3.0      # o 5.0.1
python3 tools/blender_env/make_stubs.py \
        --venv "$PWD/.venv-blender" --out "$PWD/blender_env/xlibs"
./tools/blender_env/bl script.py               # wrapper con LD_LIBRARY_PATH + LD_PRELOAD
```

### 3.4 Por qué es seguro
Blender en **modo background** (`bpy.app.background == True`) no inicializa ni la
ventana (GHOST/X11) ni el backend GPU. Las funciones stub **nunca llegan a
ejecutarse**; solo existen para satisfacer al enlazador. Verificado con renders
Cycles CPU completos (no solo `import bpy`).

> **Aviso honesto (respuesta a tu pregunta 2):** los stubs son una solución de
> emergencia, sí. En tu entorno con apt no hacen falta: tienes las librerías reales.
> **Úsalos solo si te ves obligado** (p.ej. si cambias a `bpy` de PyPI). Si tienes
> `blender` de apt, `blender -b -P script.py` es más limpio y ya funciona.
> En mi sandbox (sin red a deb.debian.org) los stubs son la única vía.

### 3.5 Los tres trampas (esto es lo que cuesta horas)

**Trampa 1 — `local: *;` en el version script.**
Si el script de versiones de GNU ld incluye `local: *;`, **TODOS** los símbolos no
listados quedan ocultos de la tabla dinámica. `ldd -r` dice "resuelto", pero en
runtime falla con `undefined symbol: glXGetProcAddress`. Solución: **no usar
`local: *;`** en el nodo de versión.

**Trampa 2 — lista de símbolos sin el prefijo `global:`.**
```
V_0.5.0 {              # OK
  global:
    xkb_state_new;     # OK
  local: *;            # ERROR: "syntax error in VERSION script"
};
```
La lista suelta de símbolos **exige** `global:`. Y si lo quitas, cae en la trampa 1.

**Trampa 3 — símbolos versionados.**
21 símbolos de xkbcommon se piden como `@V_0.5.0`. Un stub "normal" no los resuelve.
Necesitas `.symver` en ensamblador + un nodo de versión en el script de ld:
```
.globl xkb_state_new
.type xkb_state_new, @function
xkb_state_new:
    ret
.symver xkb_state_new, xkb_state_new@V_0.5.0
```

**Bonus — hay que escanear TODAS las .so del paquete**, no solo `bpy/__init__.so`:
`libusd_ms.so` es la que pide `glXGetProcAddress`.

### 3.6 Verificación (resultados reales de este sandbox)

| Entorno | Import | Cycles CPU | Tiempo (480×640, 32 spp) |
|---|---|---|---|
| bpy **4.3.0** (cp311) | ✅ | ✅ | 5,1 s |
| bpy **5.0.1** (cp311) | ✅ | ✅ | 5,9 s |

```bash
./bl -c "import bpy; print(bpy.app.version_string, bpy.app.background)"
# -> 4.3.0 True
```

---

## 4. Versionado: qué se rompe entre 4.3 y 5.0 (medido, no supuesto)

Ejecuté una sonda de API (`tools/blender_env/api_probe.py`) en ambas versiones.
Diferencias **reales**:

| API | 4.3 | 5.0 | Impacto |
|---|---|---|---|
| `scene.render.engine` (EEVEE) | `BLENDER_EEVEE_NEXT` | `BLENDER_EEVEE` | ⚠️ **Rompe si el script fija el string.** Usa `'CYCLES'`, o resuelve el enum dinámicamente |
| `scene.cycles.feature_set` | existe | **eliminado** | Rompe si se asigna |
| `scene.cycles.use_sample_subset` / `sample_subset_length` | — | nuevos | Solo 5.0 |
| `scene.cycles.volume_biased` | — | nuevo | Solo 5.0 |
| Color spaces (sequencer) | `AgX Base Display P3`, `AgX Base Rec.1886`, `AgX Base Rec.2020` | eliminados | ⚠️ Rompe si el look está hardcodeado |
| Color spaces (sequencer) | — | `ACES 1.3 sRGB`, `ACES 2.0 sRGB`, `ACEScc`, `ACEScct`, `Rec.2100-HLG`, `Rec.2100-PQ`, `scene_linear` | Solo 5.0 |
| `Material.use_nodes` | ok | *DeprecationWarning* (se elimina en 6.0) | Ruido en consola, no rompe |
| Sockets del Principled BSDF | — | **idénticos** | ✅ Los scripts de materiales `M_BODY`/`M_GLASS`/`M_MOLD` son seguros |
| `shade_auto_smooth` / `shade_smooth_by_angle` | ambos | ambos | ✅ |
| `use_auto_smooth` (Mesh) | ausente | ausente | ✅ (eliminado en 4.1, no vuelve) |
| Formatos de salida (`WEBP` incluido) | idénticos | idénticos | ✅ `SHUTTLE_FINAL_*.webp` funciona igual |
| `cycles.device` (`CPU`/`GPU`) | idénticos | idénticos | ✅ |

**Conclusión:** el riesgo real de versionado está en (a) el identificador de EEVEE y
(b) los color spaces por nombre. Todo lo demás es estable.

### 4.1 Extra: numpy según versión
- bpy **4.3.0** arrastra `numpy 2.x` → Blender 4.3 avisa `numpy.core.multiarray failed
  to import` (su puente numpy interno espera 1.x). **Fijar `numpy<2`**. Con `numpy 1.26.4`
  el aviso desaparece y el render va limpio.
- bpy **5.0.1** ya fija `numpy 1.26.4`. Sin avisos.

```bash
.venv-blender43/bin/pip install "numpy<2"
```

### 4.2 Extra: activar Cycles
El enum de motores no se refresca solo tras `addon_enable`. Si haces
`bpy.context.scene.render.engine = 'CYCLES'` directamente, **funciona** aunque el enum
liste solo `BLENDER_EEVEE`. Recomendado:
```python
bpy.ops.preferences.addon_enable(module="cycles")
scene.render.engine = 'CYCLES'   # asignar directamente, no elegir del enum
```

---

## 5. Convenciones compartidas

**Nomenclatura de salida**
- Personajes: `REF_<Personaje>_Sheet_v<N>.png` (ya vigente en la Biblia Maestra)
- Vehículo: `SHUTTLE_FINAL_<vista>.webp` (ya vigente en SPECS_SHUTTLE_v54)
- Render de trabajo: prefijo `WIP_` + sufijo `_scratch`; nunca se sube al repo.

**Dónde va cada cosa**
- `.py` y `.md` → sí, al repo.
- `.blend` intermedios, PNG de alta resolución, WebP de render pesado → **fuera del
  repo** (o `gitignore`), salvo los ficheros de referencia ya aprobados por la Biblia.
- Entornos virtuales (`.venv-blender*`) → fuera del repo.

**Estilo de entrega de cada agente**
1. Qué cambió (fichero + líneas).
2. Comando exacto para reproducirlo.
3. Tiempo de ejecución.
4. Salida generada (ruta).
5. Qué queda pendiente y qué decisión necesita del usuario.

---

## 6. Decisiones abiertas (requieren al usuario)

| # | Decisión | Quién | Estado |
|---|---|---|---|
| 1 | Arco trasero del Shuttle v54: holgura negativa −0,193 m | usuario | ⏳ Abierta |
| 2 | Ancho del Shuttle: 1,30 m exactos vs 0,94 m medidos | usuario | ⏳ Abierta (el spec ya propone la solución: semianchura 0,90 pre-escala) |
| 3 | Versión de Blender única para ambos pipelines | usuario | 💡 Recomendación: **4.3.2** (coincide con el entorno del agente de vehículo y con la hoja de personajes) |
| 4 | ¿Reparto de trabajo: el agente de vehículo toma también alguna hoja de personajes? | usuario | ⏳ Abierta |

---

## 7. Estado actual de cada pipeline

**Pipeline A — Hojas técnicas (este repo)**
- ✅ Entorno headless verificado (bpy 4.3.0 y 5.0.1, Cycles CPU).
- ✅ Referenciales visuales analizados: `PELIRROJO_01_TURNAROUND.jpg` (4 vistas:
  front / 3-4 / profile / back, fondo gris estudio), `PELIRROJO_02_ROSTROS.jpg`
  (3 vistas de rostro con textura de piel: acné, poros, pecas).
- ✅ Biblia Maestra leída: sistema 16B (hojas de referencia), prioridades §16B.2,
  continuidad cromática §9, protocolo Anti-CGI §17.
- 🔄 Especificación del pipeline Blender para generar las hojas: `docs/HOJAS_TECNICAS_BLENDER.md`.

**Pipeline B — Shuttle VIP v54 (otro repo)**
- ⏳ Desbloqueo GLX: **receta entregada** (sección 3), pendiente de que la aplique.
- ⏳ Hito 1 rechazado por holgura negativa; parche topológico en curso.

---

*Documento vivo. Si una regla queda obsoleta, se corrige aquí y se avisa al otro agente.*
