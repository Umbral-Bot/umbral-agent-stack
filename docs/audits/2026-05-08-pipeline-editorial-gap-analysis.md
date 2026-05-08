# Pipeline Editorial — Gap Analysis (Etapa 1)

- **Fecha:** 2026-05-08
- **Owner audit:** Copilot VPS
- **Modo:** read-only. 0 cambios runtime, 0 escrituras Notion, 0 código nuevo.
- **Plan de referencia:** [docs/plans/linkedin-publication-pipeline.md](../plans/linkedin-publication-pipeline.md) §4 Etapa 1, [docs/project-embudo-master-plan.md](../project-embudo-master-plan.md) §3 Fase 2.
- **Evidencia runtime:** SQLite `~/.cache/rick-discovery/state.sqlite` (snapshot 2026-05-07 18:30 ART, 437 `discovered_items`, 260 `fetch_log` rows, 26 referentes únicos en `fetch_log`).

---

## 1. Resumen ejecutivo

| Indicador | Valor |
|---|---|
| Referentes activos esperados (plan §2) | **26** |
| Referentes con ≥1 canal `ok` (último fetch) | **14 / 26 = 53.8%** |
| Referentes cubiertos por YouTube (013-K) | **13 / 26 = 50.0%** |
| Referentes huérfanos (sin canal funcional hoy) | **12 / 26 = 46.2%** |
| Canales con extractor productivo | **2 / 5** (YouTube, RSS directo parcial) |
| Canales en estado stub (`sin_acceso` siempre) | **3 / 5** (LinkedIn, Web/Newsletter funcional, Otros) |
| Etapa 7 (escritura Notion) | ✅ **Desbloqueada** desde audit 006 (2026-05-05); `created` real observado en `reports/stage4-push-*-commit*.json`. Bloqueo histórico era falsa premisa MCP. |

**Recomendación top:** **fix YouTube `sin_acceso` para los 13 referentes restantes** (costo: bajo; +13 referentes potenciales con el extractor 013-K ya existente). Ver §6.

---

## 2. Matriz canal × estado

