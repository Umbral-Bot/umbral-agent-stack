---
id: "2026-11-06-001"
title: "Laboratorio: motor paramétrico de piezas gráficas Umbral BIM (primera entrega)"
status: done
assigned_to: claude_code_tarro
created_by: claude_code_vps
priority: media
created_at: "2026-11-06"
updated_at: "2026-11-06"
pr: "https://github.com/Umbral-Bot/umbral-agent-stack/pull/710 (borrador, sin merge)"
---

## Alcance

David pidió construir un método reutilizable (una skill) para producir piezas gráficas
de Umbral BIM a partir de packs de parámetros, como una definición de Grasshopper con
sliders. Arquitectura, reglas y borrador de parámetros: `labs/motor-piezas/README.md` y
`labs/motor-piezas/parametros.borrador.yaml`.

Ejecuta una sesión de Claude Code en TARRO sobre el clon local de umbral-agent-stack,
rama `rick/motor-piezas-lab`. Es laboratorio: no es producción ni la skill final.

Insumos en Drive (solo lectura):
- Sistema v2 que eligió David: carpeta https://drive.google.com/drive/folders/1q6Nh62Yfki8EFWLbKEImYsRo9KiU5hJV
  (`generate.py`, `README.md`, `00_preview.jpg` numerado, `png/` y el paquete
  `2026-11-06_ref-save-the-date_v2.tar.gz` con fuentes y assets).
- Manual de Marca UB-3: https://drive.google.com/file/d/1E5Trex0akR9_Z1o9hsZzW5MXQ22HW6kN/view
- Tokens: `03_Sistema de Diseno/Umbral BIM Design System/colors_and_type.css`.
- Lockups oficiales: `02_Logotipo/Exportables/Lockup/`.
- Plantillas vigentes: `04_Plantillas/00_LEEME.md`.
- Insumos del Director Comercial y Marketing (capa de imagen, cuando existan):
  `02_Marca e Identidad/07_Motor de piezas/00_insumos/`. Esa subcarpeta es del Director:
  leer, no escribir.

## Primera entrega (después detenerse para revisión)

1. Análisis de las seis piezas elegidas (v1 1°; v2 1°, 12°, 20°, 22°, 24°): sus valores
   expresados como parámetros y qué cambiaría en cada una para el "ajuste espacial".
2. Tres alternativas de proceso (A grilla primero, B contenido primero, C imagen
   primero), con pasos en orden y, por paso, parámetros, tipo, defecto y cuáles fija el
   manual.
3. `parametros.borrador.yaml` ajustado y un motor mínimo (`motor.py` o equivalente) que
   lea un pack y genere SVG + PNG a partir del `generate.py` de la v2, sin valores
   escritos en el código.
4. Galería HTML numerada (1°, 2°…) con 3 o 4 piezas por alternativa, mismo contenido de
   ejemplo (workshop BIM + IA), cada pieza con su pack visible. Publicarla en
   `07_Motor de piezas/01_galerias/` de Drive.
5. `decisiones.csv` listo para registrar las elecciones de David.

## Reglas

- Un escritor: solo `labs/motor-piezas/` en esta rama y subcarpetas propias en Drive.
- Sin Notion. Sin créditos de Magnific o Midjourney sin informar cuántos y esperar OK.
- Commits pequeños; `git pull` antes de empezar y push de la rama al terminar.
- Al cerrar: PR en borrador sin merge y nota de traspaso abajo.

## Aceptación

- [x] Las seis elegidas analizadas con parámetros y correcciones propuestas
      (`labs/motor-piezas/analisis/01_piezas-elegidas.md`, cifras en `medidas_elegidas.json`).
- [x] Tres alternativas de proceso comparables (`analisis/02_alternativas-proceso.md`; G01 1°–4°, 5°–8°, 9°–12°).
- [x] El motor regenera una pieza v2 elegida solo desde un pack (sin valores en código)
      (`packs/R1-replica-v2-01.yaml` + `comparar_replica.py`: v2 1°).
- [x] Galería numerada en Drive con packs visibles; sin reglas UB-3 rotas fuera de
      piezas rotuladas como exploración (12/12 cumplen; solo el control R1 sale como exploración, a propósito).
