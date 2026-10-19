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
# (Medido: w=0,650 -> 1,2802 m finales; 0,650 x 1,0154 -> 1,3000 m.)
F_ANCHO = 1.0154
ALTURA = 1.20
BATTALA = 1.80
RADIO_RUEDA = 0.275
ANCHURA_RUEDA = 0.205
RADIO_LLANTA = 0.196        # radio de la llanta
CENTRO_RUEDA_X = 0.525         # semidistancia entre ejes de rueda
CARRIL_RUEDA_Y = 0.90          # semidistancia entre ejes (batalla 1,80)

# ---------------------------------------------------------------------------
# Paleta (catálogo NOVU). Valores lineales para Cycles.
# ---------------------------------------------------------------------------
COLOR_CARROCERIA = (0.95, 0.72, 0.05)      # amarillo taxi
COLOR_NEGRO = (0.020, 0.020, 0.024)        # piezas negras / molduras
COLOR_NEGRO_BRILLO = (0.030, 0.030, 0.036) # techo y piezas brillantes
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
    dict(y=+1.300, w=0.470, w_top=0.300, w_bot=0.395, z_bot=0.320, z_top=0.540, tag="morro"),
    dict(y=+1.270, w=0.540, w_top=0.350, w_bot=0.450, z_bot=0.270, z_top=0.575, tag="morro"),
    dict(y=+1.220, w=0.600, w_top=0.405, w_bot=0.505, z_bot=0.215, z_top=0.605, tag="morro"),
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
    dict(y=+0.485, w=0.650, w_top=0.545, w_bot=0.560, z_bot=0.158, z_top=1.175, tag="parabrisas"),
    # --- techo: largo y ligeramente abombado --------------------------------
    dict(y=+0.440, w=0.650, w_top=0.542, w_bot=0.560, z_bot=0.158, z_top=1.196, tag="techo"),
    dict(y=+0.340, w=0.650, w_top=0.541, w_bot=0.560, z_bot=0.158, z_top=1.200, tag="techo"),
    dict(y=+0.280, w=0.650, w_top=0.541, w_bot=0.560, z_bot=0.158, z_top=1.200, tag="pilar_b"),
    dict(y=+0.210, w=0.650, w_top=0.540, w_bot=0.560, z_bot=0.158, z_top=1.200, tag="pilar_b"),
    dict(y=+0.100, w=0.650, w_top=0.540, w_bot=0.560, z_bot=0.158, z_top=1.200, tag="techo"),
    dict(y=-0.100, w=0.650, w_top=0.540, w_bot=0.560, z_bot=0.158, z_top=1.200, tag="techo"),
    dict(y=-0.300, w=0.650, w_top=0.540, w_bot=0.560, z_bot=0.158, z_top=1.200, tag="techo"),
    dict(y=-0.450, w=0.650, w_top=0.540, w_bot=0.560, z_bot=0.158, z_top=1.200, tag="techo"),
    # --- pilar C ancho y ventanilla de cuarto --------------------------------
    dict(y=-0.550, w=0.650, w_top=0.540, w_bot=0.559, z_bot=0.158, z_top=1.195, tag="pilar_c"),
    dict(y=-0.650, w=0.650, w_top=0.538, w_bot=0.557, z_bot=0.160, z_top=1.175, tag="pilar_c"),
    dict(y=-0.780, w=0.648, w_top=0.520, w_bot=0.552, z_bot=0.166, z_top=1.160, tag="pilar_c"),
    # --- luna trasera y cola redondeada --------------------------------------
    dict(y=-0.860, w=0.640, w_top=0.522, w_bot=0.545, z_bot=0.175, z_top=1.150, tag="piloto_traseiro"),
    dict(y=-0.930, w=0.636, w_top=0.510, w_bot=0.538, z_bot=0.182, z_top=1.100, tag="piloto_traseiro"),
    dict(y=-1.010, w=0.628, w_top=0.490, w_bot=0.528, z_bot=0.192, z_top=1.020, tag="piloto_traseiro"),
    dict(y=-1.090, w=0.612, w_top=0.455, w_bot=0.512, z_bot=0.212, z_top=0.900, tag="cola"),
    dict(y=-1.160, w=0.588, w_top=0.415, w_bot=0.488, z_bot=0.245, z_top=0.780, tag="cola"),
    dict(y=-1.225, w=0.550, w_top=0.360, w_bot=0.450, z_bot=0.288, z_top=0.650, tag="cola"),
    dict(y=-1.270, w=0.505, w_top=0.305, w_bot=0.405, z_bot=0.330, z_top=0.545, tag="cola"),
    dict(y=-1.300, w=0.455, w_top=0.255, w_bot=0.365, z_bot=0.372, z_top=0.450, tag="cola"),
]

# Alturas clave del perfil transversal
Z_CINTURA = 0.660       # línea de cintura: base de las ventanillas
Z_ROCKER = 0.300        # remate del zócalo negro
MARCO_SUPERIOR = 0.105  # franja negra sobre el vidrio
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
# Letrero de techo.
# Altura total del conjunto: 1,277 m (carrocería 1,20 m + cartel 7,7 cm), la misma
# convención que el máster del taxi v38: la cota "1,20 m" de la ficha es la altura
# de carrocería, no la altura con accesorios. La ilustración de la hoja dibuja el
# cartel algo más alto (~11% del total), pero manda la convención del máster.
SIGN = dict(y=-0.040, z=1.200, ancho=0.400, alto=0.062, fondo=0.070,
            texto="TAXI", color=COLOR_CARROCERIA, z_base=0.015)

# Módulo LiDAR (cuadrado cian del techo)
LIDAR = dict(y=+0.020, z=1.202, lado=0.075, alto=0.020)

# Tiras LED cian: frontal en las esquinas + continuidad por el costado
LED = dict(z=0.455, x=0.630, y0=+0.980, y1=+1.245, grosor=0.028, alto=0.028,
           x_frente=0.520, y_frente=1.290)

# Pilotos traseros rojos (esquina trasera, verticales)
PILOTO = dict(x=0.520, y=-1.268, z0=0.470, z1=0.680, grosor=0.032, ancho=0.085)

# Parrilla frontal negra + rótulo NOVU
PARRILLA = dict(y=1.292, z0=0.320, z1=0.540, half_x=0.250)

# Banda de damero (cenefa de cuadros bajo la ventanilla)
DAMERO = dict(z0=0.545, z1=0.630, y0=+0.760, y1=-0.980, x=0.648, lado=0.055)

# Rótulo lateral "NOVU TAXI FREE."
ROTULO = dict(y=-0.130, z=0.400, alto=0.115, texto="NOVU TAXI FREE.")

# Retrovisores
RETROVISOR = dict(x=0.640, y=+0.760, z=0.720, ancho=0.075, alto=0.055, fondo=0.115)
