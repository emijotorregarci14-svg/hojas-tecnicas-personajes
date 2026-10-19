#!/usr/bin/env python3
"""
VER TEXTO  —  "ver" una imagen sin verla.

El otro agente no puede ver imágenes: sólo recibe texto. Este script convierte
la vista lateral de la ficha (o un render) en un MAPA DE CARACTERES con las
cotas en metros, de forma que la silueta, los colores y las proporciones se
puedan leer directamente en el terminal.

    python3 ver_texto.py FICHA  imagen.png  [--cols 150] [--zoom x0,x1,y0,y1]
    python3 ver_texto.py MODELO imagen.png  --escala 363.64

Leyenda:

    W  fondo blanco
    Y  amarillo taxi
    K  negro (techo, pilares, banda)
    G  gris medio
    g  gris claro (cristal)
    R  rojo
    C  cian
    S  beige (asiento)
    o  otro color
    .  sombra/borde duro

Cada fila lleva su altura en metros respecto a la línea de apoyo, calculada
con la escala indicada (o deducida de la spec 2,60 x 1,20 m si no se pasa).
"""
import sys

import numpy as np
from PIL import Image

FONDO = 232
SPEC_LARGO = 2.60
SPEC_ALTO = 1.20


def _escala(img, escala=None):
    """Devuelve (px_por_m, suelo_px) de una imagen."""
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    silueta = ~((r > FONDO) & (g > FONDO) & (b > FONDO))
    filas = np.nonzero(silueta.sum(axis=1) >= 3)[0]
    if len(filas) == 0:
        raise SystemExit("Sin silueta")
    suelo = int(filas.max())
    if escala is None:
        # escala deducida: el ancho de la silueta sobre la spec
        cuerpo = silueta.copy()
        cols = np.nonzero(cuerpo[suelo - int((suelo - filas.min()) * 0.3):].any(axis=0))[0]
        ancho = int(cols.max() - cols.min() + 1)
        escala = ancho / SPEC_LARGO
    return escala, suelo


def _clase(p):
    """Clasifica un píxel RGB en un carácter."""
    r, g, b = [int(v) for v in p]
    if r > 245 and g > 245 and b > 245:
        return "W"
    mx, mn = max(r, g, b), min(r, g, b)
    if mx < 60:
        return "K"
    if r > 120 and g > 85 and b < 110 and (r - b) > 50:
        return "Y"
    if r > 150 and g < 90 and b < 90:
        return "R"
    if b > 130 and g > 130 and r < 120:
        return "C"
    if r > 120 and g > 95 and b < 90 and (r - b) < 50:
        return "S"
    if mx - mn < 28:
        v = (r + g + b) / 3
        if v > 195:
            return "g"
        if v > 120:
            return "G"
        if v > 80:
            return "G"
        return "K"
    return "o"


def ver_texto(ruta, cols=150, escala=None, zoom=None, filas_marca=True):
    img = Image.open(ruta).convert("RGB")
    W, H = img.size
    if zoom:
        x0, x1, y0, y1 = zoom
        img = img.crop((x0, y0, x1, y1))
        W, H = img.size
    px_m, suelo = _escala(img, escala)
    a = np.asarray(img)
    # suelo recalculado dentro del recorte
    arr = a.astype(np.int16)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    sil = ~((r > FONDO) & (g > FONDO) & (b > FONDO))
    f = np.nonzero(sil.sum(axis=1) >= 3)[0]
    suelo = int(f.max()) if len(f) else H - 1

    paso_x = max(1, W // cols)
    paso_y = max(1, paso_x)
    print(f"# {ruta}")
    print(f"# {W}x{H} px   escala {px_m:.2f} px/m   suelo fila {suelo}")
    print("# " + "".join(
        str(int((x * paso_x) / px_m * 10) % 10) if (x * paso_x) % max(1, int(px_m / 10)) == 0
        else " " for x in range(0, W // paso_x)))
    print("# leyenda: W fondo  Y amarillo  K negro  G gris  g cristal claro  "
          "R rojo  C cian  S beige  o otro  . borde")
    print()
    for y in range(0, H, paso_y):
        linea = []
        for x in range(0, W, paso_x):
            bloque = arr[y:y + paso_y, x:x + paso_x].reshape(-1, 3)
            # color dominante del bloque por mediana
            med = np.median(bloque, axis=0)
            linea.append(_clase(med))
        if filas_marca:
            z = (suelo - y) / px_m
            etiqueta = f"{z:6.2f}"
        else:
            etiqueta = f"{y:6d}"
        print(f"{etiqueta} |{''.join(linea)}|")
    print(f"\n# eje X: cada {paso_x} px = {paso_x / px_m:.3f} m; "
          f"el coche mide {W / px_m:.2f} m de ancho en la imagen")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    modo = argv[0].upper()
    args, cols, escala, zoom = [], 150, None, None
    i = 1
    while i < len(argv):
        if argv[i] == "--cols":
            cols = int(argv[i + 1]); i += 2
        elif argv[i] == "--escala":
            escala = float(argv[i + 1]); i += 2
        elif argv[i] == "--zoom":
            z = [int(v) for v in argv[i + 1].split(",")]; i += 2
            zoom = (z[0], z[1], z[2], z[3])
        else:
            args.append(argv[i]); i += 1
    if not args:
        raise SystemExit("Falta la imagen")
    ver_texto(args[0], cols, escala, zoom)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