- [x] PR en borrador y nota de traspaso (#710).

## Nota de traspaso

**Cierra:** Claude Code en TARRO · 2026-11-06 · rama `rick/motor-piezas-lab` · PR borrador
[#710](https://github.com/Umbral-Bot/umbral-agent-stack/pull/710), sin merge. Revisan Claude del VPS y
Rick GPT; producción solo con GO de David.

**Qué se probó**

- **Herramientas:**
  - Magnific responde por la extensión local (`mcp-remote` a mcp.magnific.com): perfil y saldo leídos. Quedan 3.833 créditos y el modo ilimitado no aplica en la sesión. **0 créditos gastados.**
  - Google Drive responde por conector y por la unidad local `G:`.
  - Claude in Chrome está conectado.
  - Render con el Chrome del equipo vía Playwright: no se instaló nada.
- **Insumos del Director** (`07_Motor de piezas/00_insumos`, solo lectura):
  - Su `generate.py` portable es la base del motor.
  - Sus copias de lockups, fuentes, vectores y favoritas MJ son idénticas por sha256 a las fuentes canónicas.
- **Motor** (`motor.py`) con cuatro procesos: A grilla, B contenido, C imagen y «libre» (como la v2). Genera 12 piezas y un control desde packs, con verificación UB-3 automática por pieza.
- **Réplica:** la v2 1° regenerada desde un pack y comparada con su original en el mismo Chrome.
- **Medición** de las seis elegidas con `analisis/medir_piezas.py`.

**Resultado**

- **Galería G01:** 12/12 piezas cumplen UB-3, con contraste ≥ 4,5:1 medido sobre el fondo real y velos planos.
  - Publicada en Drive: [07_Motor de piezas/01_galerias/2026-11-06_G01](https://drive.google.com/drive/folders/1k0nPj__68xm_4tw5GNuD4rHNv_XxCr4Y).
  - En Drive se ve directo `00_preview.jpg`. `galeria.html` usa rutas relativas: se abre desde `G:` o tras descargar la carpeta.
- **Réplica R1:**
  - Cajas dentro de ±3 px en vertical.
  - Diferencia de píxeles 5,6/255; el mismo SVG en CairoSVG y en Chrome difiere 6,4.
  - Los títulos salen 14–17 px más anchos porque la v2 usó el corte Inter Display de su fuente variable y el motor usa la Inter canónica.
  - La verificación marca sola la falta UB-3 de la v2: números turquesa sobre claro, 2,82:1.
- **Medición:**
  - Filas a 7,2–7,9 px CSS en el celular.
  - Vacío del 33–38 % del alto.
  - Isometría e imagen sin alinearse con nada.
  - Bajada de la 24° a 4,49:1.
  - Velo en degradado en 22° y 24°.
  - Fondo de portada en LinkedIn (12°).
- **Registro:** `decisiones.csv` con una fila por pieza de G01, listo para el número y el comentario de David.

**Qué aplicar**

1. David elige en G01 (número 1°–12° y comentario). Se registra en `decisiones.csv` y sale una segunda vuelta de packs.
2. Decidir los pendientes que el laboratorio no toma (detalle en `labs/motor-piezas/README.md`):
   - Inter Display para titulares.
   - `#2DD4BF` como texto de acento en oscuro o `--ub-primary-text`.
   - Vista supuesta por formato (`vista_css`).
   - Imágenes MJ fijas: el PNG trae prompt, `--v 8.2` y Job ID, pero no `--sref`, perfil ni semilla.
3. Recién con esas elecciones conviene pasar el motor a skill en el registro, por PR.

**Riesgos**

- **Dependencias del equipo:** el motor depende de las rutas de TARRO (`rutas.yaml`, Drive en `G:`) y del Chrome local. En la VPS hay que adaptar `rutas.yaml`.
- **Proceso C automático:** puede elegir una franja angosta en formatos verticales (C2 fija la zona superior en su pack). Si la imagen no tiene zona limpia, el velo sube hasta casi tapar la imagen (C1: 0,96).
- **Contenido:** las piezas son de ejemplo (chip EJEMPLO, fecha ficticia): no publicar.
- **`board.md` no se tocó:** está fuera del alcance de escritura y, en el clon, tiene cambios ajenos sin commit.
- **Clon de TARRO:**
  - Queda en `rick/motor-piezas-lab`.
  - Para cambiar de rama se guardó en el stash `pre-motor-piezas-lab-20261106-hygiene` una ficha local sin seguimiento (`.agents/tasks/2026-09-22-001-t3c1-capacity.md`, con 2 líneas propias) que chocaba con su versión en la rama. Hay copia también en el scratchpad de la sesión.
  - Se recupera con `git switch main` y `git stash pop` de ese stash.
- **Historial:** el commit `718f0517` dice «ajustes de galería», pero esos cambios ya iban en `5e184219`; solo trae README y `decisiones.csv`.

**Cómo revertir**

- Cerrar #710 sin merge. Borrar la rama solo con GO.
- Borrar en Drive `07_Motor de piezas/01_galerias/2026-11-06_G01`. No toca `00_insumos`.
- No hubo escrituras en Notion ni en `main`.
