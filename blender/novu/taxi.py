"""
NOVU TAXI FREE — Construcción paramétrica del vehículo.

El cuerpo es un loft de secciones transversales (una por cota longitudinal)
con reparto de materiales por zona: carrocería amarilla, habitáculo negro,
cristal y marcos. Encima se montan ruedas con sus pasos, luces LED, letrero
de techo, rotulación y interior.

Todo sale de `params.py`: para cambiar el vehículo se cambian las cotas ahí.
"""
import bpy
import bmesh
import numpy as np
from math import cos, sin, pi

from . import params as P
from . import geo
from . import materiales as MAT

NOMBRE = "TAXI_FREE"


# ---------------------------------------------------------------------------
# Reparto de materiales del cuerpo
#
# El perfil tiene 20 puntos: 11 de la mitad derecha y su espejo.
#   0 suelo centro · 1 suelo exterior · 2 esquina inferior · 3 faldón
#   4 soporte de cintura · 5 cintura (pliegue) · 6 soporte superior
#   7 mitad de vidrio · 8 borde de techo · 9 hombro de corona · 10 corona
# La cara j del loft une el punto j con el j+1, así que:
#   caras 0,19 suelo · 1,18 zócalo · 2,17 bajos · 3,4,15,16 faldón
#   5,14 pliegue de cintura · 6,7,12,13 ventanilla · 8,9,11 marco de techo
#   10 corona
# ---------------------------------------------------------------------------
SUELO = {0, 19}                 # bajos ocultos
SILL = {1, 18}                  # zócalo negro bajo las puertas
LOWER = {2, 17}                 # esquina inferior amarilla
FLANK = {3, 4, 15, 16}          # faldón amarillo
CINTURA = {5, 14}               # pliegue vivo de la línea de cintura
GLASS_BAND = {6, 7, 12, 13}     # ventanilla lateral
RAIL = {8, 9, 11}               # marco superior y borde de techo
CROWN = {10}                    # corona (parabrisas / techo / luna trasera)

PILLARS = {"pilar_a", "pilar_b", "pilar_c"}
FRONT_ZONE = {"morro", "capo", "cowl"}
REAR_ZONE = {"cola", "piloto_traseiro"}
WINDSCREEN = {"pilar_a", "parabrisas"}


def _material_de_cara(seg, i, j, centro, estaciones):
    """Devuelve la clave de material de una cara del loft.

    Reparto de la hoja de catálogo: carrocería amarilla por debajo de la
    cintura, habitáculo negro por encima, con el cristal encastrado en los
    huecos de ventanilla y el frontal con su paragolpes negro.
    """
    tag_i = estaciones[i]["tag"]
    tag_j = estaciones[j]["tag"]
    tags = {tag_i, tag_j}
    cy, cz = centro[1], centro[2]

    # El pilar A: la transición del parabrisas al techo va siempre en negro
    if tags == {"parabrisas", "techo"}:
        return "M_ROOF"

    # Tapas de morro y cola (seg == -1): amarilla con paragolpes negro abajo
    if seg < 0:
        z_bot = estaciones[i]["z_bot"]
        if cz < z_bot + 0.070:
            return "M_MOLD"          # paragolpes
        return "M_BODY"

    if seg in SUELO or seg in SILL:
        return "M_MOLD"
    if seg in LOWER or seg in FLANK or seg in CINTURA:
        return "M_BODY"

    if seg in GLASS_BAND:
        # Por delante del pilar A esta el capó, por detrás del pilar C la cola
        if cy > P.Y_PILAR_A:
            return "M_BODY"
        if cy < P.Y_PILAR_C:
            if P.Y_CUARTO[0] <= cy <= P.Y_CUARTO[1]:
                return "M_GLASS"      # ventanilla del cuarto
            return "M_BODY"           # cola
        # Pilares C y B en negro
        if cy <= P.Y_VENTANA_TRAS:
            return "M_ROOF"
        if P.Y_PILAR_B[0] <= cy <= P.Y_PILAR_B[1]:
            return "M_ROOF"
        # Pilar A: desde el capó hasta el frente de la ventanilla
        if cy >= P.Y_VENTANA:
            return "M_ROOF"
        # Marco negro sobre el vidrio
        z_top = max(estaciones[i]["z_top"], estaciones[j]["z_top"])
        if z_top - cz < P.MARCO_SUPERIOR:
            return "M_ROOF"
        return "M_GLASS"

    if seg in RAIL:
        # Sobre el capó y la cola el marco se vuelve amarillo
        if tags & FRONT_ZONE:
            return "M_BODY"
        # El parabrisas llega hasta el hombro: su marco tambien es cristal
        if tags & WINDSCREEN:
            return "M_GLASS"
        return "M_ROOF"
    if seg in CROWN:
        if tags <= WINDSCREEN:
            return "M_GLASS"      # parabrisas
        if tags <= REAR_ZONE:
            return "M_GLASS"      # luna trasera
        if tags & FRONT_ZONE:
            return "M_BODY"       # capó amarillo
        return "M_ROOF"           # techo negro
    return "M_BODY"


