# HOJAS TÉCNICAS EN BLENDER — Especificación del pipeline

> Cómo se construyen, con Blender + Python, las **hojas de referencia de personajes**
> de la saga "El Resurgir" con el mismo lenguaje visual que las hojas ya generadas con IA.
>
> Especificación abierta. Cambios de formato → actualizar este documento + la Biblia Maestra.

---

## 1. Qué estamos construyendo

La Biblia Maestra (§16B) define que la IA genera personajes inconsistentes entre escenas
y que las **hojas de referencia** (character reference sheets) eliminan esa variabilidad:
una guía visual única por personaje, con 4 bloques en un mismo grid limpio.

Estado actual: 4 hojas generadas con IA y **aprobadas**
(`REF_Mercenario_Sheet_v1.png`, `REF_LineaNC_Vagon_Sheet_v1.png`,
`REF_Joven_Perros_Sheet_v1.png`, `REF_Vigilante_Sheet_v1.png`).

**El problema que resuelve este pipeline:** esas hojas son *imágenes*. No se pueden
reusar para renderizar, no se pueden variantear de forma consistente (vestuario nuevo,
expresión nueva, pose nueva) y no son editables.

**El objetivo:** regenerar el mismo tipo de hoja de forma **paramétrica y reproducible**
en Blender: un script con los parámetros del personaje produce la hoja exacta, y cambiar
`vestimenta` o `expresión` produce una variante coherente sin redibujar nada.

> **Nota de alcance:** el pipeline Blender produce la **hoja de trabajo geométrica y
> tonal** (silueta, proporciones, color de vestimenta, encuadre, iluminación de estudio).
> La **textura de piel fotorrealista** (acné, poros, pecas) sigue siendo territorio de la
> IA generativa o de fotografía; no se pretende competir ahí. El Blender da la estructura
> y la verdad de color; la IA (o una textura) da la carne.

---

## 2. Formato de referencia (medido sobre las hojas existentes)

### 2.1 Turnaround de cuerpo completo — `PELIRROJO_01_TURNAROUND.jpg`
- **4 vistas**: front (0°), 3/4 (≈45°), profile (90°), back (180°).
- **Fondo**: gris estudio muy claro, plano, sin horizonte, con sombra de contacto suave
  bajo los pies (no sombra dura).
- **Encuadre**: figura completa de cabeza a pies, centrada verticalmente, con aire
  arriba y abajo; las 4 figuras en fila, separadas.
- **Luz**: suave, envolvente, ligeramente superior y frontal. Sin contraluz duro.
- **Color de ropa**: fiel a la paleta de la Biblia (§9), sin saturación digital.

### 2.2 Hoja de rostros — `PELIRROJO_02_ROSTROS.jpg`
- **3 vistas**: front (0°), 3/4 (≈30–35°), profile (90°).
- **Encuadre**: cabeza y hombros (el cuello entra en cuadro), fondo liso igual.
- **Nivel de detalle**: piel real — acné, poros, pecas, vello. Es el bloque que más
  diferencia la hoja de una maqueta.

---

## 3. Parámetros de personaje (fuente única de verdad)

Todos los personajes se describen con el mismo diccionario. Cada entrada va a
`personajes/<slug>.py` y solo contiene datos — nunca lógica.

```python
CHAR = {
    "slug": "pelirrojo",
    "nombre": "El Joven de los Perros",
    "altura_m": 1.78,                 # altura total, coronilla a suela
    "proporciones": {
        "cabeza_ancho": 0.152,        # m
        "cabeza_alto": 0.196,         # m
        "hombro_ancho": 0.44,         # m (biacromático)
        "caderas_ancho": 0.34,        # m
        "longitud_brazo": 0.60,       # m
        "longadura_pierna": 0.86,     # m
    },
    "piel": {
        "base_color": [0.78, 0.64, 0.57],   # subtono rosado (Biblia §39)
        "roughness": 0.52,
        "specular": 0.32,
        "subsurface": 0.12,
    },
    "cabello": {
        "color": [0.62, 0.29, 0.13],        # cobrizo (Biblia §39)
        "roughness": 0.38,
        "forma": "ondulado_hacia_atras",    # volumen, no pegado
    },
    "vestimenta": [
        {"slug": "bomber", "color": [0.69, 0.69, 0.69],   # Stone Grey #B0B0B0
         "roughness": 0.78, "metallic": 0.0},
        {"slug": "camiseta", "color": [0.93, 0.93, 0.92], "roughness": 0.85},
        {"slug": "pantalon", "color": [0.10, 0.10, 0.11], "roughness": 0.80},
        {"slug": "zapatos", "color": [0.14, 0.14, 0.15], "roughness": 0.62},
    ],
    "atrezzo": ["catalogo_biopet_blanco_mate"],
    "pose": "neutra_manos_relajadas",
}
```

