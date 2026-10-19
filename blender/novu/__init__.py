"""
NOVU — Pipeline de construcción del taxi en Blender.

Ejemplo mínimo:

    from blender.novu import taxi, estudio
    cuerpo, piezas, mats = taxi.construir()
    estudio.configurar(muestras=128, mats=mats)
    estudio.suelo(mats, modo="estudio")
    estudio.luces("estudio")
    estudio.render("/tmp/hero.png", vista="heroi")
"""
