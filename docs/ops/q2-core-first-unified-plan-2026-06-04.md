# Plan unificado core-first Q2 (2026-06-04)

- **Veredicto:** `UNIFIED_PLAN_CONSENSUS_READY` (Codex + Cursor, evidence-based).
- **Base git:** `main` @ `3f14319d` (verificar con `git log -1` antes de ejecutar).
- **Lead prompts:** Cursor. **Runtime torneos/MC/poller:** Copilot-VPS. **Judge/merge/Azure:** Copilot Windows.

## Tabla de verdad (snapshot)

| Ítem | Estado | Superficie | Siguiente |
|------|--------|------------|-----------|
| D3.4 retro | DONE `M1_D34_TOURNAMENT_RETRO_OK` | repo | D3.5 solo si David autoriza |
| D4.1 código | DONE (#448 merged + VPS post-merge) | repo | — |
| D4.2 MC deploy | DONE (`mission-control=active`, `/health` OK) | VPS | monitorear read-only |
| D5.3 poll | poll OK; **Granola soak DEGRADED** aparte | VPS | track O8 |
| D6.1e KB | DONE alias `aeco-kb-es-current`, 1187 docs | Windows/Azure | no reabrir salvo regresión |
| O15 skills | DONE board `O15_OPENCLAW_WORKSPACE_SKILLS_OK` | repo/VPS | alinear spine |
| PR #442/#443 | OPEN, CONFLICTING, stale D3.2 | GitHub | inventario → cierre con autorización |
| PR #449 | MERGED 2026-06-04 | GitHub | cabecera core-first actualizada |
| eval #462 | MERGED | repo | usar en MC/evals |

## Secuencia acordada

1. **P4** — Inventario read-only PRs + drift docs → `TRACKER_CLEANUP_INVENTORY_READY`.
2. **P4-close** — Cerrar stale solo con `autorizo cerrar PR #NNN` por PR.
3. **O8** — Granola soak (no confundir con poll bootstrap OK).
4. **D3.6** — Plugin + skill GitHub CLI para lanes → [`d36-tournament-github-cli-plugin-roadmap-2026-06-04.md`](d36-tournament-github-cli-plugin-roadmap-2026-06-04.md).
5. **D3.5** — Torneo limpio opcional → [`d35-tournament-judge-kit-2026-06-04.md`](d35-tournament-judge-kit-2026-06-04.md); exige skill `tournament-github-cli` en VPS.
6. **Editorial** — Wave 2 + HITL Notion; **cero publicación** hasta doble gate.
7. **Lead Intel** — Después de KB + MC estables.
8. **Friday retro** — Actualizar spine/board sin drift.

## Gates David (frases exactas)

| Acción | Frase |
|--------|-------|
| Cerrar PR stale | `autorizo cerrar PR #442` / `#443` |
| Torneo limpio | `autorizo D3.5 clean tournament rerun` |
| Merge winner torneo | `autorizo merge winner D3.x` (+ PR número si aplica) |
| Patch docs spine | `autorizo patch docs-only unified plan` |
| Publicar LinkedIn | `aprobado_contenido` + `autorizar_publicacion` + `ok, publica` |

## Contradicción resuelta (MC vs tracker)

- Antes del deploy MC: **PROMPT 3 antes que tracker** (Plan B correcto).
- Con MC verificado en VPS: **siguiente paso real = PROMPT 4 inventario**.

## Referencias

- Prompt pack activo: [`core-first-next-prompts-2026-06-03.md`](core-first-next-prompts-2026-06-03.md)
- Retro torneos: [`d3-tournament-retro-2026-06-02.md`](d3-tournament-retro-2026-06-02.md)
- Protocolo: [`docs/79-tournament-protocol-openclaw-native.md`](../79-tournament-protocol-openclaw-native.md), [`docs/architecture/tournament-protocol.md`](../architecture/tournament-protocol.md)
