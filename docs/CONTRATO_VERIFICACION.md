# CONTRATO DE VERIFICACIÓN — flota NOVU

Cómo trabajan los dos agentes sobre el mismo vehículo sin pisarse y sin
discutir a ojo. Este documento es la **fuente de verdad** de la geometría de
referencia: todas las cifras están medidas sobre la hoja de catálogo.

- Referencia: `blender/novu/referencia/vista_lateral_ficha.png` (recorte ×3 de
  la vista lateral de la hoja `Max_a_NOVU_TAXI_FREE..png`, región x 380 / y 536
  de 1536 × 1024; diferencia media con el original 2,05/255).
- Origen de coordenadas del modelo: **Y** = longitudinal (morro +1,30 / cola
  −1,30), **X** = transversal (−0,65 … +0,65), **Z** = altura desde el suelo.

---

## 1. Reparto de trabajo

| | Agente de geometría (workspace) | Agente de verificación (este repo) |
|---|---|---|
| Escribe | `blender/novu/params.py`, `geo.py`, `taxi.py`, `materiales.py` | `blender/novu/medir.py`, `verificar_ficha.py`, `render.py`, `estudio.py`, `tools/medir_ficha/`, `tools/bridge/` |
| Ve | código y texto | además las imágenes y los renders |
| Entrega | commits con los cambios | tabla de desviaciones + informe de texto |

**El que no ve imágenes no implementa sobre percepciones**: todo lo que
necesite ver está medido aquí, en coordenadas de modelo.

## 2. Las seis métricas y su tolerancia

Se miden con `medir_ficha.py`, el **mismo criterio** sobre la ficha y sobre el
render. Tolerancia: `OK` ≤ 2 cm · `~` ≤ 5 cm · `!!` > 5 cm.

| Métrica | Ficha | Modelo | Δ |
|---|---|---|---|
| Largo total | 2,600 | 2,612 | +0,012 OK |
| Alto de carrocería | 1,200 | 1,199 | −0,001 OK |
| Alto con cartel TAXI | 1,332 | 1,336 | +0,005 OK |
| Línea de cintura | 0,623 | 0,610 | −0,012 OK |
| Cartel sobre el techo | 0,132 | 0,137 | +0,006 OK |
| Cartel (largo en planta) | 0,358 | 0,385 | +0,027 ~ |

Y las mismas en **ratios sin escala** (× alto de carrocería), que no dependen
de ninguna suposición de escala:

| Ratio | Ficha | Modelo | Δ |
|---|---|---|---|
| largo / alto | 2,1667 | 2,1789 | +0,0122 ~ |
| alto con cartel / alto | 1,1097 | 1,1147 | +0,0050 OK |
| cartel sobre techo / alto | 0,1097 | 0,1147 | +0,0050 OK |
| cintura / alto | 0,5190 | 0,5092 | −0,0098 OK |
| cartel en planta / alto | 0,2981 | 0,3211 | +0,0230 ~ |

## 3. Comandos (sin git en el sandbox del agente de geometría)

```bash
# 1. Traer el código (el repo es público; no hace falta git)
curl -sL https://codeload.github.com/emijotorregarci14-svg/hojas-tecnicas-personajes/tar.gz/refs/heads/arena/af8e2833-hojas-tecnicas-personajes | tar xz
cd hojas-tecnicas-personajes-arena-af8e2833-hojas-tecnicas-personajes

# 2. Medir (sólo pillow + numpy, sin Blender)
python3 tools/medir_ficha/medir_ficha.py FICHA  blender/novu/referencia/vista_lateral_ficha.png
python3 tools/medir_ficha/ver_texto.py      FICHA  blender/novu/referencia/vista_lateral_ficha.png --cols 132
python3 tools/medir_ficha/medir_ficha.py COMPARAR \
        blender/novu/referencia/vista_lateral_ficha.png renders/orto_lateral.png --escala 363.64

# 3. Publicar (sube a GitHub por la API, sin git; usa $GITHUB_TOKEN)
python3 tools/bridge/publicar.py blender/novu/params.py -m "Ajusta la cola"
```

`ver_texto.py` convierte la ficha en un **mapa de caracteres** con las cotas
en metros: es la forma de "verla" sin ver imágenes.