def carroceria(mats):
    """Crea el cuerpo del vehículo con su reparto de materiales."""
    estaciones = P.ESTACIONES
    verts, faces, meta = geo.loft(estaciones, P.Z_CINTURA, P.Z_ROCKER, 20,
                                  f_ancho=P.F_ANCHO)

    # Centro de cada cara para aplicar reglas que dependen de la altura
    idx_por_cara = []
    for (seg, i, j), cara in zip(meta, faces):
        cx = sum(verts[v][0] for v in cara) / len(cara)
        cy = sum(verts[v][1] for v in cara) / len(cara)
        cz = sum(verts[v][2] for v in cara) / len(cara)
        clave = _material_de_cara(seg, i, j, (cx, cy, cz), estaciones)
        idx_por_cara.append(["M_BODY", "M_MOLD", "M_GLASS", "M_ROOF"].index(clave))

    orden = ["M_BODY", "M_MOLD", "M_GLASS", "M_ROOF"]
    cuerpo = geo.crear_malla(
        f"{NOMBRE}_carroceria", verts, faces,
        [mats[k] for k in orden], idx_por_cara)

    # Pasos de rueda: se recortan del flanco con cilindros booleanos
    for sy in (1, -1):
        for sx in (1, -1):
            cortador = geo.cilindro(
                f"_corte_{sx}_{sy}", P.RADIO_RUEDA + 0.045, 0.52,
                (sx * 0.545, sy * P.CARRIL_RUEDA_Y, P.RADIO_RUEDA),
                material=mats["M_MOLD"], vertices=40, eje='X')
            geo.booleano(cuerpo, cortador)
            cortador.hide_render = True
            cortador.hide_viewport = True

    geo.subsurf(cuerpo, niveles=2, render=3)
    geo.shade_auto_smooth(cuerpo, 0.55)
    return cuerpo


# ---------------------------------------------------------------------------
# Ruedas
# ---------------------------------------------------------------------------
def _radios(nombre, n_radios, radio, ancho, centro, material, angulo=0.0,
            grosor=0.026):
    """Radios de la llanta: prismas que van del buje al borde de la llanta.

    Se construyen ya en el plano de la rueda (eje X), así que `angulo` permite
    dibujar los cinco radios dobles de la llanta de la hoja de catálogo.
    """
    verts, faces = [], []
    cx, cy, cz = centro
    ancho_r = ancho * 0.5
    for k in range(n_radios):
        ang = angulo + 2 * pi * k / n_radios
        base = len(verts)
        # contorno del radio: (radio, desplazamiento lateral)
        contorno = [(0.048, -ancho_r), (radio, -ancho_r * 0.55),
                    (radio, ancho_r * 0.55), (0.048, ancho_r)]
        for dx in (-grosor * 0.5, grosor * 0.5):
            for (r, t) in contorno:
                verts.append((cx + dx,
                              cy + r * cos(ang) - t * sin(ang),
                              cz + r * sin(ang) + t * cos(ang)))
        b = base
        faces += [(b + 0, b + 1, b + 5, b + 4), (b + 1, b + 2, b + 6, b + 5),
                  (b + 2, b + 3, b + 7, b + 6), (b + 3, b + 0, b + 4, b + 7),
                  (b + 3, b + 2, b + 1, b + 0), (b + 4, b + 5, b + 6, b + 7)]
    return geo.crear_malla(nombre, verts, faces, [material])


