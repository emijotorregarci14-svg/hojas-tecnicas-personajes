#!/usr/bin/env python3
"""
MEDIR FICHA  —  herramienta portable de medición del NOVU TAXI FREE.

Un único criterio, aplicable por igual al RECORTE DE LA HOJA DE CATÁLOGO y al
RENDER DEL MODELO. Así dos agentes que trabajen en sandboxes distintos
obtienen cifras comparables sin discutir a ojo.

No necesita Blender. Sólo PIL + numpy:

    python3 medir_ficha.py COMPARAR  ficha.png  modelo.png  [--escala 363.64]
    python3 medir_ficha.py FICHA     ficha.png   [--dibujar salida.png]
    python3 medir_ficha.py MODELO    modelo.png  [--escala 363.64]

Criterios (idénticos en las dos imágenes):

  silueta   todo lo que no es fondo (blanco)
  cartel    mancha amarilla de la fila más alta (la caja TAXI). Se separa del
            resto: en la ficha va pegada al techo y en el modelo también
  suelo     última fila de la silueta = línea de apoyo
  techo     primera fila de la silueta (sin el cartel) cuyo ancho sea >= 25 %
            del ancho máximo: así se ignoran las piezas estrechas y
            salientes (cartel TAXI, pod de sensor, retrovisores)
  cintura   primera fila, desde el techo hacia abajo, con >= 30 % de amarillo
  extremos  borde delantero y trasero de la silueta

ESCALA — de dónde sale y por qué es honesta:

  * En el MODELO la escala se conoce exactamente: el render es ortográfico y
    el verificador la imprime (363,64 px/m con la cámara de referencia). Se
    pasa con --escala. Si no se pasa, la herramienta la deduce de la spec y
    lo avisa, porque entonces el error de largo queda oculto.

  * En la FICHA no hay escala metida en el dibujo, así que se ancla en la
    tabla de specs de la propia hoja de catálogo: 2,60 m de largo y 1,20 m de
    alto de carrocería. De ahí salen dos escalas:
        px/m horizontal = (x_max - x_min + 1) / 2.60
        px/m vertical   = (suelo - techo_carroceria) / 1.20
    y la herramienta imprime la comprobación de isotropía: si el dibujo
    técnico es coherente, ambas deben coincidir. La diferencia observada es
    de un 1,3 % (un píxel), es decir, la ficha está a escala.

  * La altura del cartel (1,332 m) sale de esa escala vertical. Si alguien
    discrepa, el --dibujar pinta sobre el recorte las filas detectadas
    (suelo, techo, techo del cartel) para que se puedan auditar a ojo.

Salida: texto con los píxeles crudos, la escala, los metros y — en COMPARAR —
la tabla de desviaciones modelo - ficha.

Autor: agente de vehículos (flota NOVU). Copia portable de blender/novu/medir.py
para que otros entornos puedan ejecutarla sin el paquete.
"""
import json
import sys

import numpy as np
from PIL import Image

FONDO = 232          # por encima de esto (en los 3 canales) se considera fondo
ANCHO_MIN = 0.25     # fracción del ancho máximo que define el techo

# Spec de la hoja de catálogo (tabla de specs de la propia hoja)
SPEC_LARGO = 2.60    # m
SPEC_ALTO = 1.20     # m  (altura de carrocería, sin el cartel TAXI)


# ---------------------------------------------------------------- máscaras --
def _mascaras(rgb, fondo=FONDO):
    r = rgb[..., 0].astype(np.int16)
    g = rgb[..., 1].astype(np.int16)
    b = rgb[..., 2].astype(np.int16)
    blanco = (r > fondo) & (g > fondo) & (b > fondo)
    silueta = ~blanco
    amarillo = silueta & (r > 140) & (g > 100) & (b < 130) & ((r - b) > 55)
    return silueta, amarillo


def _mancha_cartel(amarillo):
    """Mancha amarilla de la fila más alta: la caja TAXI del techo.

    Se toman las filas amarillas consecutivas (se permite un hueco de dos
    filas) desde la primera que tenga amarillo. En la ficha el cartel es la
    única mancha amarilla alta; en el modelo, igual.
    """
    filas = np.nonzero(amarillo.any(axis=1))[0]
    if len(filas) == 0:
        return np.zeros_like(amarillo)
    f0 = int(filas[0])
    f1 = f0
    vacias = 0
    for f in range(f0, amarillo.shape[0]):
        if amarillo[f].any():
            f1 = f
            vacias = 0
        else:
            vacias += 1
            if vacias > 2:
                break
    return amarillo[f0:f1 + 1].copy()


