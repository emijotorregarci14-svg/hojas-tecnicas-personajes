"""
NOVU — Estudio de render.

Iluminación de producto, fondos y cámaras. Dos modos de fondo:
  - "estudio"  : degradado oscuro, como el héroe de la hoja de catálogo
  - "tecnico"  : fondo blanco, como el panel VISTAS TÉCNICAS
"""
import bpy
from math import radians, sin, cos
from mathutils import Vector

from . import params as P

VISTAS = {
    #  nombre        azimut  elev   distancia  focal   encuadre
    "heroi":      dict(az=38, el=13, dist=7.6, focal=85, aim=(0, 0.00, 0.60)),
    "heroi_atras": dict(az=215, el=14, dist=7.6, focal=85, aim=(0, 0.00, 0.60)),
    "tres_cuartos": dict(az=62, el=16, dist=7.2, focal=85, aim=(0, 0.00, 0.60)),
    "frontal":    dict(az=0, el=7, dist=8.4, focal=100, aim=(0, 0.00, 0.60)),
    "trasera":    dict(az=180, el=8, dist=8.4, focal=100, aim=(0, 0.00, 0.60)),
    "lateral":    dict(az=90, el=0, dist=12.0, focal=120, aim=(0, 0.00, 0.60)),
    "superior":   dict(az=0, el=88, dist=8.0, focal=85, aim=(0, 0.00, 0.60)),
    # Detalles: primero plano del letrero y del frontal
    "detalle_letrero": dict(az=8, el=18, dist=1.6, focal=85, aim=(0, -0.04, 1.25)),
    "detalle_frontal": dict(az=22, el=12, dist=2.2, focal=85, aim=(0, 1.05, 0.45)),
    "detalle_trasero": dict(az=186, el=10, dist=2.0, focal=85, aim=(0, -1.05, 0.52)),
}


# ---------------------------------------------------------------------------
# Fondo
# ---------------------------------------------------------------------------
def _degradado_oscuro():
    mundo = bpy.data.worlds.get("MUNDO") or bpy.data.worlds.new("MUNDO")
    bpy.context.scene.world = mundo
    mundo.use_nodes = True
    nt = mundo.node_tree
    nt.nodes.clear()

    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    fondo = nt.nodes.new("ShaderNodeBackground")
    salida = nt.nodes.new("ShaderNodeOutputWorld")

    ramp.color_ramp.elements[0].position = 0.10
    ramp.color_ramp.elements[0].color = (0.004, 0.004, 0.005, 1)
    ramp.color_ramp.elements[1].position = 0.92
    ramp.color_ramp.elements[1].color = (0.055, 0.056, 0.064, 1)

    coord.location = (-800, 0)
    sep.location = (-600, 0)
    ramp.location = (-400, 0)
    fondo.location = (-150, 0)
    salida.location = (50, 0)

    nt.links.new(coord.outputs["Window"], sep.inputs[0])
    nt.links.new(sep.outputs["Y"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], fondo.inputs["Color"])
    nt.links.new(fondo.outputs["Background"], salida.inputs["Surface"])
    return mundo


def _fondo_blanco():
    mundo = bpy.data.worlds.get("MUNDO") or bpy.data.worlds.new("MUNDO")
    bpy.context.scene.world = mundo
    mundo.use_nodes = True
    nt = mundo.node_tree
    nt.nodes.clear()
    fondo = nt.nodes.new("ShaderNodeBackground")
    fondo.inputs["Color"].default_value = (0.95, 0.95, 0.95, 1)
    fondo.inputs["Strength"].default_value = 1.0
    salida = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(fondo.outputs["Background"], salida.inputs["Surface"])
    return mundo


def suelo(mats, modo="estudio", tam=26.0):
    """Plano de suelo: oscuro y reflectante (estudio) o blanco (técnico)."""
    bpy.ops.mesh.primitive_plane_add(size=tam, location=(0, 0, 0))
    suelo = bpy.context.object
    suelo.name = "SUELO"
    if modo == "tecnico":
        suelo.data.materials.append(mats["M_FLOOR_TECNICO"])
    else:
        suelo.data.materials.append(mats["M_FLOOR"])
    return suelo


# ---------------------------------------------------------------------------
# Luces
# ---------------------------------------------------------------------------
def _area(nombre, loc, energia, tam, color=(1, 1, 1), rot=(0, 0, 0), forma='RECTANGLE',
          tam_y=None, difuso=1.0):
    datos = bpy.data.lights.new(nombre, 'AREA')
    datos.energy = energia
    datos.color = color
    datos.shape = forma
    datos.size = tam
    if tam_y is not None:
        datos.size_y = tam_y
    datos.diffuse_factor = difuso
    obj = bpy.data.objects.new(nombre, datos)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = rot
    return obj


