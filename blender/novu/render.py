#!/usr/bin/env python3
"""
NOVU TAXI FREE — Render del vehículo.

    ./tools/blender_env/bl blender/novu/render.py --vista heroi --salida /tmp/hero.png
    ./tools/blender_env/bl blender/novu/render.py --todas --salida-dir renders/ --muestras 64

Opciones:
    --vista       heroi | heroi_atras | tres_cuartos | frontal | trasera | lateral | superior
    --todas       renderiza todas las vistas
    --fondo       estudio | tecnico
    --muestras    muestras de Cycles (por defecto 128)
    --ancho/alto  resolución (por defecto 1600x900)
"""
import argparse
import os
import sys
from pathlib import Path

# Permite ejecutar el script suelto: añade la raíz del repo al sys.path
RAIZ = Path(__file__).resolve().parent.parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from blender.novu import estudio, taxi  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Render del NOVU TAXI FREE")
    ap.add_argument("--vista", default="heroi", help="vista a renderizar")
    ap.add_argument("--todas", action="store_true", help="renderiza todas las vistas")
    ap.add_argument("--salida", default=None, help="fichero PNG de salida")
    ap.add_argument("--salida-dir", default="renders/novu", help="carpeta de salida")
    ap.add_argument("--fondo", default="estudio", choices=["estudio", "tecnico"])
    ap.add_argument("--muestras", type=int, default=128)
    ap.add_argument("--ancho", type=int, default=1600)
    ap.add_argument("--alto", type=int, default=900)
    ap.add_argument("--solo-medidas", action="store_true",
                    help="no renderiza: solo informa de las cotas del modelo")
    args = ap.parse_args()

    cuerpo, piezas, mats = taxi.construir()
    estudio.configurar(muestras=args.muestras,
                       resolucion=(args.ancho, args.alto),
                       modo=args.fondo, mats=mats)
    estudio.suelo(mats, modo=args.fondo)
    estudio.luces(args.fondo)

    if args.solo_medidas:
        import bpy
        dg = bpy.context.evaluated_depsgraph_get()
        ev = cuerpo.evaluated_get(dg)
        me = ev.to_mesh()
        xs = [v.co.x for v in me.vertices]
        ys = [v.co.y for v in me.vertices]
        zs = [v.co.z for v in me.vertices]
        print(f"LONGITUD (Y) : {max(ys)-min(ys):.4f} m   (objetivo {2.60:.2f})")
        print(f"ANCHO    (X) : {max(xs)-min(xs):.4f} m   (objetivo {1.30:.2f})")
        print(f"ALTURA   (Z) : {max(zs)-min(zs):.4f} m   (objetivo {1.20:.2f})")
        print(f"ALTURA desde suelo: {max(zs):.4f} m")
        ev.to_mesh_clear()
        return 0

    vistas = list(estudio.VISTAS) if args.todas else [args.vista]
    salida_dir = Path(args.salida_dir)
    salida_dir.mkdir(parents=True, exist_ok=True)

    for v in vistas:
        if args.salida and not args.todas:
            destino = args.salida
        else:
            sufijo = "" if args.fondo == "estudio" else "_tecnico"
            destino = str(salida_dir / f"TAXI_FREE_{v}{sufijo}.png")
        estudio.render(destino, vista=v)
        print(f"OK  {v:14s} -> {destino}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
