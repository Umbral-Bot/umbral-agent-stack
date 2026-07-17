# Inputs multi-IA — diagnóstico total sys-diag (2026-07-17)

Evidencia documental de la captura multi-IA definida en `docs/plans/sys-diag-capture-prompts-2026-07-17.md`. Regla madre: **preservar verbatim, no resumir, no corregir, no resolver contradicciones en la ingesta**. La consolidación es exclusiva del Prompt 9 (file-based, fail-closed) y NO se ejecutó aún.

Gate: `SYS_DIAG_INPUTS_STAGED` (parcial — ver manifest: 01–07 esperan el pegado de David; 08 ingerido; 10/UI placeholders).

## Reglas de ingesta aplicadas

1. Devoluciones 1–7: copia COMPLETA y verbatim con header mínimo (fuente, fecha, superficie, modo read-only, completitud); secciones separadas para salida final / transcript operativo / inferencias / UNKNOWNs.
2. Sin secretos: si un valor sensible aparece por accidente se reemplaza SOLO el valor por `[REDACTED_BY_INGEST]` y se registra abajo (sin el valor).
3. Sin correcciones: las afirmaciones se preservan tal cual; las contradicciones se listan en este README, sin resolver.
4. SHA-256 por archivo; **recalcular y actualizar el manifest cada vez que un archivo pase de PENDING a contenido real.**

## Manifest

| ID | Fuente | Archivo | Estado | Fecha | Acceso | SHA-256 | Limitaciones |
|---|---|---|---|---|---|---|---|
| 01 | ChatGPT (Work, conectores) | `01-chatgpt-work.md` | **PENDING_PASTE** (esperado: COMPLETE) | 2026-07-17 | pendiente pegado David | `a48fe202f75f63b67e8fb32391c186236e4b473e66c2529189833523c44b5b17` | hash = placeholder |
| 02 | Notion AI | `02-notion-ai.md` | **PENDING_PASTE** (esperado: COMPLETE_WITH_VISIBILITY_LIMITS) | 2026-07-17 | pendiente pegado David | `1a9f38f16cf808aba1bd55b9974c6c4bddc039bdd1c4791c269a564c41bc1d5c` | hash = placeholder; no ve triggers/modelo/última ejecución de todo |
| 03 | Cursor (Auto) | `03-cursor.md` | **PENDING_PASTE** (esperado: PARTIAL_TOOL_BLOCKED) | 2026-07-17 | pendiente pegado David | `59871ab1cb6babffdb0c2b7046c174c7d901065cd30b109830cd804eccc05c3b` | hash = placeholder; hook fail-closed bloqueó verificación roots/dirty |
| 04 | Codex (clone coordinador) | `04-codex.md` | **PENDING_PASTE** (esperado: COMPLETE) | 2026-07-17 | pendiente pegado David | `7a76989482bf3838f4b99c71b6dd60f1ddd15f8c285126ee1cd7e94f7153c71c` | hash = placeholder |
| 05 | GitHub Copilot (Windows/Azure) | `05-github-copilot-windows-azure.md` | **PENDING_PASTE** (esperado: COMPLETE) | 2026-07-17 | pendiente pegado David | `0bb5b0fa3c457b38577d346c4072a9f82476be15ef53d5f3433d3c436f718034` | hash = placeholder |
| 06 | Copilot VPS (GO MIN) | `06-copilot-vps.md` | **PENDING_PASTE** (esperado: COMPLETE) | 2026-07-17 | pendiente pegado David | `257c57a3727609085b52a84d2cef3d6a733bb235a29eb527f9fa6a4cddaa72b8` | hash = placeholder |
| 07 | M365 Copilot / Graph | `07-m365-copilot.md` | **PENDING_PASTE** (esperado: COMPLETE_WITH_CONNECTOR_LIMITS) | 2026-07-17 | pendiente pegado David | `946e3ce8d0c50cccb95a493b0700eddd27bea1242e9bf8216e967e3dc8cc9c7b` | hash = placeholder |
| 08 | Perplexity Pro (research externo) | `08-perplexity-research.md` | **COMPLETE** | 2026-07-17 (fuente mtime 12:20 ET) | OK — copiado verbatim de Drive | `cae19eec22413af48c847f932f5010b2fc3df93008d99cb8ffe8d10f3b5aff7d` | investigación externa pura; no describe el stack de David (por diseño) |
| 10 | n8n (MCP/UI) | `10-n8n.md` | **PENDING_CAPTURE** | 2026-07-17 | no capturado (regla: no auditar n8n en esta misión) | `3be8edb67f736e470bcba5effae4fc4015d9842ff175b76b73d5a658df3cf3e4` | n8n vivo en VPS sin export canónico en git |
| UI | Pantallazos hilos Claude/Cursor/Codex | `ui-evidence-claude-cursor-threads.md` | **UI_EVIDENCE_PENDING** | 2026-07-17 | pendiente David | `db5312d6f01c2b7f8dcf736545d6cdf6d386769fec977016f3d00c439f7462f9` | sin capturas, correspondencia clone↔hilo NO confirmada |