# ------------------------------------------------------------------ hitos ---
def medir(ruta, escala_h=None, escala_v=None, fondo=FONDO):
    """Mide los hitos de la vista lateral sobre una imagen.

    escala_h / escala_v: px por metro. Si no se dan, se deducen de la spec
    de catálogo (2,60 x 1,20 m) y se marca el resultado como 'deducida'.
    """
    img = Image.open(ruta).convert("RGB")
    a = np.asarray(img)
    silueta, amarillo = _mascaras(a, fondo)
    H, W = silueta.shape

    ancho_fila = silueta.sum(axis=1)

    filas = np.nonzero(ancho_fila >= 3)[0]
    if len(filas) == 0:
        raise SystemExit(f"ERROR: {ruta} no tiene silueta (fondo={fondo})")
    suelo = int(filas.max())
    techo_px = int(filas.min())

    # El cartel: mancha amarilla de arriba. Se aparta para no confundir su
    # anchura con la del techo de la carrocería.
    cartel_amarillo = _mancha_cartel(amarillo)
    cuerpo = silueta.copy()
    if cartel_amarillo.any():
        filas_c = np.nonzero(cartel_amarillo.any(axis=1))[0]
        cuerpo[filas_c.min():filas_c.max() + 1] &= ~cartel_amarillo[
            filas_c.min():filas_c.max() + 1]
    ancho_cuerpo = cuerpo.sum(axis=1)

    # Techo de la carrocería: primera fila ancha (se ignoran las piezas
    # estrechas y salientes: cartel, pod de sensor, retrovisores).
    umbral = ancho_cuerpo.max() * ANCHO_MIN
    techo_carroceria = suelo
    for f in range(techo_px, suelo + 1):
        if ancho_cuerpo[f] >= umbral:
            techo_carroceria = f
            break

    # Línea de cintura: primera fila (desde el techo) con amarillo abundante.
    # El amarillo del cartel se refleja en el techo negro, así que además de
    # medir la proporción de la fila se exige una mancha grande: el amarillo
    # de la carrocería, no el reflejo.
    amarillo_max = int(amarillo.sum(axis=1).max())
    cintura = None
    for f in range(techo_carroceria, suelo + 1):
        n_amar = int(amarillo[f].sum())
        if n_amar >= 0.30 * max(1, int(silueta[f].sum())) and \
                n_amar >= 0.25 * amarillo_max:
            cintura = f
            break

    # Extremos longitudinales, ignorando el cartel
    cols = np.nonzero(cuerpo[techo_carroceria:suelo + 1].any(axis=0))[0]
    x_min, x_max = int(cols.min()), int(cols.max())

    # Cartel: extensión horizontal de su mancha amarilla
    cartel_x = None
    cartel_alto_px = None
    if cartel_amarillo.any():
        cols_c = np.nonzero(cartel_amarillo.any(axis=0))[0]
        cartel_x = (int(cols_c.min()), int(cols_c.max()))
        filas_c = np.nonzero(cartel_amarillo.any(axis=1))[0]
        cartel_alto_px = int(filas_c.max() - filas_c.min() + 1)

    deducida = escala_h is None or escala_v is None
    if escala_h is None:
        escala_h = (x_max - x_min + 1) / SPEC_LARGO
    if escala_v is None:
        escala_v = (suelo - techo_carroceria) / SPEC_ALTO

    return dict(
        ruta=ruta, ancho_px=W, alto_px=H,
        suelo_px=suelo, techo_px=techo_px,
        techo_carroceria_px=techo_carroceria,
        cintura_px=cintura, x_min_px=x_min, x_max_px=x_max,
        cartel_x_px=cartel_x, cartel_alto_px=cartel_alto_px,
        px_por_m_h=escala_h, px_por_m_v=escala_v, escala_deducida=deducida,
        metros=dict(
            largo=(x_max - x_min + 1) / escala_h,
            alto_carroceria=(suelo - techo_carroceria) / escala_v,
            alto_con_cartel=(suelo - techo_px) / escala_v,
            cintura=((suelo - cintura) / escala_v) if cintura is not None else None,
            cartel_sobre_techo=(techo_carroceria - techo_px) / escala_v,
            cartel_largo=((cartel_x[1] - cartel_x[0] + 1) / escala_h)
            if cartel_x else None,
        ),
    )


# ----------------------------------------------------------------- salida ---
def _fmt(v, dec=3):
    return "  --  " if v is None else f"{v:{dec}f}"