def ruedas(mats):
    """Neumático, llanta y radios de las cuatro ruedas.

    Diseño de la ficha: neumático de flanco redondeado, llanta oscura con
    cinco radios dobles y buje central.
    """
    piezas = []
    r = P.RADIO_RUEDA
    w = P.ANCHURA_RUEDA
    rl = P.RADIO_LLANTA

    # Perfil del neumático: (eje, radio). El eje va de -w/2 a +w/2.
    perfil_neumatico = [
        (-w * 0.50, rl),          # bead interior
        (-w * 0.50, r * 0.80),
        (-w * 0.47, r * 0.90),
        (-w * 0.38, r * 0.975),
        (-w * 0.26, r),
        (w * 0.26, r),            # banda de rodadura
        (w * 0.38, r * 0.975),
        (w * 0.47, r * 0.90),
        (w * 0.50, r * 0.80),
        (w * 0.50, rl),
        (w * 0.42, rl * 0.97),    # interior del pneumatico
        (-w * 0.42, rl * 0.97),
    ]

    # Perfil de la llanta: cubo exterior y garganta interior.
    perfil_llanta = [
        (-w * 0.34, rl),
        (-w * 0.34, rl * 0.93),
        (w * 0.30, rl * 0.93),
        (w * 0.30, rl),
        (w * 0.30, rl * 0.62),    # frente de llanta
        (w * 0.24, rl * 0.58),
    ]

    for sy in (1, -1):
        for sx in (1, -1):
            x = sx * P.CENTRO_RUEDA_X
            y = sy * P.CARRIL_RUEDA_Y
            etiqueta = f"{sx}_{sy}"

            pneumatico = geo.revolucion(
                f"{NOMBRE}_neumatico_{etiqueta}", perfil_neumatico,
                (x, y, P.RADIO_RUEDA), material=mats["M_TIRE"],
                segmentos=48, eje='X')
            piezas.append(pneumatico)

            llanta = geo.revolucion(
                f"{NOMBRE}_llanta_{etiqueta}", perfil_llanta,
                (x, y, P.RADIO_RUEDA), material=mats["M_RIM"],
                segmentos=40, eje='X')
            piezas.append(llanta)

            disco = geo.cilindro(
                f"{NOMBRE}_disco_{etiqueta}", rl * 0.60, 0.030,
                (x + sx * w * 0.20, y, P.RADIO_RUEDA), material=mats["M_MOLD"],
                vertices=32, eje='X')
            piezas.append(disco)

            # Cinco radios dobles: el dibujo de la llanta de la hoja
            for k in range(5):
                for lado in (-1, 1):
                    ang = 2 * pi * k / 5 + lado * 0.16
                    radio = _radios(
                        f"{NOMBRE}_radio_{etiqueta}_{k}_{lado}", 1,
                        rl * 0.94, 0.052,
                        (x + sx * w * 0.22, y, P.RADIO_RUEDA), mats["M_RIM"],
                        angulo=ang)
                    piezas.append(radio)

            cubo = geo.cilindro(
                f"{NOMBRE}_cubo_{etiqueta}", 0.046, 0.070,
                (x + sx * w * 0.24, y, P.RADIO_RUEDA), material=mats["M_RIM"],
                vertices=20, eje='X')
            piezas.append(cubo)
    return piezas


# ---------------------------------------------------------------------------
# Luces
# ---------------------------------------------------------------------------
def luces(mats):
    """Tiras LED cian de posición y pilotos traseros."""
    piezas = []
    led = P.LED

    # Frontal: dos barras horizontales en las esquinas del morro
    for sx in (1, -1):
        barra = geo.caja_redondeada(
            f"{NOMBRE}_led_frontal_{sx}",
            (sx * (led["x_frente"] - 0.19), led["y_frente"] - 0.012, led["z"]),
            (0.38, led["grosor"], led["alto"]), 0.012, mats["M_LED_CIAN"], 3)
        piezas.append(barra)

    # Continuación por el costado
    for sx in (1, -1):
        largo = led["y1"] - led["y0"]
        barra = geo.caja_redondeada(
            f"{NOMBRE}_led_lateral_{sx}",
            (sx * led["x"], (led["y0"] + led["y1"]) * 0.5, led["z"]),
            (led["grosor"], largo, led["alto"]), 0.010, mats["M_LED_CIAN"], 3)
        piezas.append(barra)

    # Pilotos traseros
    for sx in (1, -1):
        piloto = geo.caja_redondeada(
            f"{NOMBRE}_piloto_{sx}",
            (sx * P.PILOTO["x"], P.PILOTO["y"] + 0.010,
             (P.PILOTO["z0"] + P.PILOTO["z1"]) * 0.5),
            (P.PILOTO["ancho"], P.PILOTO["grosor"], P.PILOTO["z1"] - P.PILOTO["z0"]),
            0.016, mats["M_LED_ROJO"], 3)
        piezas.append(piloto)
    return piezas


# ---------------------------------------------------------------------------
# Letrero de techo, LiDAR, rótulos
# ---------------------------------------------------------------------------
def letrero_techo(mats):
    s = P.SIGN
    piezas = []
    z_base = s["z"] + s.get("z_base", 0.015)

    base = geo.caja_redondeada(
        f"{NOMBRE}_letrero_base", (0.0, s["y"], z_base + 0.0075),
        (s["ancho"] * 0.88, s["fondo"], 0.015), 0.005, mats["M_MOLD"], 3)
    piezas.append(base)

    z_caja = z_base + 0.015
    caja = geo.caja_redondeada(
        f"{NOMBRE}_letrero_caja", (0.0, s["y"], z_caja + s["alto"] * 0.5),
        (s["ancho"], s["fondo"] * 1.2, s["alto"]), 0.016, mats["M_SIGN"], 4)
    piezas.append(caja)

    texto = geo.texto_3d(
        f"{NOMBRE}_letrero_texto", s["texto"], s["alto"] * 0.68,
        (0.0, s["y"] - s["fondo"] * 0.62, z_caja + s["alto"] * 0.5),
        (pi / 2, 0, pi), mats["M_TEXT"], extrude=0.002)
    piezas.append(texto)
    return piezas