Fuente exacta del input 8 (para trazabilidad): `G:\Mi unidad\04_Recursos\Referencias e Investigacion\Investigacion\Perplexity\Umbral Agent Stack\Investigación  mejores prácticas multi-agente 2025-2026.md` (32.145 bytes, 144 líneas, escaneo de secretos: 0).

## Registro de redacciones por ingesta

- (ninguna hasta ahora — 0 valores redactados)

## Registro de contradicciones (SIN resolver — insumo del contradiction ledger del Prompt 9)

1. **Ramas UAS no mergeadas**: ~239 / 263 / 236 según método, momento y herramienta de conteo (git local vs gh vs capturas de otras IAs). Métrica sensible al método; ninguna cifra elegida aún.
2. **Worker — tres números**: 118 handlers registrados; 445 ejecuciones recientes en memoria en el momento del reply de Rick; 1000 en captura VPS posterior (tope `MAX_TASK_HISTORY`). Métricas de ejes distintos (catálogo vs buffer) — documentado en inventario §4-bis; queda en el ledger porque las fuentes multi-IA pueden reintroducir la confusión.
3. **SIM**: el runtime ejecuta los crons correctamente (salud técnica OK) y a la vez el valor operativo es ACTIVE_NOISY/posible DISABLE. Salud técnica ≠ utilidad para David; ambas afirmaciones son ciertas en ejes distintos.
4. **Notion AI** atribuye ACTIVE_HEALTHY a superficies donde no puede ver triggers/modelo/última ejecución → etiqueta con evidencia insuficiente; degradar a UNKNOWN en consolidación salvo confirmación cruzada.
5. **Cursor** no pudo verificar roots/dirty por fallo fail-closed de su hook → su devolución es PARTIAL; no usar sus vacíos como "no existe".
6. **Codex** infiere NEVER_SHIPPED por ausencia de callers versionados; eso NO prueba ausencia de uso externo/VPS (contraejemplo conocido: skills solo-live).
7. **Copilot Windows** considera el stack "100% Azure", pero OpenClaw rutea por OAuth ChatGPT y existen perfiles Google/Vertex en el auth store.
8. **VPS**: fingerprint parcial de credencial Google Vertex expuesto por salida de CLI (`openclaw models status`) → SECURITY_RISK; valor NO reproducido en ningún doc.
9. **`vm_script.ps1`**: contiene una credencial en texto plano → SECURITY_RISK **urgente**; valor NO reproducido; tratar como urgencia de seguridad separada (rotación = decisión David, fuera de esta misión).
10. **n8n**: systemd confirma servicio vivo; M365 observa huellas de flujos; falta inventario/API/export directo → tres señales parciales sin inventario canónico.
11. **Poller**: últimas 500 líneas de log limpias vs ventana de 48h con errores reales y gran volumen histórico → "limpio" depende de la ventana; declarar siempre la ventana.
12. **Crons ACTIVE_HEALTHY solo por ejecución/log**: ejecutar sin error no demuestra valor ni éxito funcional (caso SIM, caso dashboard-rick invertido: log existente pero 100% Permission denied).

## Ciclo de vida

1. David pega devoluciones 1–7 → se vuelcan verbatim a sus archivos, se actualizan estados y hashes.
2. Se captura n8n (Prompt 10, primera tanda) → `10-n8n.md`.
3. Pantallazos de hilos → `ui-evidence-claude-cursor-threads.md` (puede quedar pendiente sin bloquear, manteniendo `[UI_EVIDENCE_PENDING]`).
4. Prompt 9 (versión file-based de `docs/plans/sys-diag-capture-prompts-2026-07-17.md`) valida manifest+hashes y consolida. **Fail-closed**: sin n8n, sin Perplexity completo o con archivos faltantes → abort/defer.
