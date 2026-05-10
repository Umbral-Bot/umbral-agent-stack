# Wave 2.A — Changelog update (2026-05-10)

Bitácora viva de eventos posteriores al review inicial #407 / #411
(`docs/audits/2026-05-10-wave2a-review-407-411.md`) y al status-update
del mismo día (`docs/audits/2026-05-10-wave2a-status-update.md`).

Este archivo registra eventos ya ocurridos y la decisión pendiente sobre
merge temprano de #407. No autoriza merges; cualquier ejecución requiere
autorización explícita de David.

---

## 2026-05-10 — VPS-1 PASS para #407 (stop button)

- HEAD verificado: 84cd0e8d (`copilot-vps/wave2a-405-stop-button`)
- Tests: 80/80 verdes en 0.50s
  (`test_publish_flags` + `test_publish_guard_flags_integration`)
- Smoke fail-closed defaults: OK
  (`publish_enabled=False`, `dry_run=True`, `max_posts=1`,
  `max_posts_per_day=1`)
- Smoke `runtime_block` event: OK (emitido en tempfile aislado,
  `PublishBlockedError` raised con
  `reasons=[publish_disabled, dry_run_enabled]`)
- `pgrep` + `systemctl --user list-units`: cero procesos publisher
  corriendo
- Restricciones: OK (solo `publish_flags.py` + `publish_guard.py` +
  tests + runbook `publish-emergency-stop` + `runtime-flags-contract` +
  `.gitignore` + `docs/audits`)
- Notas: fetch local stale (`ed1df2d`) resuelto con
  `reset --hard origin/...`; warning informativo
  `daily_cap_not_enforced` esperado (alineado con A1).
- Evidencia: hilo "RRSS 1 - VPS" sesión anterior.

---

## 2026-05-10 — RRSS 1 PARTIAL para #411 (publish_log)

- HEAD verificado: 2c6fe460 (`rrss-wave2a/404-lite-publish-log`)
- `gh` PR #411: `isDraft=true`, `labels=[do-not-merge, wave2]`,
  `state=OPEN`, `mergeable=MERGEABLE`
- `pytest tests/lib/test_publish_log.py`: 18/18 verdes en 0.43s
- Smoke `write_event` + `read_events` + append-only + `DEFAULT_PATH` +
  `TypeError`: OK
- No callers de `publish_log` fuera de `lib/tests`: OK
- Restrictions diff (en GitHub, sobre el PR remoto): OK — solo 3
  archivos esperados (`publish-log-contract.md`, `publish_log.py`,
  `test_publish_log.py`)
- PARTIAL motivo 1: el script smoke del runbook asserta
  `"timestamp" in events[0]` pero el writer usa `timestamp_utc`
  (alineado al contrato `publish-log-contract.md`). El módulo cumple el
  contrato; el runbook/spec tiene key vieja → fix doc-only pendiente.
- PARTIAL motivo 2: drift local del worktree (no del PR) por
  contaminación cross-thread de otra sesión Copilot-VPS que dejó commit
  `a60822d` encima de `2c6fe46` sin push. PR remoto intacto.
  Mitigación: prefix `git fetch && git reset --hard origin/<branch>`
  antes de evaluar diffs locales.
- Conclusión código: PASS. Conclusión global: PARTIAL por los dos
  puntos doc/proceso.
- Evidencia: hilo "RRSS 1" sesión actual.

---

## 2026-05-10 — RRSS 4 CREATED → PR #414 (#406 doc-only)

- Branch: `rrss-wave2a/406-source-use-and-secrets` (single commit
  `2b475fb` sobre `origin/main`)
- Archivos creados:
  `docs/editorial-pipeline/source-use-policy.md`,
  `docs/runbooks/secrets-and-tokens.md`
- secret-scan grep: CLEAN (solo nombres de env vars y regex
  neutralizados)
- `gh` PR #414: draft + `do-not-merge` + `wave2`
- Notas: primer intento de commit cayó en branch equivocada
  (`404-lite`) por estado persistente de shell; detectado, branch
  contaminada eliminada del remoto, recreada limpia desde
  `origin/main`, cherry-pick del docs commit, push limpio. PR final
  +359 líneas, 2 archivos, cero runtime touch.
- Evidencia: hilo "RRSS 4" sesión actual.

---

## 2026-05-10 — Decisión pendiente: merge temprano #407 con merge-commit

- Justificación: fail-closed sin callers, simplifica rebase #410,
  preserva ancestry (5 de 6 commits de #407 son base de #410).
- Método propuesto:
  `gh pr ready 407` →
  `gh pr edit 407 --remove-label do-not-merge` (opcional) →
  `gh pr merge 407 --merge` (NO squash).
- Estado: esperando autorización explícita de David. NO ejecutar
  todavía.
