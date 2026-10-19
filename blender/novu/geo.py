"""
NOVU — Utilidades de mallado.

Herramientas mínimas y reutilizables para construir el vehículo:
loft por secciones transversales, cajas redondeadas, cilindros, texto 3D y
operaciones de modificador (subdivisión, bisel, booleano, shrinkwrap).

Todo trabaja en metros, con +Y hacia el morro y +X a la derecha.
"""
import bpy
import bmesh
from math import cos, sin, pi
from mathutils import Vector


# ---------------------------------------------------------------------------
# Escena y objetos
# ---------------------------------------------------------------------------
def nueva_escena():
    """Vacía la escena y deja las unidades en metros."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    esc = bpy.context.scene
    esc.unit_settings.system = 'METRIC'
    esc.unit_settings.scale_length = 1.0
    esc.unit_settings.length_unit = 'METERS'
    return esc


def coleccion(nombre):
    """Crea (o recupera) una colección y la deja activa."""
    col = bpy.data.collections.get(nombre)
    if col is None:
        col = bpy.data.collections.new(nombre)
        bpy.context.scene.collection.children.link(col)
    return col


def objeto_en(coleccion, obj):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coleccion.objects.link(obj)
    return obj


def crear_malla(nombre, verts, faces, materiales, idx_por_cara=None, suave=True):
    """Crea un objeto de malla a partir de listas de vértices y caras.

    materiales: lista de materiales en el orden de índice.
    idx_por_cara: índice de material por cara (opcional).
    """
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(verts, [], faces)
    me.update()
    obj = bpy.data.objects.new(nombre, me)
    bpy.context.scene.collection.objects.link(obj)

    for m in materiales:
        me.materials.append(m)

    if suave:
        for poly in me.polygons:
            poly.use_smooth = True

    # Normales hacia fuera
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()

    # Los índices de material se asignan DESPUÉS del paso por bmesh, emparejando
    # cada polígono con su cara original por el conjunto de sus vértices.
    # (Asignarlos antes funciona solo si bmesh conserva el orden, que no está
    # garantizado: en el Cap y en el morph la cara se reordena y el material
    # acaba en la cara equivocada.)
    if idx_por_cara:
        mapa = {}
        for cara, idx in zip(faces, idx_por_cara):
            mapa[frozenset(cara)] = idx
        for poly in me.polygons:
            poly.material_index = mapa.get(frozenset(poly.vertices), 0)

    return obj


# ---------------------------------------------------------------------------
# Loft por secciones transversales
# ---------------------------------------------------------------------------
def perfil(est, z_cintura, z_rocker, n_puntos=20):
    """Perfil transversal de una estación: lista de (x, z) cerrada.

    Recorrido: centro del suelo → costado derecho → corona → costado izquierdo.
    20 puntos: 11 por la mitad derecha y su espejo.

    El perfil busca el "pod" de la flota NOVU: faldón que se abre poco hacia
    la cintura, hombro redondeado y techo bajo con corona plana.

    IMPORTANTE: x y z deben ser monótonos en la mitad derecha. Si la sección se
    dobla sobre sí misma, el loft deja de ser una superficie válida y el
    booleano de los pasos de rueda devuelve una malla vacía (el modelo
    desaparece sin error). `_validar_estacion` lo comprueba.
    """
    z_bot, z_top = est["z_bot"], est["z_top"]
    w, wt, wb = est["w"], est["w_top"], est["w_bot"]

    # Alturas del perfil, forzadas a un orden estricto
    z_roc = max(z_rocker, z_bot + 0.020)
    z_cint = min(max(z_cintura, z_roc + 0.010), z_top - 0.030)
    z_rail = min(max(z_top - 0.085, z_cint + 0.015), z_top - 0.008)
    # El vidrio ocupa la mayor parte de la banda: el marco negro queda
    # como una franja fina justo bajo el borde de techo.
    z_mid = z_cint + 0.85 * (z_rail - z_cint)
    z_corona = min(max(z_top - 0.022, z_rail + 0.006), z_top - 0.002)
    # Bucles de soporte en la cintura: mantienen vivo el pliegue de la
    # línea de cintura, que en la ficha de catálogo es una arista marcada.
    z_inf_cint = max(z_cint - 0.075, z_roc + 0.010)
    z_sup_cint = min(z_cint + 0.070, z_mid - 0.010)

    derecha = [
        (0.0, z_bot),                # 0  centro del suelo
        (wb * 0.68, z_bot),          # 1  suelo exterior
        (wb * 0.94, z_bot + 0.012),  # 2  esquina inferior
        (wb, z_roc),                 # 3  faldón (se abre)
        (w * 0.985, z_inf_cint),     # 4  soporte inferior de la cintura
        (w, z_cint),                 # 5  cintura (máximo) - pliegue vivo
        (w * 0.990, z_sup_cint),     # 6  soporte superior de la cintura
        (w * 0.960, z_mid),          # 7  mitad de la banda de vidrio
        (wt, z_rail),                # 8  borde de techo
        (wt * 0.80, z_corona),       # 9  hombro de corona
        (0.0, z_top),                # 10 corona
    ]
    izquierda = [(-x, z) for (x, z) in reversed(derecha[1:-1])]
    return derecha + izquierda


def _validar_estacion(est, anillo):
    """Comprueba que la sección no se dobla. Lanza error si es inválida.

    La x crece hasta la cintura y decrece después: lo que no puede hacer es
    decrecer antes de la cintura (el faldón se metería hacia dentro y la
    sección se doblaría sobre sí misma).
    """
    mitad = anillo[:len(anillo) // 2 + 1]
    cintura = max(range(len(mitad)), key=lambda k: mitad[k][0])
    for i in range(cintura):
        if mitad[i + 1][0] < mitad[i][0] - 1e-9:
            raise ValueError(
                f"perfil inválido en y={est['y']}: x decrece antes de la cintura "
                f"({mitad[i][0]:.3f} -> {mitad[i+1][0]:.3f})")
    for i in range(cintura, len(mitad) - 1):
        if mitad[i + 1][0] > mitad[i][0] + 1e-9:
            raise ValueError(
                f"perfil inválido en y={est['y']}: x crece tras la cintura "
                f"({mitad[i][0]:.3f} -> {mitad[i+1][0]:.3f})")
    for i in range(1, len(mitad) - 1):
        if mitad[i + 1][1] <= mitad[i][1] + 1e-9:
            raise ValueError(
                f"perfil inválido en y={est['y']}: z no monótona "
                f"({mitad[i][1]:.3f} -> {mitad[i+1][1]:.3f})")


def loft(estaciones, z_cintura, z_rocker, n_puntos=20, f_ancho=1.0):
    """Construye (vértices, caras) uniendo estaciones consecutivas.

    Devuelve también, para cada cara, la tupla (índice de segmento, i, i+1).

    `f_ancho` escala las semianchuras (w, w_top, w_bot) para compensar la
    pérdida de sección que introduce la subdivisión posterior.
    """
    verts, faces, meta = [], [], []
    for est in estaciones:
        est_es = dict(est)
        for clave in ("w", "w_top", "w_bot"):
            est_es[clave] = est[clave] * f_ancho
        anillo = perfil(est_es, z_cintura, z_rocker, n_puntos)
        _validar_estacion(est, anillo)
        for (x, z) in anillo:
            verts.append((x, est["y"], z))

    n = len(estaciones)
    for i in range(n - 1):
        for j in range(n_puntos):
            k = (j + 1) % n_puntos
            a = i * n_puntos + j
            b = i * n_puntos + k
            c = (i + 1) * n_puntos + k
            d = (i + 1) * n_puntos + j
            faces.append((a, b, c, d))
            meta.append((j, i, i + 1))

    # Tapas frontales y traseras (abanico desde el centro)
    for idx, centro_y in ((0, estaciones[0]["y"]), (n - 1, estaciones[-1]["y"])):
        base = idx * n_puntos
        zc = (estaciones[idx]["z_bot"] + estaciones[idx]["z_top"]) * 0.5
        verts.append((0.0, centro_y, zc))
        c_idx = len(verts) - 1
        for j in range(n_puntos):
            k = (j + 1) % n_puntos
            if idx == 0:
                faces.append((c_idx, base + k, base + j))
            else:
                faces.append((c_idx, base + j, base + k))
            meta.append((-1, idx, idx))

    return verts, faces, meta


# ---------------------------------------------------------------------------
# Primitivas
# ---------------------------------------------------------------------------
def caja_redondeada(nombre, centro, dim, radio, material=None, segmentos=4):
    """Caja con esquinas biseladas (el recurso base de las piezas pequeñas)."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=centro)
    obj = bpy.context.object
    obj.name = nombre
    obj.scale = (dim[0], dim[1], dim[2])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    if radio > 0:
        bev = obj.modifiers.new("bisel", 'BEVEL')
        bev.width = radio
        bev.segments = segmentos
        bev.limit_method = 'ANGLE'
        bev.angle_limit = 0.52
        bev.harden_normals = False

    if material:
        obj.data.materials.append(material)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def cilindro(nombre, radio, profundidad, centro, rotacion=(0, 0, 0),
             material=None, vertices=48, eje='X'):
    """Cilindro orientado; `eje` indica el eje del cilindro."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radio,
                                        depth=profundidad, location=centro)
    obj = bpy.context.object
    obj.name = nombre
    if eje == 'X':
        obj.rotation_euler = (0, rotacion[1], rotacion[2]) if False else (0, 1.5707963, 0)
    elif eje == 'Y':
        obj.rotation_euler = (1.5707963, 0, 0)
    else:
        obj.rotation_euler = (0, 0, 0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    bev = obj.modifiers.new("bisel", 'BEVEL')
    bev.width = min(radio * 0.12, 0.02)
    bev.segments = 3
    bev.limit_method = 'ANGLE'

    if material:
        obj.data.materials.append(material)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def revolucion(nombre, perfil, centro, material=None, segmentos=48, eje='X'):
    """Revoluciona un perfil 2D (pares (eje, radio)) alrededor de un eje.

    Sirve para piezas de sección circular constante o variable: neumático,
    llanta, bujes. `eje` indica el eje de revolución ('X' = ruedas).
    """
    verts, faces = [], []
    n = len(perfil)
    for s in range(segmentos):
        ang = 2 * pi * s / segmentos
        for (t, r) in perfil:
            verts.append((r * cos(ang), r * sin(ang), t))
    for s in range(segmentos):
        s2 = (s + 1) % segmentos
        for i in range(n):
            i2 = (i + 1) % n
            faces.append((s * n + i, s * n + i2, s2 * n + i2, s2 * n + i))
    obj = crear_malla(nombre, verts, faces, [material] if material else None)
    obj.location = centro
    if eje == 'X':
        obj.rotation_euler = (0, 1.5707963, 0)   # eje local Z -> eje X
    elif eje == 'Y':
        obj.rotation_euler = (1.5707963, 0, 0)
    return obj


def texto_3d(nombre, cuerpo, tam, centro, rotacion, material=None,
             extrude=0.004, align='CENTER'):
    """Texto convertido a malla (para rótulos y el letrero TAXI)."""
    bpy.ops.object.text_add(location=centro, rotation=rotacion)
    obj = bpy.context.object
    obj.name = nombre
    obj.data.body = cuerpo
    obj.data.size = tam
    obj.data.align_x = align
    obj.data.align_y = 'CENTER'
    obj.data.extrude = extrude
    obj.data.resolution_u = 6
    bpy.ops.object.convert(target='MESH')
    obj = bpy.context.object
    obj.name = nombre
    if material:
        obj.data.materials.append(material)
    return obj


# ---------------------------------------------------------------------------
# Modificadores
# ---------------------------------------------------------------------------
def subsurf(obj, niveles=3, render=None):
    m = obj.modifiers.new("subdivision", 'SUBSURF')
    m.levels = niveles
    m.render_levels = render if render is not None else niveles
    m.use_limit_surface = True
    return m


def shade_auto_smooth(obj, angulo=0.52):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.object.shade_auto_smooth(angle=angulo)
    except Exception:
        bpy.ops.object.shade_smooth()
    return obj


def booleano(obj, cortador, operacion='DIFFERENCE'):
    m = obj.modifiers.new("booleano", 'BOOLEAN')
    m.operation = operacion
    m.object = cortador
    m.solver = 'EXACT'
    return m


def shrinkwrap(obj, destino, eje='X', offset=0.006):
    """Proyecta el objeto sobre `destino` a lo largo de `eje` (para rótulos)."""
    m = obj.modifiers.new("shrinkwrap", 'SHRINKWRAP')
    m.target = destino
    m.wrap_method = 'PROJECT'
    m.use_project_x = (eje == 'X')
    m.use_project_y = (eje == 'Y')
    m.use_project_z = (eje == 'Z')
    m.use_negative_direction = True
    m.use_positive_direction = True
    m.offset = offset
    return m


def mover(objs, dx=0, dy=0, dz=0):
    for o in objs:
        o.location.x += dx
        o.location.y += dy
        o.location.z += dz
    return objs