def imprime(h, titulo):
    print(f"\n=== {titulo} ===")
    print(f"  fichero                 {h['ruta']}")
    print(f"  tamaño de la imagen     {h['ancho_px']} x {h['alto_px']} px")
    print(f"  suelo (línea de apoyo)  fila {h['suelo_px']}")
    print(f"  techo del cartel        fila {h['techo_px']}")
    print(f"  techo de carrocería     fila {h['techo_carroceria_px']}")
    print(f"  línea de cintura        fila {h['cintura_px']}")
    print(f"  extremos                x {h['x_min_px']} .. {h['x_max_px']}")
    if h['cartel_x_px']:
        print(f"  cartel (mancha amarilla) x {h['cartel_x_px'][0]} .. "
              f"{h['cartel_x_px'][1]}   alto {h['cartel_alto_px']} px")
    origen = "DEDUCIDA de la spec 2,60 x 1,20 m" if h['escala_deducida'] \
        else "medida (render ortográfico)"
    print(f"  escala                  {h['px_por_m_h']:.2f} px/m (h)   "
          f"{h['px_por_m_v']:.2f} px/m (v)   [{origen}]")
    if h['escala_deducida']:
        d = abs(h['px_por_m_h'] - h['px_por_m_v']) / h['px_por_m_v'] * 100
        print(f"  isotropía del dibujo    {d:.1f} % de diferencia entre ejes")
    m = h['metros']
    print("  --- en metros ---")
    print(f"    largo                  {_fmt(m['largo'])}")
    print(f"    alto de carrocería     {_fmt(m['alto_carroceria'])}")
    print(f"    alto con cartel TAXI   {_fmt(m['alto_con_cartel'])}")
    print(f"    línea de cintura       {_fmt(m['cintura'])}")
    print(f"    cartel sobre el techo  {_fmt(m['cartel_sobre_techo'])}")
    print(f"    cartel (largo planta)  {_fmt(m['cartel_largo'])}")


TABLA = [
    ("Largo total", "largo"),
    ("Alto de carrocería", "alto_carroceria"),
    ("Alto con cartel TAXI", "alto_con_cartel"),
    ("Línea de cintura", "cintura"),
    ("Cartel sobre el techo", "cartel_sobre_techo"),
    ("Cartel (largo en planta)", "cartel_largo"),
]


def tabla_comparativa(a, b):
    lineas = []
    for etiqueta, clave in TABLA:
        va = a["metros"].get(clave)
        vb = b["metros"].get(clave)
        if va is None or vb is None:
            lineas.append(f"  {etiqueta:24s}   ficha: {_fmt(va):>8s}   "
                          f"modelo: {_fmt(vb):>8s}   --")
            continue
        d = vb - va
        marca = "OK " if abs(d) <= 0.02 else ("~  " if abs(d) <= 0.05 else "!! ")
        lineas.append(f"  {etiqueta:24s}   ficha: {va:8.3f}   "
                      f"modelo: {vb:8.3f}   delta: {d:+6.3f} m  {marca}")
    return "\n".join(lineas)


def dibujar(h, salida):
    """Pinta sobre la imagen las filas detectadas, para poder auditarlas."""
    img = Image.open(h["ruta"]).convert("RGB")
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    W, H = img.size
    marcas = [
        (h["suelo_px"], (0, 160, 0), "SUELO"),
        (h["techo_carroceria_px"], (0, 90, 220), "TECHO CARROCERIA"),
        (h["techo_px"], (220, 0, 0), "TECHO DEL CARTEL"),
    ]
    if h["cintura_px"] is not None:
        marcas.append((h["cintura_px"], (200, 120, 0), "CINTURA"))
    for f, color, txt in marcas:
        d.rectangle([0, f, W, f], fill=color)
        d.text((4, max(0, f - 11)), txt, fill=color)
    d.rectangle([h["x_min_px"], 0, h["x_max_px"], H - 1],
                outline=(255, 0, 255), width=2)
    d.text((4, H - 13), f"{h['ruta']}  suelo f{h['suelo_px']}  "
                        f"techo f{h['techo_carroceria_px']}  "
                        f"cartel f{h['techo_px']}", fill=(255, 0, 255))
    img = img.resize((W * 2, H * 2), Image.LANCZOS)
    img.save(salida)
    print(f"  [dibujado] {salida}")


# ------------------------------------------------------------------- CLI ----
def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    modo = argv[0].upper()
    escala = None
    salida = None
    args = []
    i = 1
    while i < len(argv):
        if argv[i] == "--escala":
            escala = float(argv[i + 1]); i += 2
        elif argv[i] == "--dibujar":
            salida = argv[i + 1]; i += 2
        else:
            args.append(argv[i]); i += 1

    if modo in ("FICHA", "MODELO", "MEDIR"):
        if not args:
            raise SystemExit("Falta la imagen")
        h = medir(args[0], escala, escala)
        imprime(h, modo)
        if salida:
            dibujar(h, salida)
        print(json.dumps(h, indent=2, default=str))
        return 0

    if modo == "COMPARAR":
        if len(args) < 2:
            raise SystemExit("Uso: comparar FICHA.png MODELO.png")
        hf = medir(args[0])
        hm = medir(args[1], escala, escala)
        imprime(hf, "FICHA (recorte de la hoja de catálogo)")
        imprime(hm, "MODELO (render)")
        print("\n=== DESVIACIONES (modelo - ficha) ===")
        print(tabla_comparativa(hf, hm))
        return 0

    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
