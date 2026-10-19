#!/usr/bin/env python3
"""
NOVU — Verificador contra la ficha de catálogo.

Renderiza la vista lateral ortográfica del modelo sobre fondo blanco, mide los
hitos con el MISMO criterio que se aplicó a la imagen de la hoja de catálogo y
presenta la tabla de desviaciones.

    ./tools/blender_env/bl blender/novu/verificar_ficha.py
    ./tools/blender_env/bl blender/novu/verificar_ficha.py --comparar render.png

La referencia de la ficha es: blender/novu/referencia/vista_lateral_ficha.png
(recorte del panel VISTAS TÉCNICAS de la hoja NOVU TAXI FREE).
"""
import argparse
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from blender.novu import estudio, medir, taxi  # noqa: E402

REFERENCIA = RAIZ / "blender/novu/referencia/vista_lateral_ficha.png"
ANCHO_PX = 1200
ALTO_PX = 700
ORTHO_SCALE = 3.30          # metros que abarca el ancho del encuadre


def render_lateral_ortografico(destino, muestras=24):
    """Render lateral ortográfico: la escala en píxeles es exactamente conocida."""
    import bpy
    from math import radians
    from mathutils import Vector

    cuerpo, piezas, mats = taxi.construir()
    estudio.configurar(muestras=muestras, resolucion=(ANCHO_PX, ALTO_PX),
                       modo="tecnico", mats=mats)
    # Sin suelo: el reflejo del coche contaminaría la silueta que se mide
    estudio.luces("tecnico")

    cam = bpy.data.cameras.new("CAM_lateral_orto")
    cam.type = 'ORTHO'
    cam.ortho_scale = ORTHO_SCALE
    obj = bpy.data.objects.new("CAM_lateral_orto", cam)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = (9.0, 0.0, 0.60)
    obj.rotation_euler = (radians(90), 0, radians(90))
    bpy.context.scene.camera = obj

    bpy.context.scene.render.filepath = destino
    bpy.ops.render.render(write_still=True)
    return destino


def main():
    ap = argparse.ArgumentParser(description="Verifica el modelo contra la ficha")
    ap.add_argument("--comparar", default=None,
                    help="render ya existente para comparar (si no, se genera)")
    ap.add_argument("--muestras", type=int, default=24)
    ap.add_argument("--salida", default="/tmp/verificar_lateral.png")
    args = ap.parse_args()

    if args.comparar:
        ruta_modelo = args.comparar
        px_h = px_v = None
    else:
        ruta_modelo = render_lateral_ortografico(args.salida, args.muestras)
        px_h = ANCHO_PX / ORTHO_SCALE
        px_v = px_h

    if not REFERENCIA.exists():
        print(f"FALTA la referencia: {REFERENCIA}")
        return 2

    ficha = medir.hitos_de_imagen(str(REFERENCIA))
    modelo = medir.hitos_de_imagen(ruta_modelo, px_por_m_h=px_h, px_por_m_v=px_v)

    print("\n=== FICHA (hoja de catálogo) ===")
    print(f"  largo {ficha['metros']['largo']:.3f} m   alto carrocería "
          f"{ficha['metros']['alto_carroceria']:.3f} m   alto con cartel "
          f"{ficha['metros']['alto_con_cartel']:.3f} m")
    print(f"  escala: {ficha['px_por_m_h']:.2f} px/m (horizontal) · "
          f"{ficha['px_por_m_v']:.2f} px/m (vertical)")
    print("\n=== MODELO (render) ===")
    print(f"  largo {modelo['metros']['largo']:.3f} m   alto carrocería "
          f"{modelo['metros']['alto_carroceria']:.3f} m   alto con cartel "
          f"{modelo['metros']['alto_con_cartel']:.3f} m")
    print(f"  escala: {modelo['px_por_m_h']:.2f} px/m (ORTográfica, exacta)")
    print("\n=== DESVIACIONES (modelo - ficha) ===")
    print(medir.tabla_comparativa(ficha, modelo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