Estado por canal en el ingest Stage 2 (evidencia: [scripts/discovery/stage2_ingest.py L31-35](../../scripts/discovery/stage2_ingest.py#L31-L35) — definición de `CHANNEL_*`; L636-657 — flujo por canal).

| # | Canal | Plan §2/§4 lo lista | Implementado | Extractor | Stage 2 status | `discovered_items` | Promovidos | Cobertura referentes (último fetch ok) |
|---|---|---|---|---|---|---|---|---|
| 1 | **YouTube channel** | ✅ | ✅ **completo** (013-K) | [dispatcher/extractors/youtube_data_api.py](../../dispatcher/extractors/youtube_data_api.py) + [scripts/discovery/backfill_youtube_content.py](../../scripts/discovery/backfill_youtube_content.py) + RSSHub fan-out en stage2 | OK | **387** | **16** | **13 / 26** |
| 2 | **RSS feed** (directo) | ✅ | ⚠️ **parcial** | [scripts/discovery/stage2_ingest.py L606-614](../../scripts/discovery/stage2_ingest.py#L606-L614) (`process_channel(canal=CHANNEL_RSS, fetch_url=ref.rss_url)`) + parser XML/Atom L263-326 | OK / http_error / sin_acceso | **50** | **4** | **4 / 26** |
| 3 | **Web / Newsletter** | ✅ | ❌ **stub funcional** | [scripts/discovery/stage2_ingest.py L625-633](../../scripts/discovery/stage2_ingest.py#L625-L633) — solo dispara si `is_direct_rss_candidate(web_url)` (L464: requiere terminación `.rss` / `.xml` / `.atom` o palabra `feed` en path) | sin_acceso para 26 / 26 | 0 | 0 | **0 / 26** |
| 4 | **LinkedIn activity feed** | ✅ | ❌ **stub explícito** | [scripts/discovery/stage2_ingest.py L636-645](../../scripts/discovery/stage2_ingest.py#L636-L645) — comentario literal: `# LinkedIn (Fase B not done) → sin_acceso always`; `fetch_url=None` forzado | sin_acceso para 26 / 26 | 0 | 0 | **0 / 26** |
| 5 | **Otros canales** (X, IG, Patreon, GitHub, Medium, Substack…) | ✅ | ❌ **stub explícito** | [scripts/discovery/stage2_ingest.py L647-657](../../scripts/discovery/stage2_ingest.py#L647-L657) — comentario: `# Otros → sin_acceso (no estructurado en Stage 2)`; `fetch_url=None` forzado | sin_acceso para 26 / 26 | 0 | 0 | **0 / 26** |

Totales `discovered_items`: **437** items; **20 promovidos a candidato** (16 YouTube + 4 RSS).

---

## 3. Detalle por canal NO implementado

### 3.1 LinkedIn activity feed

| Item | Evidencia |
|---|---|
| Spike previo en repo | ✅ [docs/spikes/O18-linkedin-auth-gap-report.md](../spikes/O18-linkedin-auth-gap-report.md) (PR #339, mergeado) |
| Tareas previas | [.agents/tasks/2026-05-08-O18-linkedin-auth-spike.md](../../.agents/tasks/2026-05-08-O18-linkedin-auth-spike.md), [.agents/tasks/2026-05-08-O18b-yaml-linkedin-minor-fixes.md](../../.agents/tasks/2026-05-08-O18b-yaml-linkedin-minor-fixes.md) (PR #340 abierto) |
| ADR | ✅ [docs/adr/ADR-005-publicacion-multicanal.md](../adr/ADR-005-publicacion-multicanal.md) — Rick publica en perfil personal, sin Company Page |
| Bloqueado por | OAuth: `mdp_approved: false` (ver O18 §4 P1). Sin MDP de LinkedIn no hay refresh programático del access_token (TTL 60d). Workaround manual: Token Generator del Developer Portal — desbloquea handler v0 sin OAuth callback completo. |
| Cobertura potencial | Plan §2 nota: "26 referentes efectivos; 1 sin LinkedIn (Jose Luis Crespo / QuantumFracture)". → **25 / 26 referentes** si se implementa. |
| Costo relativo | **Med-Alto** — requiere David interactuando con Developer Portal LinkedIn cada ~60 días + parser de feed (no hay endpoint Activities oficial; alternativas: scraping `recent-activity/all/` con ToS friction, o API LinkedIn Marketing/UGC posts si MDP) |

### 3.2 Web / Newsletter

| Item | Evidencia |
|---|---|
| Implementación parcial | El handler existe (CHANNEL_WEB_RSS) pero el filtro [is_direct_rss_candidate](../../scripts/discovery/stage2_ingest.py#L464) rechaza cualquier URL que no termine en `.rss/.xml/.atom` o no contenga `/feed`. Substack canónico (p.ej. `pascalbornet.substack.com`) no matchea. |
| Tareas previas | [.agents/tasks/2026-03-23-015-codex-fase-3-research-web-runtime-hardening.md](../../.agents/tasks/2026-03-23-015-codex-fase-3-research-web-runtime-hardening.md), [.agents/tasks/2026-03-24-004-codex-accion-3-discovery-web-runtime.md](../../.agents/tasks/2026-03-24-004-codex-accion-3-discovery-web-runtime.md) (genérico, no apuntan a este canal) |
| ADR | sin ADR específico |
| Bloqueado por | nada técnico; falta: (a) auto-discovery de feed via `<link rel="alternate" type="application/rss+xml">` HTML head, (b) heurística Substack `${slug}/feed` |
| Cobertura potencial | Plan §2 cita Substack como secundario para Pascal Bornet, blogs personales. Estimación conservadora: **8-12 / 26** referentes con feed RSS resoluble por auto-discovery. |
| Costo relativo | **Bajo** — extender `is_direct_rss_candidate` + un `httpx.get(web_url)` + `BeautifulSoup` para extraer `<link rel="alternate">`. <100 LOC, reusa parser RSS existente. |

### 3.3 Otros canales (X, IG, Patreon, GitHub, Medium, Substack)

| Item | Evidencia |
|---|---|
| Spike / extractor previo | **ninguno** |
| Tareas previas | [.agents/tasks/2026-03-04-054-r12-cloud5-rrss-pipeline-n8n.md](../../.agents/tasks/2026-03-04-054-r12-cloud5-rrss-pipeline-n8n.md) (n8n approach, no integrado a Stage 2 actual) |
| ADR | sin ADR específico (ADR-005 es del lado de publicación, no de discovery) |
| Bloqueado por | Por plataforma: X/Twitter (ToS + API tier pago), Instagram (sin API pública para feeds de terceros), Patreon (RSS por-creator, podría tratarse como caso 3.2), GitHub (Atom feed `/$user.atom` — trivial, costo bajo), Medium (Atom feed `/feed/@$user` — trivial), Substack (caso 3.2) |
| Cobertura potencial | Marginal hoy — Plan §2 lista `Otros canales` como rich_text en Notion, no enumera referentes con dependencia exclusiva. Casos verificados: Pascal Bornet (Substack — cae en 3.2), no hay referente que dependa exclusivamente de X/IG. |
| Costo relativo | **Variable**: GitHub/Medium/Substack/Patreon = **Bajo** (Atom feeds estandarizados, agrupar bajo extensión de canal RSS). X/IG = **Alto** (API pago / scraping frágil) |

### 3.4 YouTube — `sin_acceso` residual (13 referentes)

Detallado en §6.1 porque es el ROI más alto.

---

## 4. Cobertura por referente — los 26 activos

Snapshot SQLite (último `fetched_at` por referente × canal):

| Métrica | Cuenta |
|---|---|
| Referentes con `youtube=ok` | **13** |
| Referentes con `youtube=sin_acceso` | **13** |
| Referentes con `rss=ok` | **4** |
| Referentes con `rss=http_error` | 10 |
| Referentes con `rss=sin_acceso` | 12 |
| Referentes con **al menos un canal OK** (any) | **14 / 26 (53.8%)** |
| Referentes **huérfanos** (todos los canales `sin_acceso`/`http_error`) | **12 / 26 (46.2%)** |

YouTube items por referente (top, fuente: `discovered_items` `WHERE canal='youtube'`):

```
Nate Gentile                  30 items   2 promovidos
Milos Temerinski              30 items   2 promovidos
Lucas Dalto                   30 items   0 promovidos
José Luis Crespo              30 items   1 promovido
Grant Sanderson               30 items   0 promovidos
Fred Mills                    30 items   3 promovidos
Daniel Shiffman               30 items   1 promovido
Cole Nussbaumer Knaflic       30 items   0 promovidos
Carlos Santana Vega           30 items   0 promovidos
Bernard Marr                  30 items   3 promovidos
Andrew Ng                     30 items   2 promovidos
Alex Freberg                  30 items   2 promovidos
Ruth Pozuelo Martinez         27 items   0 promovidos
```

**Lectura:** YouTube cubre exactamente la mitad del universo. La otra mitad (**12 huérfanos**) requiere LinkedIn o web/newsletter para entrar al pipeline. Sin alguno de esos dos, ~46% de los referentes nunca producirán candidatos editoriales.

---

## 5. Etapa 7 — estado de unblock para escritura Notion

**Plan §4 Etapa 7 dice:** *"Bloqueada hasta que el audit Notion MCP resuelva la autoridad de escritura."*

**Audit 006 ([.agents/tasks/2026-05-05-006-copilot-vps-audit-rick-notion-mcp-integration.md](../../.agents/tasks/2026-05-05-006-copilot-vps-audit-rick-notion-mcp-integration.md) §TL;DR + §6.5):**

> *"La premisa de la task era 'Rick tiene su propia MCP Notion integration en VPS'. **Esa premisa no se sostiene en runtime.** […] No hay capa MCP. […] Es REST puro encapsulado por el worker."*

> *§6.5 — Crear/actualizar tasks/pages/dashboards/reports → `worker/tasks/notion.py` (~1000 líneas, 11 handlers `handle_notion_*`). **Recomendación: usar siempre — está testeado, tiene retries, schema rígido.**"*

**Evidencia de runtime ya operativo:** `reports/stage4-push-20260507T050638Z-commit5.json` muestra `commit: true, created: 4, errors: 0` contra `database_id=b9d3d8677b1e4247bafdcb0cc6f53024` con `NOTION_API_KEY` (bot Rick, scope workspace Umbral BIM verificado en audit 006 §6.3).

**Conclusión Etapa 7:** ✅ **Desbloqueada técnicamente.** El bloqueo histórico era una falsa premisa (suponer MCP donde solo había REST). Lo que sigue **abierto pero no bloqueante**:

- **Hardening pendiente** (audit 006 §6.7, no ejecutado): allowlist DBs por subagent en `worker/tasks/notion.py` (`rick-delivery` no debería poder escribir en `Sesiones · David Moreira`).
- **Token rotation pendiente** (audit 006 §6.8 punto 4): 3 archivos de sesión OpenClaw contienen patrones que matchean `secret_/ntn_` — recomendación rotar y limpiar; reportado, no ejecutado.
- **Confirmación David** (audit 006 §6.8 punto 1): ¿quería un MCP server Notion nativo (caso B) o las 2 integrations REST existentes (caso A)? Si caso B, hay que instalar `@notionhq/mcp-server-notion`.

Ninguno de los tres bloquea la escritura del candidato editorial; bloquean iteraciones de seguridad/UX posteriores.

---

## 6. Recomendación de orden — qué canal atacar primero post-013-K

Ordenado por **ROI = cobertura ganada / costo de implementación**.

### 6.1 🥇 P1 — Resolver YouTube `sin_acceso` para los 13 referentes restantes

- **Costo:** **Bajo** (no nuevo extractor — el de 013-K ya funciona; el problema es upstream en parsing de la columna `YouTube channel` o falta de handle en Notion).
- **Beneficio:** **+13 referentes** (de 13/26 → 26/26 cobertura YouTube si todos tienen canal real).
- **Diagnóstico necesario:** auditar las 13 filas que dan `sin_acceso` — ¿qué hay en su columna `YouTube channel` (vacía vs URL no parseable vs handle inválido)?
- **Punto de entrada:** [scripts/discovery/stage2_ingest.py L127-150](../../scripts/discovery/stage2_ingest.py#L127-L150) — `parse_youtube_channel_id` y `youtube_rsshub_path`.
- **Riesgo:** algunos referentes simplemente no tienen YouTube (cota superior real probablemente <13).

### 6.2 🥈 P2 — Web / Newsletter auto-discovery de feed

- **Costo:** **Bajo** (<100 LOC: extender `is_direct_rss_candidate` + parser HTML `<link rel="alternate" type="application/rss+xml">` + heurística Substack `${slug}/feed`).
- **Beneficio:** **+8-12 referentes estimados** con Substack/blog (Pascal Bornet, otros con `Web / Newsletter` poblada en Notion).
- **Punto de entrada:** [scripts/discovery/stage2_ingest.py L464-471](../../scripts/discovery/stage2_ingest.py#L464-L471) (`is_direct_rss_candidate`) y L625-633 (`process_channel CHANNEL_WEB_RSS`).
- **Sinergia:** reusa parser RSS existente (L263-326), 0 dependencias nuevas excepto `beautifulsoup4` (ya en repo).

### 6.3 🥉 P3 — LinkedIn handler v0 con Token Generator manual

- **Costo:** **Med-Alto** — David debe ejecutar Token Generator del Developer Portal cada ~60 días manualmente (TTL access_token = 60d, sin refresh sin MDP). Parser de feed `recent-activity/all/` tiene fricción ToS. Alternativa: solo posts del propio perfil de David (no aplica a discovery de referentes).
- **Beneficio:** **+25 referentes potenciales** (Plan §2: 25/26 tienen LinkedIn — sin QuantumFracture).
- **Bloqueo real:** sin MDP no hay automatización del refresh; sin scraping no hay feed read. La elección es: (a) esperar MDP (sin ETA), o (b) decidir un workaround scraping con ToS risk.
- **Pre-requisito:** decidir scraping policy con David (riesgo cuenta personal) o esperar MDP.
- **Tareas relacionadas:** PR #339 (spike O18 — gap report), PR #340 (O18b — yaml fixes).

### 6.4 P4 (opcional) — GitHub / Medium / Substack via Atom feeds estandarizados

- **Costo:** **Bajo** (Atom feeds: `github.com/$user.atom`, `medium.com/feed/@$user`, `${slug}.substack.com/feed`).
- **Beneficio:** marginal — Plan §2 no lista referentes que dependan exclusivamente de estos. Pascal Bornet (Substack) ya cae bajo P2 si éste se hace primero.
- **Recomendación:** posponer hasta que P1+P2 estén estables y aparezca un referente concreto que lo requiera.

### 6.5 ❌ NO recomendado a corto plazo — X/Twitter, Instagram

- **Costo:** **Alto** (X API tier pago / IG sin API pública / scraping frágil + ToS).
- **Beneficio:** ningún referente del catálogo actual depende exclusivamente de estos (Plan §2 los lista en `Otros canales` como complementarios).

---

## 7. Acciones derivadas (no incluidas en este audit; sólo enumeración)

Este audit es read-only. Las acciones siguientes quedan como propuestas para tareas futuras:

1. **Diagnóstico de los 13 YouTube `sin_acceso`** — script auditor sobre `fetch_log.error` + columna `YouTube channel` en Notion. Spec: nueva tarea `028b-youtube-sin-acceso-diagnose`.
2. **Implementación P2 (Web auto-discovery)** — spec: nueva tarea `029-web-newsletter-feed-autodiscovery`.
3. **Decision-doc LinkedIn** — pedir a David: ¿esperar MDP o scraping con riesgo? Sin esa decisión, P3 está bloqueado a nivel producto.
4. **Hardening Notion (audit 006 §6.7)** — allowlist DBs por subagent + rotación tokens + cleanup de jsonl con secretos leakeados. No bloqueante de pipeline editorial pero sí de seguridad.

---

## 8. Quality gate del audit

- ✅ Read-only: 0 cambios runtime, 0 escrituras Notion, 0 código nuevo (solo este `.md`).
- ✅ Toda afirmación cita archivo + línea o reporte JSON existente.
- ✅ Sin invención: cobertura derivada de `state.sqlite` real; estados de canal derivados de comentarios literales en `stage2_ingest.py`; estado Etapa 7 derivado de audit 006 + reports `stage4-push-*-commit*.json`.
- ✅ Sin secretos: 0 tokens, 0 API keys (solo nombres de variables).
