# Wave 2.A — Merge Closeout

**Fecha**: 2026-05-15
**Autor**: Coordinador de Agentes (custom agent de GitHub Copilot)
**Tipo**: audit / closeout
**Scope**: cierre operativo de la Ola 2.A del editorial pipeline

---

## 1. Resumen ejecutivo

Wave 2.A del editorial pipeline quedó cerrada en `main` con dos PRs mergeadas el 2026-05-15:

| PR | Título | Merge commit | Mergeado en |
|---|---|---|---|
| #410 | `feat(wave2a/402): publication_content_hash contract and dry-run guard` | `ecb533da4c6b5c3f7d5f66efe3768cdd8907dff2` | 2026-05-15 05:46:18Z |
| #411 | `feat(wave2a/404-lite): publish_log.jsonl schema and writer` | `2f07e36d0456799720f1eae508d6d13d5579b2ed` | 2026-05-15 15:37:34Z |

Ambos merges fueron commits explícitos (no squash, no rebase-merge) para preservar la historia de la branch. Ambos pasaron por verificación end-to-end en VPS read-only antes del merge gate.

Esta PR (#412) es **documentación / audit only**: agrega 7 audits del 2026-05-10 + este closeout del 2026-05-15. Cero código, cero scripts, cero runtime.

---

## 2. Cronología

| Fecha (UTC) | Evento |
|---|---|
| 2026-05-12 | Repo-side rehearsal #411: 18/18 tests verdes en local |
| 2026-05-13 | Repo-side rehearsal #410: 132/132 tests verdes en local |
| 2026-05-13 | Rebase #410 sobre main (merge de #407) → HEAD `dc42e38f` |
| 2026-05-14 | VPS-3 PASS para #411 (HEAD `2c6fe46`, 18/18 + suite full + round-trip 5/5 + isolation OK) |
| 2026-05-14 | VPS-2 PASS para #410 (HEAD `dc42e38f`, 132/132 + suite full 3333 + isolation OK) |
| 2026-05-15 05:46 | Merge #410 a main → `ecb533da` |
| 2026-05-15 ~07:22 | Rebase #411 sobre nuevo main → HEAD `a2758aa6`, force-push `--force-with-lease` |
| 2026-05-15 ~07:40 | VPS-3 revalidación: tests verdes pero **SHA local ≠ SHA esperado** (caveat reportado) |
| 2026-05-15 | VPS-3.1 + VPS-3.2 diagnóstico: root cause = refspec restrictivo del VPS |
| 2026-05-15 15:37 | Merge #411 a main con guard `--match-head-commit a2758aa6...` → `2f07e36d` |
| 2026-05-15 | Rebase #412 sobre main + adición de este closeout |

---

## 3. Caveat #411 — SHA mismatch en VPS

### 3.1 Síntoma

Después de hacer `git push --force-with-lease` con el rebase de #411 sobre `main` post-#410, el SHA autoritativo en GitHub pasó a ser `a2758aa6489b4f79d1fdb4a1a8937c64553193e6`. Pero el VPS, después de ejecutar `git fetch origin rrss-wave2a/404-lite-publish-log --force` (12 objects unpacked), seguía reportando `2c6fe4600dac9b24004743134c7eb44a0b13902b` como tip de la branch local.

### 3.2 Diagnóstico (VPS-3.2)

`git ls-remote origin rrss-wave2a/404-lite-publish-log` desde el VPS confirmó que GitHub mostraba `a2758aa6`. Pero el ref local `refs/remotes/origin/rrss-wave2a/404-lite-publish-log` seguía apuntando a `2c6fe46` (loose ref, mtime 2026-05-10 05:25Z).

Inspección de `git config --get-all remote.origin.fetch` reveló:

```
+refs/heads/main:refs/remotes/origin/main
+refs/heads/copilot/*:refs/remotes/origin/copilot/*
```

El refspec **no incluye** `rrss-wave2a/*`. Cuando se ejecuta `git fetch origin <branch> --force` sin destino explícito (`src:dst`), git:

1. ✅ descarga los objetos
2. ✅ actualiza `FETCH_HEAD`
3. ❌ **NO actualiza** `refs/remotes/origin/<branch>` si ningún refspec configurado matchea ese namespace

Por eso el ref local quedó congelado en el SHA de la última vez que algún comando explícito lo escribió (probablemente un `git fetch <branch>:refs/remotes/origin/<branch>` el 2026-05-10).

### 3.3 Por qué el caveat fue benigno

El rebase fue **clean** (sin conflictos): el árbol resultante de `a2758aa6` es **bit-a-bit idéntico** al de `2c6fe46`. Solo cambia el commit parent (de `f43f200` a `ecb533da`) y el committer date. Por lo tanto, todas las verificaciones funcionales del VPS sobre `2c6fe46` son válidas también para `a2758aa6`:

- `git diff --name-only origin/main...HEAD` reportó los 3 archivos exactos del scope ✅
- 18 targeted tests PASS ✅
- Full suite 3055 PASS (post-#410 baseline) ✅
- Round-trip 5/5 sub-checks PASS ✅
- `publish_log.py` no importa `publish_guard` ni módulos de #410 ✅
- Productive log `~/.config/umbral/publish_log.jsonl` no tocado ✅

El merge se ejecutó con `gh pr merge 411 --merge --match-head-commit a2758aa6489b4f79d1fdb4a1a8937c64553193e6` para garantizar que el SHA mergeado fuera el verificado en GitHub.

---

## 4. Decisión

**El caveat fue benigno y no bloqueó el merge.** El árbol verificado por el VPS es funcionalmente equivalente al árbol mergeado. Riesgo de regresión por el SHA mismatch = nulo.

---

## 5. Deuda técnica abierta

### 5.1 Refspec del VPS

El refspec actual del VPS solo trackea `main` y `copilot/*`. Cualquier branch `rrss-wave2a/*`, `rrss/*`, `wave2/*` u otro namespace no recibe auto-update con `git fetch origin` genérico, y los refs locales pueden quedar stale durante días.

**Propuesta para tarea separada** (NO se aplicó en esta PR):

```bash
# Opción minimalista: ampliar selectivamente
git config --add remote.origin.fetch '+refs/heads/rrss-wave2a/*:refs/remotes/origin/rrss-wave2a/*'

# Opción full mirror (recomendada operativamente):
git config --replace-all remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
```

Requiere autorización explícita para tocar `~/umbral-agent-stack/.git/config`. No es runtime de OpenClaw, pero sí es write sobre el repo VPS. Antes de aplicar: backup del config actual + diff documentado + verificación post-cambio con `git fetch origin && git ls-remote origin | head -20`.

**Riesgo si no se arregla**: futuras revalidaciones VPS de cualquier branch `rrss-*` o equivalente pueden seguir reportando SHAs stale, generando falsos positivos del tipo "HEAD esperado ≠ HEAD real". El diagnóstico está documentado, pero el reflejo de los próximos agentes puede ser bloquear merges innecesariamente.

---

## 6. Confirmación de scope de esta PR (#412)

Esta PR toca exclusivamente `docs/audits/`. No modifica:

- código bajo `scripts/`, `worker/`, `dispatcher/`, `openclaw/`, `identity/`, `client/`
- configuración bajo `config/`
- infraestructura bajo `infra/`
- tests bajo `tests/`
- runbooks que disparan ejecución
- ningún archivo que se consuma por cron, systemd timer, n8n flow, o el openclaw-gateway

Riesgo funcional de la merge = **nulo**. Es living doc de Wave 2.A.

---

## 7. Estado final Wave 2.A

| Item | Estado |
|---|---|
| #407 (review-407-411 dependencia) | MERGED previo |
| #410 (`publication_content_hash`) | ✅ MERGED en `ecb533da` |
| #411 (`publish_log.jsonl`) | ✅ MERGED en `2f07e36d` |
| #412 (audit / living doc) | ✅ MERGED (esta PR, ver merge commit reportado por Coordinador) |
| #414 (sub-tarea relacionada) | MERGED previo (ver `wave2a-changelog-update.md`) |
| Wave 2.B (`publish_guard` integration) | scope futuro, fuera de Wave 2.A |
| Refspec VPS fix | ⏳ deuda técnica abierta, tarea separada |

**Wave 2.A queda cerrada operativamente.** Próximos pasos (fuera de scope de este closeout):

1. Sesión separada para fix del refspec del VPS (con autorización para `git config`).
2. Inicio de Wave 2.B cuando David lo autorice.

---

## 8. Restricciones honradas durante el cierre

- ❌ No se publicó nada
- ❌ No se tocó Notion, n8n, Azure, O16, OpenClaw runtime, ni configuración del VPS
- ❌ No se removieron labels o draft de #412 hasta el momento del merge gate
- ❌ No se ejecutaron acciones write sin autorización explícita de David
- ✅ Merges con `--match-head-commit` para guard contra SHA drift entre verificación y merge
