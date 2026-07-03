---
id: "2026-07-03-010"
title: "PIT Telegram deliverables — deck PPT en Google Drive + link Rick"
status: done
assigned_to: copilot
created_by: david
priority: high
sprint: pit
created_at: "2026-07-03"
updated_at: "2026-07-03"
---

## Objetivo

Post-torneo PIT, Rick entrega por Telegram un resumen ejecutivo (≤12 líneas) + **link** al deck `.pptx` subido al Google Drive de Rick (carpeta compartida con David). Nunca el archivo adjunto. Reutilizable para todo torneo product v1. Gap cerrado: **PIT-TG-DRIVE**.

## MEGAPROMPT

PIT-TG-DRIVE-DELIVER-v1 (David, 2026-07-03). Autorización David: SÍ (link Drive, no adjunto).

## Entregables

- [x] `worker/tasks/google_drive.py` — `google_drive.upload_file` + `upload_presentation` (OAuth refresh env, guard carpeta PIT, share reader idempotente) + registro en `TASK_HANDLERS`
- [x] `scripts/pit/pit_build_outcome_deck.py` — outcome yaml (+spec/run-metrics) → 7-8 slides → `pit/<id>/deliverables/<id>-outcome-deck.pptx` (`PIT_DECK_BUILD_OK`)
- [x] `scripts/pit/pit_deliver_telegram_pack.py` — gate winner → deck → upload → `telegram_pack.json` con `summary_lines[]` (`PIT_DELIVER_PACK_OK|DRY_OK|FAIL`, `--dry-run`)
- [x] Skill `product-innovation-tournament` §Entrega Telegram post-torneo (plantilla fija + reglas duras + hard stop pptx-adjunto)
- [x] `pit_outcome_report.yaml` template — bloque `deliverables:` (drive_deck_url, drive_file_id, telegram_sent_at)
- [x] `docs/ops/pit-telegram-drive-deliverables-runbook.md` (OAuth paso a paso, FOLDER_ID, env chmod 600, smoke, integración, troubleshooting)
- [x] `docs/ops/pit-process-index.md` paso 8b + contrato ejecutable · `docs/62` §8 párrafo · `openclaw/env.template` placeholders GOOGLE_DRIVE_*
- [x] Deps: `worker/requirements.txt` + `pyproject.toml` extra `drive` (incluido en `all`)
- [x] Tests: `test_google_drive_upload.py` (12) + `test_pit_build_outcome_deck.py` (7) + `test_pit_deliver_telegram_pack.py` (8) — mocks, sin red
- [x] Task 010 + board + PR (sin merge sin David)

## Verificación

- Suite nueva: **27/27 passed**.
- Regresión PIT + document_generator + mission_control (Windows): **344 passed, 4 skipped**; 31 errors en `tests/mission_control/test_pit_preview.py` **pre-existentes en main** (fixture `symlink_to` requiere privilegios Windows; verificado con stash — fallan igual sin estos cambios; verdes en CI Linux).
- Sin secretos commiteados; env solo placeholders comentados.

## Handoff VPS (follow-up separado, David + Copilot-VPS)

1. Crear OAuth refresh token cuenta Rick (scope `drive.file` mínimo) — runbook §1.
2. `GOOGLE_DRIVE_PIT_FOLDER_ID` = carpeta compartida existente Rick↔David (runbook §2).
3. Añadir vars a `~/.config/openclaw/env` + `chmod 600` + `pip install google-api-python-client google-auth-oauthlib`.
4. Smoke: `python scripts/pit/pit_deliver_telegram_pack.py --pit-id <id> --dry-run`.
5. Smoke real: upload dummy (runbook §4.2) → ver link desde cuenta David.

## Veredicto

`PIT_TG_DRIVE_IMPLEMENTED | worker=google_drive.upload | deck_builder=OK | skill=OK | pendiente=OAuth VPS`
