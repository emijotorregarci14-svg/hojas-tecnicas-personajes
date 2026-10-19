"""
NOVU — Parámetros del vehículo.

TODAS las cotas y colores del taxi en un único sitio. Si cambia una medida,
cambia aquí y el modelo entero se reconstruye coherente.

Unidades: metros. Sistema: X = lateral (+X derecha), Y = longitudinal (+Y morro),
Z = vertical (0 = suelo). Origen: centro de la huella, en el suelo.

Cotas oficiales (hoja de catálogo NOVU TAXI FREE):
    longitud 2,60 · ancho 1,30 · altura 1,20 · batalla 1,80

Cotas de detalle medidas sobre la vista lateral de esa misma hoja
(escala real: 62,5 px/m, 1,20 m de altura = 75 px):
    línea de cintura      Z 0,64    base del parabrisas  Y +0,79
    techo (punto más alto) Z 1,19   frente del techo     Y +0,51
    pilar B               Y +0,14   pilar C              Y −0,56
    morro (punto más bajo) Z 0,51   portón trasero        Y −1,13
"""

# ---------------------------------------------------------------------------
# Cotas principales
# ---------------------------------------------------------------------------
LONGITUD = 2.60
ANCHO = 1.30
# El loft + subdivisión encoge la sección transversal ~2,2 %. Este factor
# compensa esa pérdida para que la anchura final sea exactamente 1,30 m.
# (Medido: w=0,650 -> 1,3146 m finales; 0,650 x 1,0041 -> 1,3000 m.)
F_ANCHO = 1.0041
ALTURA = 1.20
BATTALA = 1.80
RADIO_RUEDA = 0.275
ANCHURA_RUEDA = 0.205
RADIO_LLANTA = 0.196        # radio de la llanta
CENTRO_RUEDA_X = 0.525         # semidistancia entre ejes de rueda
# Ejes: en la vista lateral de la ficha el centro de la rueda delantera cae
# en Y +0,885 y el de la trasera en Y −1,004, con las ruedas pegadas a los
# extremos. La batalla oficial es 1,80 m, así que se reparten de forma
# asimétrica: +0,885 y −0,915.
CARRIL_RUEDA_Y = 0.90          # semidistancia nominal (batalla 1,80)
CARRIL_RUEDA_Y_FRENTE = 0.885
CARRIL_RUEDA_Y_TRAS = -0.915

# ---------------------------------------------------------------------------
# Paleta (catálogo NOVU). Valores lineales para Cycles.
# ---------------------------------------------------------------------------
COLOR_CARROCERIA = (0.95, 0.72, 0.05)      # amarillo taxi
COLOR_NEGRO = (0.020, 0.020, 0.024)        # piezas negras / molduras
COLOR_NEGRO_BRILLO = (0.011, 0.011, 0.014) # techo y piezas brillantes
COLOR_CRISTAL = (0.055, 0.060, 0.070)      # cristal gris oscuro
COLOR_CIAN = (0.10, 0.85, 0.95)            # LED cian
COLOR_ROJO = (0.85, 0.05, 0.04)            # pilotos traseros
COLOR_RUEDA = (0.018, 0.018, 0.018)
COLOR_LLANTA = (0.030, 0.030, 0.032)
COLOR_ASIENTO = (0.42, 0.34, 0.24)        # interior beige
COLOR_LED = (0.25, 0.95, 1.00)             # emisivo cian
COLOR_ROJO_EM = (1.00, 0.06, 0.04)         # emisivo rojo
COLOR_FONDO = (0.035, 0.035, 0.040)        # fondo del estudio

ALFA_CRISTAL = 0.80                         # cristal oscuro ahumado (catálogo)

