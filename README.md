# hojas-tecnicas-personajes

Producción de las hojas técnicas de los personajes de **"El Resurgir"** — saga distópica de Novus Corp (Biblia Maestra v5.0).

## Estructura

| Ruta | Contenido |
|---|---|
| `BIBLIA_MAESTRA_v5.0.md` | **Canon maestro** — fuente única de verdad: lore, paletas HEX, bloqueos, prompts maestros, estado de producción |
| `archivo_arte/index.html` | **Interfaz** del Archivo de Arte — tarjetas por bloque (Protagonistas/Catalizadores · Trío de Poder · Sub-crónica 24H · Pendientes) |
| `archivo_arte/fichas/` | Hojas técnicas individuales (HTML, **solo texto** — sin base64, regla §76) |
| `hoja_personaje_1.md` | Plantilla genérica Markdown (creada antes de recibir la Biblia; se conserva para personajes sin canon) |

## Flujo de trabajo (canon §62 / §76)

1. **UN activo → presentar → aprobar → archivar** con nombre canónico. Nada de generar 7 de golpe.
2. El canon NO vive en archivos pesados: vive en la **Biblia + fichas de texto**. Las imágenes son regenerables; el canon no.
3. Fichas = texto + nombres canónicos de activo. **Nada de base64** (el HTML anterior se perdió por el límite de 128 MB).
4. **El HEX es ley** (§24): ningún color genérico sin código.
5. Lo no dictado se marca **"Pendiente de definir"**. No se inventa.

## Uso

Abrir `archivo_arte/index.html` en el navegador, o servir la raíz:

```bash
python3 -m http.server 8080
# → http://localhost:8080  (redirige al Archivo de Arte)
```

## Estado del archivo de arte

| Nº | Personaje | Ficha | Estado |
|---|---|---|---|
| 00 | El Pelirrojo | `FICHA_00_EL_PELIRROJO.html` | ✅ Construida (modelo) |
| 01 | El Coleta | `FICHA_01_EL_COLETA.html` | ⏳ En construcción |
| 02 | El Rubio | `FICHA_02_EL_RUBIO.html` | ⏳ En construcción |
| 03 | La Japonesa | `FICHA_03_LA_JAPONESA.html` | ⏳ En construcción |
| 04 | El Ejecutivo NC | `FICHA_04_EL_EJECUTIVO_NC.html` | ⏳ En construcción |
| 05 | El Mercenario | `FICHA_05_EL_MERCENARIO.html` | ⏳ En construcción |
| 18 | Valeria Sanz | `FICHA_18_VALERIA_SANZ_24H.html` | ⏳ En construcción |
| 19 | Carlos Ramírez | `FICHA_19_CARLOS_RAMIREZ_24H.html` | ⏳ En construcción |
| 20 | Zona BSL-4 | `FICHA_20_ZONA_BSL4.html` | ⏳ En construcción |
