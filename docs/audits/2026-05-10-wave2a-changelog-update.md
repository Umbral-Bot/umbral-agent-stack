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

---

## 2026-05-10 — #407 MERGED (autorizado por David)

- Autorización explícita: David, mismo día.
- Secuencia ejecutada desde Copilot Chat (no VPS):
  `gh pr ready 407` → `gh pr edit 407 --remove-label do-not-merge` →
  `gh pr merge 407 --merge` (no squash, sin `--delete-branch`).
- HEAD pre-merge: `84cd0e8d` (sin cambios desde VPS-1 PASS).
- CI pre-merge: SUCCESS en 3.11 y 3.12 (workflow Tests).
- Merge commit: `30e5489f29b962a8c651850830363638a3ed1d2e`.
- `origin/main` HEAD post-merge: `30e5489f`.
- PR #407 estado final: `MERGED` a `2026-05-10T09:47:15Z`.
- Branch `copilot-vps/wave2a-405-stop-button` preservada (no
  borrada — útil como base estable para rebase de #410).
- Restricciones respetadas: cero VPS touch, cero publish, cero cron,
  cero runtime cambio, cero edición Stage 7.5 / variants / O16.2 /
  Azure / GHCR / Notion writes productivos.

---

## 2026-05-10 — B (gap-check #411 hardening) — NO GAP

Verificación read-only contra `origin/rrss-wave2a/404-lite-publish-log`
HEAD `2c6fe460`, motivada por el addendum del plan
(`docs/audits/2026-05-10-wave2a-plan.md` líneas 67-76):
"#404-lite debe persistir `flags.publish_enabled`, `flags.dry_run`,
`flags.max_posts`, `flags.max_posts_per_day`, `block_reasons()`".

Cobertura del contrato `docs/editorial-pipeline/publish-log-contract.md`:

| Campo plan-required                  | Documentado | Writer-preserva | Test round-trip |
|---|---|---|---|
| `publish_enabled`                    | ✅          | ✅              | ✅               |
| `dry_run`                            | ✅          | ✅              | ✅               |
| `max_posts`                          | ✅          | ✅              | ✅               |
| `max_posts_per_day`                  | ✅          | ✅              | ✅               |
| `block_reasons` (lista)              | ✅          | ✅              | ✅               |
| `cross_validation` (lista warnings)  | ✅          | ✅              | ✅               |
| `publication_content_hash`           | ✅          | ✅              | ✅               |
| `source_content_hash`                | ✅          | ✅              | ✅               |
| `would_publish`                      | ✅          | ✅              | ✅               |
| `gate_outcomes` (dict 6 gates)       | ✅          | ✅              | ✅               |

Mecanismo: `write_event(event)` hace `dict(event)` shallow copy +
`setdefault("timestamp_utc", _utc_now_iso())`; no descarta keys. El
test `test_roundtrip_contract_shaped_event`
(`tests/lib/test_publish_log.py`) ejercita los 13 campos del contrato y
asserta `evt[k] == v` para cada uno.

Conclusión B: **NO HAY GAP.** El writer #411 ya cumple el addendum del
plan. La integración con `publish_guard` (que es quien debe llenar esos
campos) sigue siendo trabajo de un PR posterior, fuera de #411.

---

## 2026-05-10 — A (doc-fix `timestamp` → `timestamp_utc` en #411) — NO-OP en repo

Auditoría exhaustiva del eje `timestamp` vs `timestamp_utc`:

- `git grep '"timestamp" in events'` sobre TODAS las refs remotas:
  cero coincidencias en código/runbook/contract/tests.
  Única aparición: este propio changelog auto-referenciándose
  (línea 49 del entry RRSS 1).
- `docs/runbooks/publish-emergency-stop.md` (en main post-merge #407):
  solo hace `tail -200 ~/.config/umbral/publish_log.jsonl`, sin
  asserts sobre keys.
- `docs/audits/2026-05-10-wave2a-vps-prompts.md` (sección VPS-3, smoke
  de #411): usa `print('events:', read_events())` — sin assert.
- `docs/editorial-pipeline/publish-log-contract.md`: solo
  `timestamp_utc`.
- `scripts/discovery/lib/publish_log.py`: solo `timestamp_utc`.
- `tests/lib/test_publish_log.py`: solo `timestamp_utc`.

Conclusión A: el "doc bug" reportado en el entry RRSS 1 fue
**transitorio en un prompt enviado a Copilot-VPS** (smoke ad-hoc), NO
una inconsistencia persistida en el repo. **No hay archivo que
modificar en branch #411.** El repo ya es coherente sobre la key
canónica `timestamp_utc`.

Recomendación: dejar el motivo 1 del PARTIAL de RRSS 1 como nota
histórica del proceso, no como bug abierto. El PARTIAL queda reducido
al motivo 2 (drift local cross-thread, ya mitigado con la regla
`fetch + reset --hard` documentada en user memory
`cross-repo-handoff-rules.md`).

---

## 2026-05-10 — Estado actual de PRs Wave 2.A

| PR | Branch | HEAD | Estado |
|---|---|---|---|
| #407 | `copilot-vps/wave2a-405-stop-button` | `84cd0e8d` | **MERGED** (`30e5489f`) |
| #410 | `rrss-wave2a/402-publication-content-hash` | `3a2dc4d8` | open / draft / `do-not-merge` — **rebase pendiente** sobre nuevo `origin/main` |
| #411 | `rrss-wave2a/404-lite-publish-log` | `2c6fe460` | open / draft / `do-not-merge` — código PASS, contrato cumple plan, sin doc-fix necesario; listo para VPS-3 + merge cuando David autorice |
| #412 | `rrss-wave2a/docs-and-prompts` | (este commit) | open / draft / `do-not-merge` — bitácora viva |
| #414 | `rrss-wave2a/406-source-use-and-secrets` | `2b475fb` | open / draft / `do-not-merge` — doc-only, mergeable en cualquier momento |

---

## 2026-05-10 — Próxima decisión requerida de David

Tres caminos no-bloqueantes que pueden ejecutarse en paralelo o en
serie según prioridad. NINGUNO requiere ejecución todavía:

1. **Rebase #410** sobre nuevo `origin/main` (post-#407). Conflicto
   esperado en `scripts/discovery/lib/publish_flags.py` resuelto con
   `git checkout --theirs` (preservar A1 fix de #407). Push
   `--force-with-lease`. Después: VPS-2 (review profundo + tests).
2. **Merge #414** (#406 doc-only, sin dependencias técnicas, ya verde).
3. **Merge #411** (#404-lite, código PASS, contrato cumple plan,
   restricciones intactas; opcional VPS-3 antes de merge).

Recomendación: primero (1) rebase #410 para liberar el siguiente
bloqueante de la cadena del plan, y en paralelo (2) merge #414 (cero
riesgo). #411 puede mergearse cuando lo decidás.

NO ejecutado: VPS-2, VPS-3, rebase #410, merges #410/#411/#414/#412,
n8n, O16.2, Stage 7.5, runtime.