def luces(modo="estudio"):
    """Key + relleno + contraluz, pensadas para el lenguaje de la hoja de catálogo."""
    if modo == "tecnico":
        _area("KEY", (2.6, -2.2, 4.2), 1400, 5.0, (1, 1, 1), (radians(38), 0, radians(48)),
              'RECTANGLE', 3.0)
        _area("FILL", (-3.0, -1.6, 2.4), 500, 4.0, (0.92, 0.95, 1.0),
              (radians(58), 0, radians(-58)), 'RECTANGLE', 3.0)
        _area("RIM", (-1.2, 3.4, 2.6), 700, 3.0, (1, 1, 1),
              (radians(66), 0, radians(200)), 'RECTANGLE', 2.0)
        return

    # Estudio oscuro: clave cenital suave, relleno frío, contraluz cálido
    _area("KEY", (2.0, -2.8, 4.2), 1150, 2.4, (1.0, 0.98, 0.93),
          (radians(36), 0, radians(38)), 'RECTANGLE', 1.8)
    _area("FILL", (-3.0, -2.2, 1.8), 260, 4.0, (0.86, 0.92, 1.0),
          (radians(74), 0, radians(-56)), 'RECTANGLE', 3.0)
    # La contraluz va baja y atras: en el parabrisas solo deja el filo,
    # nunca un reflejo blanco (era lo que rompia la lectura del cristal).
    _area("RIM", (-1.6, 3.8, 1.9), 380, 1.8, (1.0, 0.94, 0.86),
          (radians(74), 0, radians(205)), 'RECTANGLE', 1.1)
    _area("STRIP", (0.6, 0.0, 4.6), 95, 0.8, (1, 1, 1),
          (0, 0, 0), 'RECTANGLE', 2.6)


# ---------------------------------------------------------------------------
# Cámara
# ---------------------------------------------------------------------------
def camara(vista="heroi", nombre=None):
    """Crea la cámara de una vista y la activa como cámara de la escena."""
    cfg = VISTAS[vista]
    az, el, d = radians(cfg["az"]), radians(cfg["el"]), cfg["dist"]
    aim = Vector(cfg["aim"])

    pos = aim + Vector((
        d * cos(el) * sin(az),
        d * cos(el) * cos(az),
        d * sin(el),
    ))

    datos = bpy.data.cameras.new(nombre or f"CAM_{vista}")
    datos.lens = cfg["focal"]
    datos.sensor_width = 36.0
    datos.clip_start = 0.05
    datos.clip_end = 200.0
    obj = bpy.data.objects.new(nombre or f"CAM_{vista}", datos)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = pos
    obj.rotation_euler = (aim - pos).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = obj
    return obj


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def configurar(muestras=128, resolucion=(1600, 900), modo="estudio", mats=None):
    esc = bpy.context.scene
    esc.render.engine = 'CYCLES'
    esc.cycles.device = 'CPU'
    esc.cycles.samples = muestras
    esc.cycles.use_adaptive_sampling = True
    esc.cycles.adaptive_threshold = 0.01
    esc.cycles.use_denoising = True
    try:
        esc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except TypeError:
        pass
    esc.cycles.max_bounces = 8
    esc.cycles.transmission_bounces = 8
    esc.cycles.transparent_max_bounces = 12
    esc.cycles.caustics_reflective = False
    esc.cycles.caustics_refractive = False

    esc.render.resolution_x, esc.render.resolution_y = resolucion
    esc.render.resolution_percentage = 100
    esc.render.film_transparent = False
    esc.render.image_settings.file_format = 'PNG'
    esc.render.image_settings.color_mode = 'RGB'
    esc.render.image_settings.color_depth = '8'
    esc.render.use_file_extension = True

    # Gestión de color: AgX con contraste medio si existe
    vs = esc.view_settings
    disponibles = [i.identifier for i in
                    type(vs).bl_rna.properties["view_transform"].enum_items]
    vs.view_transform = "AgX" if "AgX" in disponibles else "Standard"
    looks = [i.identifier for i in type(vs).bl_rna.properties["look"].enum_items]
    for candidato in ("AgX - Medium High Contrast", "AgX - Base Contrast", "None"):
        if candidato in looks:
            vs.look = candidato
            break
    vs.exposure = 0.0
    vs.gamma = 1.0

    if modo == "tecnico":
        _fondo_blanco()
    else:
        _degradado_oscuro()

    if mats is not None:
        if "M_FLOOR_TECNICO" not in mats:
            from . import materiales as MAT
            mats["M_FLOOR_TECNICO"] = MAT.base(
                "M_FLOOR_TECNICO", (0.88, 0.88, 0.88), roughness=0.55)
    return esc


def render(destino, vista=None, muestras=128, resolucion=(1600, 900), modo="estudio"):
    if vista:
        camara(vista)
    esc = bpy.context.scene
    esc.render.filepath = destino
    bpy.ops.render.render(write_still=True)
    return destino