### 3.1 Paleta oficial (Biblia Maestra §9)
Los colores van por **hex de la Biblia**, convertidos a lineal antes de entrar en
Blender (sRGB → lineal), nunca en float directo.

| Elemento | Hex | Nota |
|---|---|---|
| Obsidian Black | `#0B0B0B` | ropa del Mercenario |
| Charcoal Grey | `#36454F` | abrigo del Ejecutivo NC |
| Polished Chrome Silver | `#C0C0C0` | maletín |
| Deep Blue | `#00008B` | asientos del vagón |
| Amber Gold | `#FFBF00` | glow ámbar |
| Stone Grey | `#B0B0B0` | bomber del Joven |
| Platinum White | `#E5E4E2` | traje del Kingpin |
| Burnt Sienna / Olive Drab / Ash Grey | | paleta del Vigilante |

**Regla de continuidad cromática (§24):** todo material con color definido en la Biblia
usa su hex exacto. Un color no aprobado en la Biblia es un error, no una decisión de render.

---

## 4. Arquitectura del pipeline

```
tools/blender_env/         entorno verificado (bpy headless + stubs)
blender/
  personajes/<slug>.py     DATOS puros del personaje (sin lógica)
  lib/
    materiales.py           sRGB→lineal, creación de materiales, naming M_*
    cuerpo.py               malla paramétrica (torso, miembros, cabeza)
    rigs_turnaround.py      cámara en órbita + encuadres por vista
    estudio.py              fondo, luces, settings Cycles, anti-CGI
    hoja.py                 composición del grid y exportación
    cli.py                  argparse: --personaje --vistas --salida --muestras
  generar_hoja.py           script principal (invocado por cli.py)
```

### 4.1 Principio de separación
- **Datos** (`personajes/*.py`): qué es el personaje. Editable por el usuario sin tocar código.
- **Motor** (`blender/lib/*.py`): cómo se construye y se renderiza. No conoce a ningún
  personaje concreto.
- **Salida**: `REF_<Personaje>_Sheet_v<N>.png` + `REF_<Personaje>_params.json`
  (la ficha de parámetros, para poder reconstruir la hoja).

Esto es lo que hace que la variante de vestimenta sea trivial (§16B.4 de la Biblia:
"hoja base del rostro + vestimenta nueva referenciando la hoja base").

---

## 5. Cámaras y vistas

Una única cámara en órbita, 4 (o 3) posiciones por hoja.

| Vista | Ángulo Y | Altura cámara | Focal (mm) | Uso |
|---|---|---|---|---|
| `front` | 0° | 0,95 × altura | 85 | plano frontal |
| `three_quarter` | 45° | 0,95 × altura | 85 | 3/4 (default) |
| `profile` | 90° | 0,95 × altura | 85 | perfil |
| `back` | 180° | 0,95 × altura | 85 |Reverso |
| `face_front` | 0° | altura de ojos | 100 | hoja de rostros |
| `face_3q` | 32° | altura de ojos | 100 | hoja de rostros |
| `face_profile` | 90° | altura de ojos | 100 | hoja de rostros |

- Focal largo (85–100 mm) → perspectiva de retrato, sin deformación de bordes.
- `ortho_scale` solo para el turnaround del vehículo (no para personas).
- **Encuadre**: la figura se normaliza para ocupar el ~88 % de la altura del encuadre,
  con el suelo en la línea inferior. Se calcula, no se fija a ojo.

---

## 6. Estudio (iluminación y render)

Objetivo: **luz de estudio, no render de videojuego.**

- **Fondo**: plano curva (`Sweep` / cyclorama) en gris muy claro, o `World` con
  gradiente. Sin horizonte visible.
- **Luz clave**: `AREA` grande (≈2 m) a 45° arriba-frontal, con `size` grande → sombra suave.
- **Relleno**: `AREA` opuesta, intensidad ≈25–35 % de la clave.
- **Contraluz/borde**: `AREA` trasera suave, ≈20 % → separa la silueta del fondo.
- **Sombra de contacto**: Cycles con `use_fast_gi` desactivado y muestras altas; nunca
  un plano flotante sin sombra (delata el 3D).