# ---------------------------------------------------------------------------
# Secciones del cuerpo (loft a lo largo de Y)
#
# Cada estación define el perfil transversal del vehículo en ese punto:
#   y      posición longitudinal
#   w      semianchura en la línea de cintura (máximo)
#   w_top  semianchura en el borde de techo
#   w_bot  semianchura en el suelo
#   z_bot  altura del suelo de la carrocería
#   z_top  altura de la corona en esa estación
#   tag    marca para el reparto de materiales (vidrio, pilares, techo)
# ---------------------------------------------------------------------------
ESTACIONES = [
    # --- morro: gota corta y redondeada -------------------------------------
    dict(y=+1.300, w=0.505, w_top=0.330, w_bot=0.420, z_bot=0.335, z_top=0.560, tag="morro"),
    dict(y=+1.270, w=0.560, w_top=0.375, w_bot=0.470, z_bot=0.275, z_top=0.595, tag="morro"),
    dict(y=+1.220, w=0.612, w_top=0.420, w_bot=0.520, z_bot=0.220, z_top=0.618, tag="morro"),
    # --- capó: muy corto, sube hasta la base del parabrisas -----------------
    dict(y=+1.160, w=0.630, w_top=0.450, w_bot=0.538, z_bot=0.185, z_top=0.622, tag="capo"),
    dict(y=+1.090, w=0.645, w_top=0.488, w_bot=0.550, z_bot=0.168, z_top=0.632, tag="capo"),
    dict(y=+1.020, w=0.650, w_top=0.505, w_bot=0.556, z_bot=0.160, z_top=0.640, tag="cowl"),
    # --- parabrisas: muy inclinado (38 grados) ------------------------------
    dict(y=+0.950, w=0.650, w_top=0.525, w_bot=0.558, z_bot=0.158, z_top=0.700, tag="parabrisas"),
    dict(y=+0.870, w=0.650, w_top=0.540, w_bot=0.559, z_bot=0.158, z_top=0.780, tag="parabrisas"),
    dict(y=+0.790, w=0.650, w_top=0.550, w_bot=0.560, z_bot=0.158, z_top=0.860, tag="parabrisas"),
    dict(y=+0.710, w=0.650, w_top=0.556, w_bot=0.560, z_bot=0.158, z_top=0.940, tag="parabrisas"),
    dict(y=+0.630, w=0.650, w_top=0.560, w_bot=0.560, z_bot=0.158, z_top=1.020, tag="parabrisas"),
    dict(y=+0.560, w=0.650, w_top=0.562, w_bot=0.560, z_bot=0.158, z_top=1.095, tag="parabrisas"),
    dict(y=+0.485, w=0.650, w_top=0.545, w_bot=0.560, z_bot=0.158, z_top=1.180, tag="parabrisas"),
    # --- techo: largo y ligeramente abombado --------------------------------
    dict(y=+0.440, w=0.650, w_top=0.542, w_bot=0.560, z_bot=0.158, z_top=1.203, tag="techo"),
    dict(y=+0.340, w=0.650, w_top=0.541, w_bot=0.560, z_bot=0.158, z_top=1.207, tag="techo"),
    dict(y=+0.280, w=0.650, w_top=0.541, w_bot=0.560, z_bot=0.158, z_top=1.207, tag="pilar_b"),
    dict(y=+0.210, w=0.650, w_top=0.540, w_bot=0.560, z_bot=0.158, z_top=1.207, tag="pilar_b"),
    dict(y=+0.100, w=0.650, w_top=0.540, w_bot=0.560, z_bot=0.158, z_top=1.207, tag="techo"),
    dict(y=-0.100, w=0.650, w_top=0.540, w_bot=0.560, z_bot=0.158, z_top=1.207, tag="techo"),
    dict(y=-0.300, w=0.650, w_top=0.540, w_bot=0.560, z_bot=0.158, z_top=1.207, tag="techo"),
    dict(y=-0.450, w=0.650, w_top=0.540, w_bot=0.560, z_bot=0.158, z_top=1.207, tag="techo"),
    # --- pilar C ancho y ventanilla de cuarto --------------------------------
    dict(y=-0.550, w=0.650, w_top=0.540, w_bot=0.559, z_bot=0.158, z_top=1.200, tag="pilar_c"),
    dict(y=-0.650, w=0.650, w_top=0.538, w_bot=0.557, z_bot=0.160, z_top=1.180, tag="pilar_c"),
    dict(y=-0.780, w=0.648, w_top=0.520, w_bot=0.552, z_bot=0.166, z_top=1.165, tag="pilar_c"),
    # --- luna trasera y cola redondeada --------------------------------------
    dict(y=-0.860, w=0.640, w_top=0.522, w_bot=0.545, z_bot=0.175, z_top=1.150, tag="piloto_traseiro"),
    dict(y=-0.930, w=0.640, w_top=0.512, w_bot=0.538, z_bot=0.182, z_top=1.100, tag="piloto_traseiro"),
    dict(y=-1.010, w=0.634, w_top=0.500, w_bot=0.528, z_bot=0.192, z_top=1.030, tag="piloto_traseiro"),
    dict(y=-1.090, w=0.626, w_top=0.478, w_bot=0.512, z_bot=0.212, z_top=0.960, tag="cola"),
    dict(y=-1.160, w=0.610, w_top=0.450, w_bot=0.488, z_bot=0.245, z_top=0.880, tag="cola"),
    dict(y=-1.225, w=0.585, w_top=0.405, w_bot=0.450, z_bot=0.290, z_top=0.780, tag="cola"),
    dict(y=-1.270, w=0.550, w_top=0.355, w_bot=0.405, z_bot=0.335, z_top=0.700, tag="cola"),
    dict(y=-1.300, w=0.505, w_top=0.310, w_bot=0.378, z_bot=0.395, z_top=0.640, tag="cola"),
]