```
# leyenda: W fondo  Y amarillo  K negro  G gris  g cristal claro  R rojo  C cian  S beige
  1.20 |WGKKKKKKKKKKKKKKKKKggggggggggggggWWWWWWWWWWWWWWWgggggWWWWWWWWWWWWWWWW|
  1.00 |WGKKKGKKKKKKKKKKKGGGGGGGKKKKKKKKKKKGGGGGGGGGGGgggggggGGKKKKKKKKKKKKKKGgGGGGGGGGGKKKKKKKKKKKKKKKgWWWWWWWW|
  0.60 |WWWWWWWWWWWWWWoYYYYYYYYYYYYYYYoKKYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYoWW|
  0.40 |WWWWgooooYYYYYYKKKKKKKKKKKKKKKKKKKKoYYYYYYYYKoYooYYoooYoYoYoYYYYoYoKoYYKYYKYYYKYYKYKYKoYooYYYYYYYYYYYYYYoKKKKKKKKKKKKKKKKKKKYYYYYYYYYYgW|
```

## 4. Especificación de los detalles pendientes

Todas estas cotas están medidas sobre la ficha (columna de píxeles indicada).

### 4.1 Zócalo negro inferior — FALTA EN EL MODELO
Franja negra bajo toda la carrocería, de **z 0,05 a 0,15 m** (0,10 m de alto),
visible entre las ruedas y bajo los pasos. En la columna x=250 el negro va de
z 0,147 a 0,051; el amarillo de la puerta empieza en z 0,162.

### 4.2 Cenefa de cuadros — EL MODELO TIENE 1 FILA, LA FICHA 2
Banda de cuadros de **dos filas**, de **z 0,40 a 0,53 m** (0,13 m de alto),
fila de 0,065 m. Filas negras medidas en z 0,506–0,532 y z 0,400–0,420; entre
ellas la fila amarilla z 0,430–0,496.

### 4.3 Rótulo lateral — YA APLICADO
«NOVU TAXI FREE.» de **Y +0,24 a Y −0,71** (0,95 m), mayúsculas de **z 0,33 a
0,41**. En el modelo: `ROTULO(y=-0.190, z=0.367, alto=0.105, ancho=0.880)`.

### 4.4 Cristal y marco — YA APLICADO
Banda de cristal de **z 0,66 a 0,94 m**; sobre ella, marco negro hasta el
techo (1,20 m). `MARCO_SUPERIOR = 0.240`, `M_GLASS` con alfa 0,70.

### 4.5 Cola — PENDIENTE (forma)
- Techo plano hasta **Y −0,93 m**; a partir de ahí cae hasta **z 0,633 en
  Y −1,27 m**. El modelo redondea ya desde Y −0,86 (~12 cm antes).
- El remate superior de la cola (Y −1,17) es **negro** de z 0,66 a 0,92.
- Bandas amarillas: z 0,55–0,65 y z 0,20–0,49.
- **Piloto rojo** en z 0,49–0,52 en la esquina trasera.

### 4.6 Portón trasero — PENDIENTE (del héroe 3/4 trasero)
- Portón **amarillo** con **banda negra** horizontal en la parte alta, con
  «NOVU» en letras blancas: banda ≈ 0,75 m de ancho × 0,17 m de alto, con la
  línea de texto a z ≈ 0,60.
- «NOVU TAXI FREE.» en negro, centrado en el amarillo, ≈ 0,67 m de ancho,
  altura de letra ≈ 0,07 m, a z 0,33–0,41.
- **Pilotos rojos**: barras horizontales a ambos lados, ≈ 0,24 m de largo ×
  0,07 m de alto, con el núcleo claro, a la altura de la banda «NOVU».
- **Parachoques negro** en la parte baja del portón, de z 0,05 a 0,25.
- Ventana trasera grande y oscura, con los reposacabezas visibles.
- El modelo hoy deja la cola demasiado negra: falta el portón amarillo.

### 4.7 Ruedas — YA APLICADO
Delantera **Y +0,885**, trasera **Y −0,915** (batalla 1,80 de la spec; la
ficha dibuja 1,89, se adopta la spec). Radio 0,26, centros X ±0,48.

### 4.8 Perfil superior — YA COINCIDE
Morro Y +1,310 / z 0,359 · cowl Y +1,03 / z 0,618 · parabrisas a 47° hasta
Y +0,45 / z 1,144 · techo plano hasta Y −0,93.

## 5. Reglas

1. Nada de subir a GitHub sin avisar; publicar con `publicar.py` avisa por
   consola.
2. No tocar `SHUTTLE_FINAL_*` ni `COCHE_MODULAR_v54`.
3. Pipelines en directorios separados: `blender/novu/` + `tools/` aquí;
   `tools/blender/` en el otro pipeline.
4. Nada se da por aprobado sin medición y visto bueno del usuario.
5. Referencia de versión: bpy 4.3.x (4.3.0 verificado aquí); 5.0 sólo con
   comparación previa.
6. Si se cambia la silueta, se avisa antes de tocar `geo.py`: el otro agente
   puede estar a mitad de un cambio sobre el mismo fichero.
