"""
NOVU — Biblioteca de materiales.

Nomenclatura coherente con la del pipeline de vehículos (M_BODY, M_GLASS, M_MOLD):
si un material aparece en ambos pipelines, se llama igual y significa lo mismo.

Valores de color en espacio lineal (los de la paleta ya están convertidos).
"""
import bpy

from . import params as P


def _nuevo(nombre):
    mat = bpy.data.materials.get(nombre)
    if mat:
        return mat
    mat = bpy.data.materials.new(nombre)
    mat.use_nodes = True
    return mat


def _principled(mat):
    for n in mat.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            return n
    return None


def base(nombre, color, metallic=0.0, roughness=0.5, alpha=1.0,
         emission=None, emission_strength=0.0, ior=1.45, spec=0.5):
    mat = _nuevo(nombre)
    bsdf = _principled(mat)
    if bsdf is None:
        return mat
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Alpha"].default_value = alpha
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = ior
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = spec
    if emission is not None:
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emission_strength
    if alpha < 1.0:
        # Cycles respeta el alfa del Principled sin tocar el modo de fusión.
        try:
            mat.blend_method = 'BLEND'
        except (AttributeError, TypeError):
            pass
        try:
            mat.surface_render_method = 'BLENDED'
        except (AttributeError, TypeError):
            pass
    return mat


def libreria():
    """Crea (o actualiza) todos los materiales del vehículo."""
    m = {}
    m["M_BODY"] = base("M_BODY", P.COLOR_CARROCERIA, metallic=0.35, roughness=0.30)
    m["M_MOLD"] = base("M_MOLD", P.COLOR_NEGRO, metallic=0.0, roughness=0.55)
    # El techo del catálogo es negro profundo con un brillo suave: con la
    # rugosidad de espejo (0,11) reflejaba el fondo blanco y la cabina
    # leía gris claro en vez de negra.
    m["M_ROOF"] = base("M_ROOF", P.COLOR_NEGRO_BRILLO, metallic=0.0, roughness=0.45,
                        spec=0.12)
    # Cristal opaco y muy reflectante: se comporta como un espejo oscuro y
    # lee gris claro sobre fondo blanco, como en la hoja tecnica.
    m["M_GLASS"] = base("M_GLASS", P.COLOR_CRISTAL, metallic=0.0, roughness=0.05,
                        alpha=1.0, ior=1.45, spec=0.75)
    # Con una emision de 6.0 el AgX la desaturaba y el LED salia blanco:
    # en la hoja de catalogo las tiras se leen cian.
    m["M_LED_CIAN"] = base("M_LED_CIAN", P.COLOR_CIAN, roughness=0.25,
                            emission=P.COLOR_LED, emission_strength=3.0)
    m["M_LED_ROJO"] = base("M_LED_ROJO", P.COLOR_ROJO, roughness=0.25,
                            emission=P.COLOR_ROJO_EM, emission_strength=9.0)
    m["M_TIRE"] = base("M_TIRE", P.COLOR_RUEDA, metallic=0.0, roughness=0.82)
    m["M_RIM"] = base("M_RIM", P.COLOR_LLANTA, metallic=0.55, roughness=0.32)
    m["M_SEAT"] = base("M_SEAT", (0.20, 0.16, 0.11), metallic=0.0, roughness=0.75)
    m["M_SIGN"] = base("M_SIGN", P.COLOR_CARROCERIA, metallic=0.20, roughness=0.30)
    m["M_TEXT"] = base("M_TEXT", (0.01, 0.01, 0.01), metallic=0.0, roughness=0.45)
    m["M_LIVERY"] = base("M_LIVERY", (0.012, 0.012, 0.012), metallic=0.0, roughness=0.40)
    m["M_PLACA"] = base("M_PLACA", (0.72, 0.74, 0.78), metallic=0.0, roughness=0.35)
    m["M_FLOOR"] = base("M_FLOOR", (0.020, 0.020, 0.022), metallic=0.0, roughness=0.35)
    return m
