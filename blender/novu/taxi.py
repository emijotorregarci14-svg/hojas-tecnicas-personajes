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

    # Paragolpes: negro por debajo de la linea de faros, en todo el morro
    if tags & FRONT_ZONE and cz < P.Z_PARAGOLPES:
        return "M_MOLD"
    # Paragolpes trasero: la cola se cierra en negro por debajo
    if tags & {"cola"} and cz < P.Z_PARAGOLPES_TRAS:
        return "M_MOLD"
    # Banda negra del porton con la marca NOVU
    if tags & {"cola"} and abs(cz - P.PORTON["z"]) < P.PORTON["alto"] * 0.5:
        return "M_MOLD"

    # Tapas de morro y cola (seg == -1)
    if seg < 0:
        z_bot = estaciones[i]["z_bot"]
        if cz < z_bot + 0.070:
            return "M_MOLD"          # paragolpes bajo
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
            if cz > P.Z_LUNA:
                return "M_GLASS"      # luna trasera
            return "M_BODY"           # porton amarillo
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
        if tags <= {"piloto_traseiro"}:
            return "M_GLASS"      # luna trasera
        if tags & FRONT_ZONE:
            return "M_BODY"       # capó amarillo
        if tags & REAR_ZONE:
            return "M_ROOF"        # parte alta del porton (negra)
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
            y_rueda = (P.CARRIL_RUEDA_Y_FRENTE if sy > 0
                       else P.CARRIL_RUEDA_Y_TRAS)
            # El paso abraza el neumático: en la ficha el arco queda a
            # centimetros del flanco, no con un hueco de 4,5 cm.
            cortador = geo.cilindro(
                f"_corte_{sx}_{sy}", P.RADIO_RUEDA + 0.022, 0.52,
                (sx * 0.545, y_rueda, P.RADIO_RUEDA),
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
            y = (P.CARRIL_RUEDA_Y_FRENTE if sy > 0
                 else P.CARRIL_RUEDA_Y_TRAS)
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
            (sx * led["x_frontal"], led["y_frontal"], led["z"]),
            (led["largo_frontal"], led["grosor"], led["alto"]), 0.012,
            mats["M_LED_CIAN"], 3)
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
    """Caja de techo con la palabra TAXI, como en la hoja de catálogo.

    La caja se apoya en el techo y lleva el texto negro en las dos caras
    laterales (se lee en la vista lateral) y en las dos frontales (se lee en
    la vista trasera).
    """
    s = P.SIGN
    piezas = []
    z_base = s["z"]

    base = geo.caja_redondeada(
        f"{NOMBRE}_letrero_base", (0.0, s["y"], z_base + s["z_base"] * 0.5),
        (s["ancho"] * 0.86, s["fondo"] * 0.86, s["z_base"]), 0.005,
        mats["M_MOLD"], 3)
    piezas.append(base)

    z_caja = z_base + s["z_base"]
    caja = geo.caja_redondeada(
        f"{NOMBRE}_letrero_caja", (0.0, s["y"], z_caja + s["alto"] * 0.5),
        (s["ancho"], s["fondo"], s["alto"]), 0.016, mats["M_SIGN"], 4)
    piezas.append(caja)

    # Texto: se estira en el sentido de la lectura hasta el ancho de la hoja
    tam = s["alto_texto"] / 0.72        # alto_texto es el alto de las mayusculas
    for sx in (1, -1):
        texto = geo.texto_3d(
            f"{NOMBRE}_letrero_texto_{sx}", s["texto"], tam,
            (sx * (s["ancho"] * 0.5 + 0.003), s["y"], z_caja + s["alto"] * 0.5),
            (pi / 2, 0, sx * pi / 2), mats["M_TEXT"], extrude=0.002)
        xs = [v.co.x for v in texto.data.vertices]
        ancho = max(xs) - min(xs)
        if ancho > 1e-6:
            texto.scale.x = s["ancho_texto"] / ancho
        piezas.append(texto)

    for sy in (1, -1):
        texto = geo.texto_3d(
            f"{NOMBRE}_letrero_texto_y{sy}", s["texto"], tam,
            (0.0, s["y"] + sy * (s["fondo"] * 0.5 + 0.003), z_caja + s["alto"] * 0.5),
            (pi / 2, 0, pi if sy > 0 else 0), mats["M_TEXT"], extrude=0.002)
        xs = [v.co.x for v in texto.data.vertices]
        ancho = max(xs) - min(xs)
        if ancho > 1e-6:
            texto.scale.x = s["ancho_texto"] / ancho
        piezas.append(texto)
    return piezas


def lidar(mats):
    """Pod de sensor del techo trasero (pieza negra y baja, como en la ficha)."""
    l = P.LIDAR
    base = geo.caja_redondeada(
        f"{NOMBRE}_lidar_base", (0.0, l["y"], l["z"] + 0.008),
        (l["lado"] * 1.1, l["largo"] * 1.05, 0.016), 0.006, mats["M_MOLD"], 3)
    ventana = geo.caja_redondeada(
        f"{NOMBRE}_lidar", (0.0, l["y"], l["z"] + 0.016 + l["alto"] * 0.5),
        (l["lado"], l["largo"] * 0.92, l["alto"]), 0.010, mats["M_MOLD"], 3)
    return [base, ventana]


