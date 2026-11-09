# REPORT PKG-DIHR-VPS-02 — sesión «UAS - VPS», solo lectura, ventana 2026-11-09T05:50:44Z–05:53:33Z
Recibido por cross-session-message ~06:22Z. Texto del emisor. Gateway sin caída durante la lectura (NRestarts=7, arriba desde 2026-11-08T21:34:26Z; memoria disponible bajó a 618 MB → evitó comandos node pesados).

PASO 0 (05:50:44Z) PASS: sin logins; mismas 2 sshd notty (esta app) + túnel solo-reenvío; 0 agentes ajenos.

1 Agentes (05:50:44Z) — PASS: OpenClaw 2026.10.10 (7dc3350). openclaw.json: 9 agentes; primary openai/gpt-6.1-sol en main, rick-orchestrator, rick-delivery, rick-qa, rick-communication-director, rick-linkedin-writer, rick-editorial; openai/gpt-6-luna en rick-tracker y rick-ops; todos con 2 fallbacks; heartbeat en 8 (no linkedin-writer). defaults: gpt-6.1-sol + fallbacks [anthropic/claude-sonnet-5-5, openai/gpt-6-luna]; utilityModel gpt-6-luna. Binding único: main ← telegram (account *). Canal telegram enabled, dmPolicy/groupPolicy allowlist. `openclaw memory status`: NO PROBADO (memoria baja + duda de que consulte proveedor); índice ya leído en 01: gemini-embedding-001.

2 n8n (05:50:58Z) — PASS: v2.10.2; 2 workflows, 2 activos («B3 — Worker /health cron → alerta Telegram», «B1 — Telegram ‘ok publica’ → Worker /enqueue»). Últimas 5 ejecuciones: B3, success (04:45–05:45Z cada 15 min). 7 días: 672 success, 0 error. Fuente: ~/.n8n/database.sqlite (ro).

3 Editorial (05:51:15Z) — PASS (inventario) / sin actividad: sin cron del sistema ni unidad editorial. Interruptores en env: NOTION_POLLER_ENABLE_PROMOTE=true, EDITORIAL_BLOG_ASSET_UPLOAD=true (resto solo presentes: EDITORIAL_BLOG_FUNCTION_URL/KEY, CANONICAL_BASE_URL, NOTION_PUBLICACIONES_DB_ID, NOTION_SHORTLIST_DS_ID, GOOGLE_DRIVE_EDITORIAL_HITL_FOLDER_ID). ops_log 7 días: 0 eventos editoriales/promoción. Límite: no identificó cuáles interruptores leyó el corte del 4-nov; reporta los presentes.

4 Granola (05:51:29Z) — FAIL leve: cron diario 08:00 granola-gap-check; última corrida 2026-11-08 11:00Z → «Recent gaps detected». Estado /tmp/granola_gap_check_latest.json: total_pages 100, recent_issues 7, max_date 2026-11-05, freshness 3 d, stale=false. ops_log 7 días: 0 eventos granola. Sin contadores raw/procesados/pendientes en archivo de estado.

5 Worker/Dispatcher (05:51:47Z) — PASS: ops_log actual + archivo ~/exec-diag-2026-07/archive/ops_log.jsonl.1.gz (rotación por tamaño), 2026-11-02T05:52Z→11-09T05:51Z: task_completed 127.979, task_failed 17, llm_usage 158. Top tareas: notion.poll_comments 100.051, notion.read_database 27.266, notion.update_dashboard 168, ping 146, notion.add_comment 133. Fallos: nonexistent_task 8, notion.poll_comments 5 (Notion API devolvió HTML), llm.generate 3 (timeout del proxy OpenClaw), google.calendar.list_events 1 (auth no configurada). llm_usage por proveedor/modelo: openclaw_proxy claude-sonnet-4-6 59 + anthropic/claude-sonnet-4-6 25 + claude-3-haiku 7; azure_foundry gpt-5.3-codex 15, gpt-5.4 10; gemini-2.5-flash 8.

6 Costos (05:52:50Z) — NO PROBADO en montos (por diseño): quota-guard */15 corre («Checking claude_pro quota… Done», último 05:45Z) sin línea de estado. runtime-snapshot 2026-11-09T03:20Z (7 d): llm_usage tracked=false, tokens 0, estimated_cost_proxy_usd 0 — inconsistente con 158 llm_usage del ops_log; research_usage 13. Sin montos inferidos.

7 Mission Control (05:53:09Z) — PASS: /health 200; /risks 200 → pip-audit high mitigate_in_pr; env-acl medium local_hardening_required; board-drift medium watch; stale-prs medium needs_david_authorization; linkedin-autopublish high blocked_by_policy. /gates 200 → D6.1 AECO KB blocked_source_repair; D5/O15 Gmail+Calendar ready; editorial hitl_required; security watch; tests required. Token usado desde el entorno del servicio, no mostrado.

8 Supervisor/poller (05:53:25Z) — PASS: supervisor 05:50Z Redis/Worker/Dispatcher OK, «Restarted: none», sin errores en el log. Poller: daemon pid 1714 desde 2026-10-23; último poll_comments completado 05:52:53Z, 0 fallos en 24 h. ADR-010: 11 claves Redis notion:poll:cursor:* (TTL muestra ~30 días); valores no leídos.

OMITIDO: `openclaw memory status`; montos de costo; valores de cursores Redis; contenido de mensajes/páginas; credenciales (solo nombres/presencia); cualquier corrección (canario, heap, embeddings, Granola, Calendar auth).

## Nota del coordinador
- 100.051 `notion.poll_comments` en 7 días ≈ una llamada cada 6 s. Con 180 req/min por integración en el plan de Notion, es la mayor presión sobre la cuota del workspace y candidata a explicar los 429/HTML esporádicos y la competencia con escritores (P7).
- `runtime-snapshot` reporta tokens 0 / coste 0 con 158 `llm_usage`: la medición de coste está rota, no el gasto (P9).
- `/risks` de Mission Control ya incorpora «stale-prs needs_david_authorization» y «env-acl local_hardening_required»: coincide con hallazgos de TARRO (PRs draft antiguos, `.env` y clave suelta).