- **Cycles CPU**: `samples` 128 base (256 para la hoja de rostros), `use_denoising` ON.
- **Gestión de color**: `view_transform = 'AgX'`, `look = 'AgX - Medium Contrast'`
  (verificar el nombre exacto en la versión: cambió entre 4.3 y 5.0 → ver
  `COORDINACION_AGENTES.md` §4).
- **Salida**: PNG 16-bit o 8-bit sRGB, fondo sin transparencia (o alpha si se pide).

### 6.1 Protocolo Anti-CGI (Biblia §17)
Lo que hay que dañar a propósito para que no parezca un render:
- grano fino (o se resuelve en post con LUT de la Biblia)
- leve aberración cromática y viñeteado muy sutil en post
- micro-imperfecciones: la ropa no es perfecta, el pelo tiene fly-aways
- **nunca**: `smooth skin`, `perfect symmetry`, `airbrushed`

---

## 7. Reglas de malla

- **No usar `Subdivision Surface` como atajo**: la malla base debe ser legible
  (anillos de control) y el suavizado se hace con `shade_auto_smooth` / `shade_smooth_by_angle`.
- **Escala real en metros**: el pipeline trabaja en unidades = metros, `scene.unit_settings`.
- **Nombre de objetos**: `<personaje>_<pieza>` en snake_case (p. ej. `pelirrojo_bomber_cuerpo`).
- **Materiales**: `M_<PIE>` en mayúsculas, coincidente con la nomenclatura del pipeline
  de vehículo (`M_BODY`, `M_GLASS`, `M_MOLD`) para que ambos pipelines compartan criterio.
- **Modifiers**: no aplicar; dejarlos en vivo y parametrizados (no destructivo = re-editable).

---

## 8. Composición de la hoja (grid)

- 4 vistas en fila para el turnaround; 3 en fila para rostros.
- Separación constante calculada a partir del ancho del panel.
- Fondo idéntico y continuo entre paneles (se renderiza en un solo pase o se compone
  con fondo uniforme plano).
- **Sin** texto, marcas de agua, números de vista ni logos sobre la imagen
  (las hojas son de referencia, no de presentación).
- Exportar además la versión con guías/etiquetas en `WIP_*` para revisión interna.

---

## 9. Flujo de trabajo

1. Editar `blender/personajes/<slug>.py` (solo datos).
2. `python blender/generar_hoja.py --personaje pelirrojo --vistas front,3q,profile,back`
3. Revisar el `WIP_` en el visor.
4. Ajustar parámetros (no la malla).
5. Versionar: `REF_<Personaje>_Sheet_v<N>.png` + `REF_<Personaje>_params.json`.
6. Registrar en `README.md` (Biblia Maestra §19, tabla de archivos de referencia).

---

## 10. Criterios de aceptación

Una hoja se acepta si:
- [ ] Las 4/3 vistas están en el mismo plano de suelo y a la misma escala entre sí.
- [ ] La silueta frontal coincide con la hoja IA aprobada (comparación lado a lado).
- [ ] Los colores coinciden con el hex de la Biblia (diferencia ΔE por debajo del umbral acordado).
- [ ] No hay sombras duras ni "look" de render.
- [ ] Los ficheros de salida tienen la nomenclatura de la Biblia y el `.json` de parámetros.
- [ ] El comando de regeneración está documentado en la entrega.

---

## 11. Orden de trabajo (propuesta)

| Prioridad | Personaje | Hoja | Nota |
|---|---|---|---|
| 1 | Pelirrojo (Joven de los Perros) | turnaround + rostros | Ya hay 2 referencias IA: sirve de ground truth |
| 2 | El Mercenario | turnaround + rostros | §16B.2 prioridad 1 🔴; rostro revelado, "Impoluto" |
| 3 | El Vigilante | turnaround | adulto del protagonista, con chihuahua |
| 4 | El Ejecutivo NC | turnaround | nunca se ve el rostro: turnaround sin cara |
| 5 | Objetos: Catálogo Bio-Pet, Maletín | hoja de objeto | §16B.4 (objetos también) |

---

*Especificación viva. Cualquier deviation debe anotarse aquí con su motivo.*
