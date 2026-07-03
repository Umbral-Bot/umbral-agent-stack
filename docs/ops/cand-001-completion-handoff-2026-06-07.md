# CAND-001 — Handoff editorial final (ALT 1 afirmativa)

> **Estado:** `CAND001_BLOG_EXAMPLE_COMPLETE` (2026-07-02). Blog publicado en Azure SWA; gates intactos. Ver `docs/ops/cand-001-closeout-2026-07-02.md`.  
> **Pendiente opcional:** republicar hero con Alt 1 (`imagen_alt_1_url` ≠ hero live).  
> **Page ID:** `34b5f443-fb5c-81dd-8338-cb0b46699250`  
> **trace_id:** `CAND-001-v3.1-human-editorial-sensitivity-fix`  
> **claim_type:** `opinión` — sin fuente primaria externa  
> **Canónico YAML:** `evals/editorial/cand-001-final-copy.yaml`  
> **Apply Notion:** `python scripts/editorial/apply_publication_copy.py --publication-id CAND-001`

Rick/Copilot: **no** marcar `aprobado_contenido` ni `autorizar_publicacion`.

---

## A. Copy LinkedIn FINAL — ALT 1 (afirmativa)

```text
Un equipo BIM puede sumar un agente que revise modelos antes de definir qué cuenta como una revisión válida.

Cuando eso pasa, automatizar no ordena: acelera el desorden que ya estaba.

Si nadie tiene claro quién revisa el modelo, qué interferencia se acepta, qué fuente manda y cómo se audita cada decisión, el agente puede cerrar observaciones que nadie validó y arrastrar el error al entregable.

Automatizar bien no parte por la herramienta. Parte por la gobernanza mínima del proceso: quién revisa, qué se acepta y qué queda registrado.

Primero claridad. Después velocidad.
```

---

## B. Copy Blog FINAL

Ver texto completo en `evals/editorial/cand-001-final-copy.yaml` (`copy_blog`).

Tesis: **Automatizar sin gobernanza escala el desorden.**

---

## C. Copy X FINAL

```text
Automatizar un proceso desordenado no lo arregla: lo acelera.

Antes de usar IA o agentes, hace falta gobernanza mínima: responsables, criterios, fuentes, trazabilidad y revisión humana.

Primero claridad. Después velocidad.
```

---

## D. Comentarios revisión (Notion)

Ajuste humano v3.1 aplicado: se elimina lectura sensible sobre dependencia de pocas personas, se evita aludir a procesos lentos, se suaviza una frase forzada sobre fuente/conflicto y se corrige el lenguaje técnico usando incidencias/issues cuando corresponde. La pieza mantiene foco en gobernanza mínima, trazabilidad y criterio compartido. LinkedIn ALT 1 sin cambios. Mantener como opinión operativa sin fuente primaria externa.

---

## E. Pipeline y modelo

- Benchmark: `evals/editorial/benchmark-umbral-voice-v1.yaml` v1.1
- Canales: `evals/editorial/channel-criteria-v1.yaml`
- Calibración: `CAL-005`, `CAL-006`, `CAL-007` en `director-comunicacion-umbral/CALIBRATION.md`
- Modelo producción: `azure-openai-responses/gpt-5.5` — ver `docs/editorial-pipeline/editorial-model-contract.md`

---

## F. Evidencia histórica

| Versión | Ubicación |
|---------|-----------|
| v1 baseline | handoff 2026-06-07 (superseded) |
| v2 OpenClaw | `~/coord-ag-evidence/cand-001-fase4/` (VPS) |
| v3 micro-fix | `~/coord-ag-evidence/cand-001-fase4b/` (VPS) |
| v3.1 sensitivity | PR post-#492 — blog v3.1, LinkedIn/X sin cambios |
| **canónico** | `evals/editorial/cand-001-final-copy.yaml` |

---

## G. Magnific / imágenes

Sin cambios en selección visual. ALT 1 aquí es variante **textual** LinkedIn, no alternativa de imagen.
