---
id: "2026-11-06-001"
title: "Laboratorio: motor paramétrico de piezas gráficas Umbral BIM (primera entrega)"
status: ready
assigned_to: claude_code_tarro
created_by: claude_code_vps
priority: media
created_at: "2026-11-06"
updated_at: "2026-11-06"
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

- [ ] Las seis elegidas analizadas con parámetros y correcciones propuestas.
- [ ] Tres alternativas de proceso comparables.
- [ ] El motor regenera una pieza v2 elegida solo desde un pack (sin valores en código).
- [ ] Galería numerada en Drive con packs visibles; sin reglas UB-3 rotas fuera de
      piezas rotuladas como exploración.
- [ ] PR en borrador y nota de traspaso.

## Nota de traspaso

(Completar al cerrar: qué se probó, resultado, qué aplicar, riesgos, cómo revertir.)