def lidar(mats):
    l = P.LIDAR
    base = geo.caja_redondeada(
        f"{NOMBRE}_lidar_base", (0.0, l["y"], l["z"] + 0.008),
        (l["lado"] * 1.15, l["lado"] * 1.15, 0.016), 0.006, mats["M_MOLD"], 3)
    ventana = geo.caja_redondeada(
        f"{NOMBRE}_lidar", (0.0, l["y"], l["z"] + 0.016 + l["alto"] * 0.5),
        (l["lado"], l["lado"], l["alto"]), 0.006, mats["M_LED_CIAN"], 3)
    return [base, ventana]


def rotulo_lateral(mats, cuerpo):
    """«NOVU TAXI FREE.» proyectado sobre el flanco."""
    r = P.ROTULO
    piezas = []
    for sx in (1, -1):
        texto = geo.texto_3d(
            f"{NOMBRE}_rotulo_{sx}", r["texto"], r["alto"],
            (sx * 0.72, r["y"], r["z"]), (pi / 2, 0, pi / 2), mats["M_LIVERY"],
            extrude=0.004)
        geo.shrinkwrap(texto, cuerpo, eje='X', offset=0.006)
        piezas.append(texto)
    return piezas


def rotulo_novu(mats):
    """«NOVU» en la parrilla frontal."""
    texto = geo.texto_3d(
        f"{NOMBRE}_novu", "NOVU", 0.085, (0.0, P.PARRILLA["y"] - 0.010, 0.395),
        (pi / 2, 0, pi), mats["M_LED_CIAN"], extrude=0.003)
    return [texto]


def retrovisores(mats):
    r = P.RETROVISOR
    piezas = []
    for sx in (1, -1):
        brazo = geo.caja_redondeada(
            f"{NOMBRE}_retrovisor_brazo_{sx}", (sx * (r["x"] - 0.03), r["y"], r["z"]),
            (0.09, 0.05, 0.028), 0.010, mats["M_MOLD"], 3)
        carcasa = geo.caja_redondeada(
            f"{NOMBRE}_retrovisor_{sx}", (sx * (r["x"] + 0.02), r["y"], r["z"] + 0.015),
            (r["ancho"], r["fondo"], r["alto"]), 0.018, mats["M_MOLD"], 3)
        piezas += [brazo, carcasa]
    return piezas


# ---------------------------------------------------------------------------
# Interior (visible a través del cristal)
# ---------------------------------------------------------------------------
def interior(mats):
    piezas = []
    for sx in (1, -1):
        for yy in (0.36, -0.30):
            base = geo.caja_redondeada(
                f"{NOMBRE}_asiento_base_{sx}_{yy}", (sx * 0.30, yy, 0.455),
                (0.40, 0.38, 0.09), 0.030, mats["M_SEAT"], 3)
            respaldo = geo.caja_redondeada(
                f"{NOMBRE}_asiento_respaldo_{sx}_{yy}", (sx * 0.30, yy - 0.17, 0.640),
                (0.40, 0.10, 0.38), 0.030, mats["M_SEAT"], 3)
            piezas += [base, respaldo]
    salpicadero = geo.caja_redondeada(
        f"{NOMBRE}_salpicadero", (0.0, 0.66, 0.520),
        (1.05, 0.34, 0.16), 0.05, mats["M_MOLD"], 3)
    piezas.append(salpicadero)
    return piezas


# ---------------------------------------------------------------------------
# Ensamblado
# ---------------------------------------------------------------------------
def construir():
    """Construye el taxi completo y devuelve la lista de objetos."""
    geo.nueva_escena()
    mats = MAT.libreria()

    cuerpo = carroceria(mats)
    piezas = [cuerpo]
    piezas += ruedas(mats)
    piezas += luces(mats)
    piezas += letrero_techo(mats)
    piezas += lidar(mats)
    piezas += rotulo_lateral(mats, cuerpo)
    piezas += rotulo_novu(mats)
    piezas += retrovisores(mats)
    piezas += interior(mats)

    for obj in piezas:
        obj.select_set(False)
    return cuerpo, piezas, mats