def banda_cuadros(mats, cuerpo):
    """Cenefa de cuadros negro y amarillo proyectada sobre el flanco.

    Va justo bajo la línea de cintura, como en la hoja de catálogo, y es la
    banda que separa el habitáculo negro de la rotulación de las puertas.
    """
    d = P.DAMERO
    lado = d["lado"]
    y0, y1 = d["y0"], d["y1"]
    z0, z1 = d["z0"], d["z1"]
    n_y = max(1, int(round((y0 - y1) / lado)))
    n_z = max(1, int(round((z1 - z0) / lado)))
    dy = (y0 - y1) / n_y
    dz = (z1 - z0) / n_z

    piezas = []
    for sx in (1, -1):
        verts, faces, idx = [], [], []
        for j in range(n_z):
            for i in range(n_y):
                base = len(verts)
                ya = y0 - i * dy
                yb = ya - dy
                za = z0 + j * dz
                zb = za + dz
                for (yy, zz) in ((ya, za), (ya, zb), (yb, zb), (yb, za)):
                    verts.append((sx * d["x"], yy, zz))
                faces.append((base, base + 1, base + 2, base + 3))
                idx.append(0 if (i + j) % 2 == 0 else 1)
        obj = geo.crear_malla(
            f"{NOMBRE}_cuadros_{sx}", verts, faces,
            [mats["M_LIVERY"], mats["M_BODY"]], idx)
        geo.shrinkwrap(obj, cuerpo, eje='X', offset=0.004)
        piezas.append(obj)
    return piezas


def rotulo_lateral(mats, cuerpo):
    """«NOVU TAXI FREE.» proyectado sobre el flanco.

    El texto se estira en el sentido de la lectura hasta el ancho medido en la
    ficha (0,95 m), porque la rotulación del catálogo es ancha y baja.
    """
    r = P.ROTULO
    piezas = []
    for sx in (1, -1):
        texto = geo.texto_3d(
            f"{NOMBRE}_rotulo_{sx}", r["texto"], r["alto"],
            (sx * 0.72, r["y"], r["z"]), (pi / 2, 0, sx * pi / 2),
            mats["M_LIVERY"], extrude=0.004)
        xs = [v.co.x for v in texto.data.vertices]
        ancho = max(xs) - min(xs)
        if ancho > 1e-6 and r.get("ancho"):
            texto.scale.x = r["ancho"] / ancho
        geo.shrinkwrap(texto, cuerpo, eje='X', offset=0.006)
        piezas.append(texto)
    return piezas


def rotulo_novu(mats):
    """«NOVU» en la parrilla frontal."""
    texto = geo.texto_3d(
        f"{NOMBRE}_novu", "NOVU", 0.062, (0.0, P.PARRILLA["y"] + 0.042, 0.402),
        (pi / 2, 0, pi), mats["M_PLACA"], extrude=0.003)
    return [texto]


def porton(mats, cuerpo):
    """Porton trasero: banda negra con la marca NOVU, pilotos y rotulo.

    Todo se proyecta sobre la cola con shrinkwrap, porque el porton es una
    superficie curva y no un plano.
    """
    p = P.PORTON
    piezas = []

    texto = geo.texto_3d(
        f"{NOMBRE}_porton_novu", "NOVU", p["alto"] * 0.78,
        (0.0, p["y"] - 0.030, p["z"]), (pi / 2, 0, 0), mats["M_PLACA"],
        extrude=0.003)
    geo.shrinkwrap(texto, cuerpo, eje='Y', offset=0.0, sentido='neg')
    texto.location.y -= 0.007
    piezas.append(texto)

    # Rotulo "NOVU TAXI FREE." sobre el porton amarillo
    rot = geo.texto_3d(
        f"{NOMBRE}_porton_rotulo", "NOVU TAXI FREE.", p["rotulo_alto"],
        (0.0, p["y"] - 0.030, p["z"] - p["rotulo_offset"]), (pi / 2, 0, 0),
        mats["M_LIVERY"], extrude=0.003)
    geo.shrinkwrap(rot, cuerpo, eje='Y', offset=0.0, sentido='neg')
    rot.location.y -= 0.007
    piezas.append(rot)

    # Pilotos rojos horizontales a los lados
    for sx in (1, -1):
        piloto = geo.caja_redondeada(
            f"{NOMBRE}_porton_piloto_{sx}",
            (sx * p["piloto_x"], p["y"] - 0.010, p["z"] + p["piloto_offset"]),
            (p["piloto_ancho"], p["piloto_grosor"], p["piloto_alto"]), 0.012,
            mats["M_LED_ROJO"], 3)
        geo.shrinkwrap(piloto, cuerpo, eje='Y', offset=0.0, sentido='neg')
        piloto.location.y -= 0.008
        piezas.append(piloto)
    return piezas


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
    piezas += banda_cuadros(mats, cuerpo)
    piezas += rotulo_lateral(mats, cuerpo)
    piezas += rotulo_novu(mats)
    piezas += porton(mats, cuerpo)
    piezas += retrovisores(mats)
    piezas += interior(mats)

    for obj in piezas:
        obj.select_set(False)
    return cuerpo, piezas, mats
