#!/usr/bin/env python3
"""
Sonda de compatibilidad entre versiones de Blender (bpy).

Dumps un informe NORMALIZADO de las APIs que usa un pipeline de render
(character sheets / vehiculos). Al ejecutar el mismo script en dos versiones
distintas, `diff` da exactamente que se rompe al cambiar de version.

Uso:
    ./bl api_probe.py > probe_4.3.txt
    BL_VENV=... ./bl api_probe.py > probe_5.0.txt
    diff probe_4.3.txt probe_5.0.txt
"""

import bpy
import json
import sys


def safe(fn, default="<error>"):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return f"<error: {type(e).__name__}>"


def enum_items(rna_type, prop):
    try:
        return sorted(i.identifier for i in rna_type.bl_rna.properties[prop].enum_items)
    except Exception:
        return []


def collect():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    # El addon de Cycles debe estar habilitado para exponer sc.cycles
    try:
        bpy.ops.preferences.addon_enable(module="cycles")
    except Exception:
        pass
    out = {}

    # --- Motores de render disponibles ---
    out["engines"] = enum_items(bpy.types.RenderSettings, "engine")

    # --- Sockets del Principled BSDF (cambio mayor 4.0 vs 3.x) ---
    mat = bpy.data.materials.new("probe")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    out["principled_inputs"] = sorted(i.name for i in bsdf.inputs) if bsdf else []

    # --- Operadores de suavizado (auto smooth eliminado en 4.1) ---
    out["ops_shading"] = sorted(
        o for o in dir(bpy.ops.object) if "smooth" in o
    )
    out["has_use_auto_smooth"] = hasattr(bpy.types.Mesh, "use_auto_smooth")

    # --- Cycles: ajustes y denoisers ---
    out["cycles_props"] = sorted(
        p.identifier for p in bpy.context.scene.cycles.bl_rna.properties
        if not p.is_readonly
    ) if hasattr(sc, "cycles") else []
    def cycles_enum(prop):
        try:
            fixed = bpy.types.Scene.bl_rna.properties["cycles"].fixed_type
            return sorted(i.identifier for i in fixed.bl_rna.properties[prop].enum_items)
        except Exception:
            return []

    out["cycles_denoisers"] = cycles_enum("denoiser")
    out["cycles_devices"] = cycles_enum("device")

    # --- Formatos de salida (el pipeline del otro agente usa WebP q90) ---
    out["image_formats"] = enum_items(bpy.types.ImageFormatSettings, "file_format")
    out["color_modes"] = enum_items(bpy.types.ImageFormatSettings, "color_mode")

    # --- Gestion de color ---
    out["view_transforms"] = enum_items(bpy.types.ColorManagedViewSettings, "view_transform")
    out["looks"] = enum_items(bpy.types.ColorManagedViewSettings, "look")
    out["sequencer_cs"] = enum_items(bpy.types.ColorManagedSequencerColorspaceSettings, "name")

    # --- Modificadores usados en modelado de vehiculo/hojas ---
    out["modifiers"] = enum_items(bpy.types.Modifier, "type")

    # --- Primitivas de malla ---
    out["mesh_primitives"] = sorted(
        o for o in dir(bpy.ops.mesh) if o.startswith("primitive_")
    )

    # --- Callbacks / utilidades de datos ---
    out["has_foreach_set"] = hasattr(bpy.types.Mesh, "foreach_set") or hasattr(
        bpy.types.bpy_prop_collection, "foreach_set"
    )
    out["node_group_types"] = enum_items(bpy.types.NodeTree, "type")

    # --- Objetos:，能否 crear malla desde datos (loft, etc.) ---
    def mesh_from_pydata():
        me = bpy.data.meshes.new("m")
        me.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
        me.update()
        return len(me.polygons)

    out["from_pydata_polys"] = safe(mesh_from_pydata)

    # --- Salida de video/imagen: ruta de escritura ---
    out["image_settings_has_quality"] = hasattr(
        bpy.types.ImageFormatSettings, "quality"
    )
    out["has_render_stamp"] = hasattr(bpy.types.RenderSettings, "use_stamp")

    return out


if __name__ == "__main__":
    data = collect()
    print(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))