# Alturas clave del perfil transversal
# La línea de cintura (donde el amarillo se encuentra con el habitáculo
# negro) está en 0,623 m según la vista lateral de la ficha; el pliegue
# estructural de la sección va por debajo, en 0,52 m.
Z_CINTURA = 0.485       # pliegue vivo de la sección (máximo de anchura)
Z_CINTURA_VISIBLE = 0.623   # línea de cintura pintada (borde amarillo/negro)
Z_ROCKER = 0.300        # remate del zócalo negro
# Franja negra sobre el vidrio. En la vista lateral de la ficha el cristal
# llega hasta 0,98 m y de ahí al techo (1,20 m) hay una banda negra de 0,22 m.
MARCO_SUPERIOR = 0.240
# Cortes longitudinales de la banda de ventanillas (medidos en la vista lateral)
Y_VENTANA = 0.86           # borde delantero del hueco de ventanilla
Y_VENTANA_TRAS = -0.37     # borde trasero
Y_PILAR_B = (0.21, 0.28)   # pilar B (el de en medio)
Y_PILAR_A = 1.04           # por delante del pilar A está el capó
Y_PILAR_C = -0.62          # por detrás del pilar C está el cuarto trasero
Y_CUARTO = (-0.86, -0.62)  # ventanilla pequeña del cuarto trasero

# ---------------------------------------------------------------------------
# Elementos
# ---------------------------------------------------------------------------
# Letrero de techo "TAXI".
# Medido sobre la vista lateral de la hoja de catálogo (escala 66,0 px/m):
#   caja vista de lado  0,39 m de largo (x 460..482 px de la hoja)
#   caja vista de frente 0,43 m de ancho (hoja, vista trasera)
#   altura de la caja   0,12 m  -> corona en 1,337 m (16,6 cm sobre el techo)
#   palabra TAXI en negro, en la cara LATERAL y en la trasera
# La caja se apoya en el techo (1,20 m): no flota.
SIGN = dict(y=-0.013, z=1.200, ancho=0.420, fondo=0.390, alto=0.122,
            z_base=0.015, texto="TAXI",
            ancho_texto=0.330, alto_texto=0.067)

# Pod de sensor del techo trasero. En la ficha es una pieza negra y baja
# (0,17 m de largo) en el borde de la luna trasera, no un cubo cian.
LIDAR = dict(y=-0.855, z=1.150, lado=0.060, largo=0.170, alto=0.042)

# Tiras LED cian: frontal en las esquinas + continuidad por el costado
LED = dict(z=0.505, x=0.600, y0=+1.120, y1=+1.262, grosor=0.024, alto=0.024,
           x_frontal=0.275, y_frontal=1.288, largo_frontal=0.270)

# Pilotos traseros rojos (esquina trasera, verticales)
PILOTO = dict(x=0.420, y=-1.252, z0=0.395, z1=0.520, grosor=0.030, ancho=0.075)

# Parrilla frontal negra + rótulo NOVU
PARRILLA = dict(y=1.262, z0=0.330, z1=0.470, half_x=0.210)
Z_PARAGOLPES = 0.478         # por debajo de esta altura el morro es negro
Z_PARAGOLPES_TRAS = 0.285    # por debajo de esta altura la cola es negra
Z_LUNA = 0.760                # por encima de esta altura el porton es cristal

# Porton trasero: banda negra con NOVU, pilotos rojos y rotulo
PORTON = dict(y=-1.262, z=0.505, ancho=0.380, alto=0.085,
              rotulo_alto=0.044, rotulo_offset=0.060,
              piloto_x=0.225, piloto_ancho=0.130, piloto_alto=0.038,
              piloto_grosor=0.026, piloto_offset=0.058)

# Banda de damero (cenefa de cuadros bajo la ventanilla, justo bajo la
# línea de cintura de 0,623 m)
DAMERO = dict(z0=0.505, z1=0.585, y0=+0.800, y1=-0.620, x=0.655, lado=0.0425)

# Rótulo lateral "NOVU TAXI FREE."
# Medido en la vista lateral de la ficha: ocupa de Y +0,24 a Y −0,71
# (0,95 m de largo) con las mayúsculas entre Z 0,33 y Z 0,41.
ROTULO = dict(y=-0.190, z=0.367, alto=0.105, ancho=0.880,
              texto="NOVU TAXI FREE.")

# Retrovisores
RETROVISOR = dict(x=0.640, y=+0.760, z=0.720, ancho=0.075, alto=0.055, fondo=0.115)
