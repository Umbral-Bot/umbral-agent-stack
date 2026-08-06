# P1.2 — KILL del set autorizado de 28 huérfanas (2026-08-06)

> **Pack:** PKG-UAS-P1-2-ORPHAN-KILL28 · rama `claude/pkg-uas-p1-2-orphan-kill28-20260806` · base `0f3251e0`
> **GO de David (verbatim):** "sí — autorizo borrar SOLO el set KILL de 28 ramas de
> `docs/ops/uas-p1-2-orphan-32-classify-2026-08-06.md` §3.1."
> **Precede:** [uas-p1-2-orphan-32-classify-2026-08-06.md](uas-p1-2-orphan-32-classify-2026-08-06.md)
> (PR #590, MERGED) — clasificó 32 huérfanas con merge-base en 28 KILL / 1 RESCUE / 3 KEEP.

---

## 1. Preflight (antes de cualquier delete)

- Las 28 ramas del set autorizado existen en `origin` (`git ls-remote --heads origin <rama>` × 28,
  28/28 `EXISTS`, 0 `MISSING`).
- Ninguna tiene PR open (`gh pr list --state open` devuelve solo `#541` y `#521`, ninguno de los
  28 nombres coincide).
- Cero solapamiento entre el set de 28 y el set explícitamente FUERA de alcance (`rescue/copilot-
  dirty-2026-07-13` [RESCUE], `codex/docs-pit-v2-contract`, `rescue/coordinador-dirty-2026-07-13`,
  `rick/stage7_5-multiformat` [los 3 KEEP]) — verificado por `comm -12`, resultado vacío.

Ninguna rama excluida del set original — las 28 se ejecutan tal cual, sin ampliar ni recortar.

## 2. Lista exacta (28, copiada del acta §3.1 antes del primer delete)

```
codex/cand-prod001-stage2
coord-ag-2a/build-push-aeco-source-crawler
copilot-vps/052-aeco-kb-build-blocked-pat-scope
copilot-vps/052-aeco-kb-pushed-visibility-manual
copilot-vps/recover-post-force-push-2026-05-06
copilot-vps/stage4-013e-execution-2026-05-07
copilot/burn-q2-o7-o9-delegates
copilot/docs-editorial-master-plan
copilot/docs-notion-schema-gates
copilot/docs-s6-s7-multiplatform-design
copilot/feat-o16-2-047-gap-closure
copilot/feat-o16-infra-base
copilot/feat-s0-s1-discovery
copilot/feat-s10-publish-guard
copilot/feat-s2-source-verification
cursor/cand001-magnific-megaprompt
evidence/openclaw-e2e-cycle-001
rescue/copilot-vps/editorial-contract-paths-backup-2026-07
rescue/copilot-vps/editorial-contract-paths-canonical-2026-07
rescue/copilot-vps/poller-hardening-2026-07
rick-delivery/notion-poller-healthcheck-hardening
rick/stage7_5-voice-v2
rick/stage7_5-voice-v3
tournament/umbral-agent-stack-375-fa19920/lane-docs-explanatory
tournament/umbral-agent-stack-440-462ef1c1/lane-backup-impl
tournament/umbral-agent-stack-440-462ef1c1/lane-backup-qa
tournament/umbral-agent-stack-445-d5f34a07/lane-sync-delivery
tournament/umbral-agent-stack-d35-33863db/lane-openclaw-skill
```

## 3. Ejecución

Un solo `git push origin :refs/heads/rama1 :refs/heads/rama2 ...` con las 28 refspecs.

| Métrica | Valor |
|---|---|
| N planificadas | 28 |
| N borradas (`[deleted]` confirmado por git) | **28** |
| N fallidas | **0** |

Post-check:

```
git ls-remote --heads origin > heads_final.txt
comm -12 <(sort kill28.txt) <(heads_final ramas)   # vacío — 0 residuales
```

Confirmación de que lo que **no** debía tocarse sigue vivo en `origin`:

| Rama | Estado |
|---|---|
| `rescue/copilot-dirty-2026-07-13` (RESCUE) | viva, `003bafc2` |
| `codex/docs-pit-v2-contract` (KEEP) | viva, `16e39b40` |
| `rescue/coordinador-dirty-2026-07-13` (KEEP) | viva, `16219f25` |
| `rick/stage7_5-multiformat` (KEEP) | viva, `a2635398` |
| `claude/plan-sys-diag-openclaw-worksystem-2026-07-17` (#541 open) | viva, `ba9b3486` |
| `copilot/docs-openclaw-models-hygiene-20260704` (#521 open) | viva, `7abfaa6f` |

`UAS_P12_ORPHAN_KILL28_PASS=Y` — 28/28, 0 fallidas, 0 residuales, RESCUE+KEEP+PR-open confirmados
vivos.

## 4. Prohibido (respetado)

- Cero borrado fuera de la lista de 28.
- Cero `--force` a `main`.
- Cero touch a RESCUE (`rescue/copilot-dirty-2026-07-13`) ni a los 3 KEEP.
- Cero touch a las 58 sin merge-base.
- Cero touch a `#541`/`#521`.
- Cero touch a VPS, Notion.
