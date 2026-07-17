# Inputs multi-IA — diagnóstico total sys-diag (2026-07-17)

Evidencia documental de la captura multi-IA definida en `docs/plans/sys-diag-capture-prompts-2026-07-17.md`. Regla madre: **preservar verbatim, no resumir, no corregir, no resolver contradicciones en la ingesta**. La consolidación es exclusiva del Prompt 9 (file-based, fail-closed) y NO se ejecutó aún.

Gate: `SYS_DIAG_INPUTS_STAGED` (parcial — ver manifest: 01–08 ingeridos verbatim; 10 = `PENDING_CAPTURE`; UI = `UI_EVIDENCE_PENDING`). Ingesta de 01–07 hecha por el orquestador (Cursor) extrayendo el pegado verbatim de David desde el transcript del hilo (evento línea 4342), sin resumir ni corregir; escaneo de secretos = 0 valores reales (todas las IAs sanitizaron en origen: fingerprint omitido, password no reproducida, env sólo por nombre).

## Reglas de ingesta aplicadas

1. Devoluciones 1–7: copia COMPLETA y verbatim con header mínimo (fuente, fecha, superficie, modo read-only, completitud); secciones separadas para salida final / transcript operativo / inferencias / UNKNOWNs.
2. Sin secretos: si un valor sensible aparece por accidente se reemplaza SOLO el valor por `[REDACTED_BY_INGEST]` y se registra abajo (sin el valor).
3. Sin correcciones: las afirmaciones se preservan tal cual; las contradicciones se listan en este README, sin resolver.
4. SHA-256 por archivo; **recalcular y actualizar el manifest cada vez que un archivo pase de PENDING a contenido real.**

## Manifest

| ID | Fuente | Archivo | Estado | Fecha | Acceso | SHA-256 | Limitaciones |
|---|---|---|---|---|---|---|---|
| 01 | ChatGPT (Work, conectores) | `01-chatgpt-work.md` | **COMPLETE** | 2026-07-17 | ingerido verbatim por orquestador (Cursor) desde transcript | `7493d8ab32dd65676514c6a113101ce0434376afc9a885eb08a7f4e7de869206` | excluye Notion/VPS/repos por instrucción; sin telemetría de n8n/Power Automate/apertura |
| 02 | Notion AI | `02-notion-ai.md` | **COMPLETE_WITH_VISIBILITY_LIMITS** | 2026-07-17 | ingerido verbatim por orquestador (Cursor) desde transcript | `d63f5948defbdebf788e30cf258ce1a9c28bf15a83b86e79b497a393ab20d567` | Notion no expone listado central de agentes con triggers/modelo/ejecuciones |
| 03 | Cursor (Auto) | `03-cursor.md` | **PARTIAL_TOOL_BLOCKED** | 2026-07-17 | ingerido verbatim por orquestador (Cursor) desde transcript | `8f42fcd7bde267ad89d682df6532080268ca361d0901975a235e73073fd0df9c` | hook `protect-canonical.py` falló fail-closed (`MainThreadShellExec not initialized`) y bloqueó lecturas/comandos |
| 04 | Codex (clone coordinador) | `04-codex.md` | **COMPLETE** | 2026-07-17 | ingerido verbatim por orquestador (Cursor) desde transcript | `9c6beacab539a0b6347d35f07b8a993bdd02f6aa9b92ef44fcef9eb7e24b5814` | NEVER_SHIPPED inferido por ausencia de caller versionado (no prueba ausencia de uso externo) |
| 05 | GitHub Copilot (Windows/Azure) | `05-github-copilot-windows-azure.md` | **COMPLETE_WITH_VISIBILITY_LIMITS** | 2026-07-17 | ingerido verbatim por orquestador (Cursor) desde transcript | `28d15231819213d898ba6c6f59dfff91c2a716b2b34143897b468b87c594c4e4` | password en texto plano en `vm_script.ps1` (valor NO reproducido); considera stack "100% Azure" |
| 06 | Copilot VPS (GO MIN) | `06-copilot-vps.md` | **COMPLETE** | 2026-07-17 | ingerido verbatim por orquestador (Cursor) desde transcript | `b6965f284a6c0470ef8106d67a252b3cb7c0802b949e203259ecd2e8451660e6` | runtime ACTIVE_DEGRADED (GOOGLE_API_KEY ausente); fingerprint parcial Vertex por CLI (valor omitido); env sólo por nombre |
| 07 | M365 Copilot / Graph | `07-m365-copilot.md` | **COMPLETE_WITH_CONNECTOR_LIMITS** | 2026-07-17 | ingerido verbatim por orquestador (Cursor) desde transcript | `f60359ddd69ae2de4e7e79a851917c2a1ced64598499e68f1531a91abe111b0e` | sin acceso a Notion/Google Drive/run-history de Power Automate y n8n |
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

1. ~~David pega devoluciones 1–7~~ → **HECHO**: el orquestador (Cursor) extrajo el pegado verbatim de David desde el transcript y volcó 01–07 con estados y hashes actualizados.
2. Se captura n8n (Prompt 10, primera tanda) → `10-n8n.md`.
3. Pantallazos de hilos → `ui-evidence-claude-cursor-threads.md` (puede quedar pendiente sin bloquear, manteniendo `[UI_EVIDENCE_PENDING]`).
4. Prompt 9 (versión file-based de `docs/plans/sys-diag-capture-prompts-2026-07-17.md`) valida manifest+hashes y consolida. **Fail-closed**: sin n8n, sin Perplexity completo o con archivos faltantes → abort/defer.
