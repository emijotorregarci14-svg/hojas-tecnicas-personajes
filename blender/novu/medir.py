"""
NOVU — Medición de hitos sobre una imagen.

Define un ÚNICO criterio de medida, aplicable por igual al render del modelo y a
la imagen de referencia de la hoja de catálogo. Así la comparación es objetiva
y repetible: el mismo script mide los dos y da la tabla de desviaciones.

Criterios (los mismos en las dos imágenes):

  silueta      todo lo que no es fondo
  cartel       mancha amarilla de la fila más alta (la caja TAXI). Se separa
               del resto: en la ficha va pegada al techo y en el modelo flota
  suelo        última fila de la silueta = línea de apoyo
  techo        primera fila de la silueta (sin el cartel) cuyo ancho sea
               >= 25 % del ancho máximo: así se ignoran las piezas estrechas
               y salientes (cartel TAXI, pod de sensor)
  cintura      primera fila, desde el techo hacia abajo, con >= 30 % de
               amarillo = línea de cintura
  extremos     borde delantero y trasero de la silueta

Uso:
    from blender.novu import medir
    h = medir.hitos_de_imagen("ruta.png", px_por_m_h=..., px_por_m_v=...)
"""
import numpy as np
from PIL import Image

FONDO = 232          # por encima de esto (en los 3 canales) seConsidera fondo
ANCHO_MIN = 0.25     # fracción del ancho máximo que define el techo


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


def hitos_de_imagen(ruta, px_por_m_h=None, px_por_m_v=None, fondo=FONDO):
    """Mide los hitos de la vista lateral sobre una imagen.

    px_por_m_h / px_por_m_v: escala. Si no se dan, se deduce de la propia
    imagen suponiendo 2,60 m de largo y 1,20 m de techo (lo que hace la ficha).
    """
    img = Image.open(ruta).convert("RGB")
    a = np.asarray(img)
    silueta, amarillo = _mascaras(a, fondo)
    H, W = silueta.shape

    ancho_fila = silueta.sum(axis=1)

    filas = np.nonzero(ancho_fila >= 3)[0]
    if len(filas) == 0:
        return None
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

    # Ruedas: en la banda inferior, el ancho de la silueta cae (pasos de rueda)
    banda = suelo - max(4, int((suelo - techo_carroceria) * 0.12))
    bajo = silueta[banda:suelo + 1]
    ancho_bajo = bajo.sum(axis=0)
    huecos = [x for x in range(x_min, x_max + 1) if ancho_bajo[x] == 0]
    grupos = []
    for x in huecos:
        if grupos and x == grupos[-1][1] + 1:
            grupos[-1][1] = x
        else:
            grupos.append([x, x])

    # Largo del cartel en planta: extensión horizontal de su mancha amarilla
    cartel_x = None
    if cartel_amarillo.any():
        cols_c = np.nonzero(cartel_amarillo.any(axis=0))[0]
        cartel_x = (int(cols_c.min()), int(cols_c.max()))

    if px_por_m_h is None:
        px_por_m_h = (x_max - x_min + 1) / 2.60
    if px_por_m_v is None:
        px_por_m_v = (suelo - techo_carroceria) / 1.20

    return dict(
        ruta=ruta, ancho_px=W, alto_px=H,
        suelo_px=suelo, techo_px=techo_px, techo_carroceria_px=techo_carroceria,
        cintura_px=cintura, x_min_px=x_min, x_max_px=x_max,
        cartel_x_px=cartel_x,
        px_por_m_h=px_por_m_h, px_por_m_v=px_por_m_v,
        metros=dict(
            largo=(x_max - x_min + 1) / px_por_m_h,
            alto_carroceria=(suelo - techo_carroceria) / px_por_m_v,
            alto_con_cartel=(suelo - techo_px) / px_por_m_v,
            cintura=((suelo - cintura) / px_por_m_v) if cintura else None,
            cartel_sobre_techo=(techo_carroceria - techo_px) / px_por_m_v,
            cartel_largo=((cartel_x[1] - cartel_x[0] + 1) / px_por_m_h)
            if cartel_x else None,
        ),
        grupos_huecos=grupos,
    )


def tabla_comparativa(hito_ficha, hito_modelo):
    """Devuelve la tabla de desviaciones entre la ficha y el modelo."""
    filas = [
        ("Largo total", "largo"),
        ("Alto de carrocería", "alto_carroceria"),
        ("Alto con cartel TAXI", "alto_con_cartel"),
        ("Línea de cintura", "cintura"),
        ("Cartel sobre el techo", "cartel_sobre_techo"),
        ("Cartel (largo en planta)", "cartel_largo"),
    ]
    lineas = []
    for etiqueta, clave in filas:
        a = hito_ficha["metros"].get(clave)
        b = hito_modelo["metros"].get(clave)
        if a is None or b is None:
            lineas.append(f"  {etiqueta:24s}   ficha: {str(a):>8s}   "
                          f"modelo: {str(b):>8s}   —")
            continue
        d = b - a
        marca = "OK " if abs(d) <= 0.02 else ("~  " if abs(d) <= 0.05 else "!! ")
        lineas.append(f"  {etiqueta:24s}   ficha: {a:8.3f}   modelo: {b:8.3f}   "
                      f"delta: {d:+6.3f} m  {marca}")
    return "\n".join(lineas)
