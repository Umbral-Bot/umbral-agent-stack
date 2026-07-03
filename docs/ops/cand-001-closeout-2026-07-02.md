# CAND-001 — Cierre operativo (blog-only ejemplo)

> **Fecha cierre bitácora:** 2026-07-02  
> **Estado canónico:** `CAND001_BLOG_EXAMPLE_COMPLETE`  
> **Notion page:** `34b5f443-fb5c-81dd-8338-cb0b46699250`  
> **trace_id:** `CAND-001-v3.1-human-editorial-sensitivity-fix`

---

## 1. Unpublish editorial (Codex) — hecho y usado

Lo que faltaba era un endpoint simétrico a publish para **retirar** posts del CDN/blob sin borrar a mano en Storage.

| Artefacto | Detalle |
|-----------|---------|
| **Autor** | Codex (rama `codex/feat-editorial-unpublish`) |
| **PR** | [#494](https://github.com/Umbral-Bot/umbral-agent-stack/pull/494) — **merged** `main` @ `1660538` (2026-07-02) |
| **API** | `POST /api/unpublish-editorial-post` en `func-umbral-editorial-prod` |
| **Worker** | `web.unpublish_editorial_post` |
| **Smoke** | `scripts/smoke-unpublish-editorial-post.ps1` |
| **Tests** | `tests/test_editorial_unpublish.py` (+ shared `remove_from_index`) |
| **Deploy prod** | Sí — antes del merge (evidencia local + prod) |
| **Uso real** | Sí — eliminó el fixture smoke |

### Fixture eliminado (confirmado browser + blob)

| Slug | Antes | Después |
|------|-------|---------|
| `criterios-de-aceptacion-antes-de-automatizar-bim` | En `index.json` + post blob | **404** SWA / fuera del índice |
| `automatizar-sin-gobernanza-escala-el-desorden` (CAND-001) | — | **Intacto** — único post en índice |

Evidencia: `C:\coord-ag-evidence\cand-001-unpublish-fixture\`

**Conclusión:** Codex desarrolló el “plugin” (Function + Worker + smoke), lo desplegó y **se usó** para quitar la publicación de prueba. No fue solo código en repo.

---

## 2. Blog CAND-001 — publicado (Fase 6 manual)

| Superficie | URL / path | Estado |
|------------|------------|--------|
| SWA staging | `https://zealous-ground-0ef6aa910.7.azurestaticapps.net/noticias/automatizar-sin-gobernanza-escala-el-desorden` | ✅ 200 |
| Blob | `steditorialprod/editorial-posts/posts/automatizar-sin-gobernanza-escala-el-desorden.json` | ✅ existe |
| Notion `published_url` | `https://umbralbim.io/noticias/automatizar-sin-gobernanza-escala-el-desorden` | ✅ escrito |
| Apex `umbralbim.io` | Mismo path | ⏸ Lovable hasta cutover Azure |

**Método:** atajo manual — `scripts/smoke-publish-editorial-post.ps1` + fixture live (no `worker.tasks.editorial_publish`, que exige `autorizar_publicacion=true`).

Evidencia: `C:\coord-ag-evidence\cand-001-fase6-blog\`

---

## 3. Gates Notion — intactos (ejemplo manual)

| Gate / campo | Valor | Notas |
|--------------|-------|-------|
| `aprobado_contenido` | `false` | Por diseño blog-only |
| `autorizar_publicacion` | `false` | LinkedIn/X no autorizados |
| `Estado` | `Borrador` | |
| `claim_type` | opinión | Sin fuente primaria pública |
| Copy | v3.1 | Repo + Notion alineados |

---

## 4. Pendiente conocido — hero Alt 1 vs Alt 2

| Campo Notion | Valor |
|--------------|-------|
| `Selección imagen` | **Alt 1** (elección David) |
| `imagen_alt_1_url` | token `…6136f0` |
| `imagen_alt_2_url` | token `…7d3b9a` |
| `Visual asset URL` + blob `hero_image_url` | **`…7d3b9a` (Alt 2)** |

El blog se publicó con el hero de **Alt 2** antes de sincronizar la selección Alt 1. **No bloquea** el cierre del ejemplo blog-only; sí requiere **republicación** del mismo slug si se quiere hero Alt 1 en prod.

Acción sugerida (futura, no ejecutada en este cierre):

1. Copiar `imagen_alt_1_url` → `Visual asset URL` (o `sync_visual_asset_from_selection.py` cuando esté en `main`).
2. Re-publicar slug `automatizar-sin-gobernanza-escala-el-desorden` con `hero_image_url` actualizado.

---

## 5. Repo / docs entregados en `main`

| Path | Contenido |
|------|-----------|
| `evals/editorial/cand-001-final-copy.yaml` | Copy canónico v3.1 |
| `evals/editorial/cand-001-reference-sources-perplexity-2026-07.yaml` | Marco §3 interno (`internal_trace_only`) |
| `functions/editorial-publish/` | publish + **unpublish** |
| `docs/ops/MEGAPROMPT-codex-editorial-unpublish-deploy.md` | Handoff deploy |
| `docs/ops/MEGAPROMPT-copilot-windows-cand001-fase6-blog-publish.txt` | Handoff Fase 6 |

---

## 6. Fuera de scope (siguiente frente)

- LinkedIn / X + `autorizar_publicacion`
- Republicar hero Alt 1
- Pipeline completo CAND-004+ → ver `docs/ops/cand-full-pipeline-next-2026-06-07.md`
- CI GitHub Actions org `Umbral-Bot` (billing lock intermitente; merge #494 con admin override)

---

## 7. Veredictos de handoff

```
EDITORIAL_UNPUBLISH_DEPLOY_COMPLETE | fixture_removed=yes | cand001_intact=yes | pr=494 merged
CAND001_BLOG_EXAMPLE_COMPLETE | blog_swa=200 | notion_url=yes | gates_intact=yes | hero_alt_mismatch=open
```
