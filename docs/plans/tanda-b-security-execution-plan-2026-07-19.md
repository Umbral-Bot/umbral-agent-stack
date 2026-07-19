# Plan de ejecución — Tanda B (seguridad) — 2026-07-19

Estado: **PLAN** (mesurado, reversible, fail-closed). **No implementa, no despliega, no rota, no edita runtime.**
Base: `origin/main` @ `843fb27b` (Tanda A ya live, `PKG_TANDA_A_LIVE_PASS`).
Fuente: `docs/audits/sys-diag-openclaw-inventory-final-2026-07-17.md` §7 + inputs `05-github-copilot-windows-azure.md` y `06-copilot-vps.md`.

> **Regla madre de esta tanda**: ningún paso pide imprimir, pegar, leer o reproducir valores de passwords, tokens, fingerprints o `.env`. B1/B2/B3 son **rotaciones/movimientos de secretos → solo David**: el agente prepara runbook y checklist, nunca ejecuta la rotación. B4 es el único ítem que puede volverse un PR de código/config, y aquí solo se diseña su alcance.

## 1. Resumen ejecutivo

Cuatro frentes de seguridad, dos naturalezas distintas que **no deben mezclarse**:

- **B1, B2, B3 = higiene de secretos** → acción intrínsecamente humana (rotar/mover credenciales). El agente no toca ningún secreto; solo entrega el runbook sin valores y verifica lo que sea observable sin leer el secreto. Superficies: máquina Windows local de David (B1, B3-parte) y auth store del gateway en VPS (B2, B3-parte).
- **B4 = contención de publicación LinkedIn/imagen** → riesgo de *ejecución*, no de fuga. `stage9c` publicaría bajo identidad personal legacy contra el contrato Company-page (ADR-009-A); `stage8` usa un proveedor de imagen superado (ADR-006). Hoy **ningún cron/pipeline los invoca** (verificado: sin callers en `scripts/`, `config/`, `.github/`), así que el riesgo es manual/accidental o un cableado futuro. B4 puede ser un PR de guardrail fail-closed.

Prioridad por daño potencial × exposición: **B2 ≈ B1 > B4 > B3**. B2 (credencial live de un proveedor cloud, expuesta por un bug del CLI que cualquier `openclaw models status` re-emite) y B1 (password de VM de ~5 meses en texto plano) son las urgentes. B3 es higiene local sin fuga demostrada por git (env.rick gitignored, token-map.csv sin abrir). B4 no fuga nada; contiene una vía de mal-uso.

## 2. Matriz B1–B4 — humano vs agente vs prohibido

| Ítem | Superficie exacta | Solo-HUMANO (David) | AGENTE tras GO | PROHIBIDO en esta tanda | Destinatario | Tamaño | Depende de |
|---|---|---|---|---|---|---|---|
| **B1** | `C:\Users\david\vm_script.ps1` (Windows local) + credencial de la VM Hyper-V "OpenClaw" | rotar password de la VM; migrar a vault (DPAPI/Credential Manager); borrar el valor del script | (opcional) preparar plantilla de script que lea de vault, **sin** el valor; verificar por nombre que el vault tiene la entrada | leer/editar/mover `vm_script.ps1`; imprimir el password | David (rota) · Copilot Windows (plantilla opcional) | S | — |
| **B2** | perfil `google-vertex` en el auth store del gateway (`~/.openclaw/…`, VPS) + bug de salida de `openclaw models status` | rotar/eliminar el perfil Vertex desde la consola de Google Cloud + `openclaw` | reportar el bug del CLI upstream; diseñar/ajustar `secret-output-guard` para enmascarar fingerprints parciales (PR futuro, no en este plan) | ejecutar `openclaw models status` sin el guard; reproducir el fingerprint; tocar el auth store | David (rota en GCP) · Claude Code (guard/CLI, PR aparte) | S | — |
| **B3** | `env.rick` (raíz repo, **gitignored**, local) + `C:\Users\david\Documents\_audit-2026-07\token-map.csv` (local) | revisar contenido de ambos; mover `env.rick` fuera del repo o a vault; decidir destino de `token-map.csv`; rotar lo que corresponda | (opcional) confirmar por `git ls-files`/`git check-ignore` que `env.rick` no está trackeado (ya verificado: gitignored, no en índice) | abrir/mover/borrar `env.rick` o `token-map.csv`; imprimir cualquier clave/valor | David | S | B1/B2 (mismo criterio de rotación) |
| **B4** | `scripts/discovery/stage9c_linkedin_publish.py` (LinkedIn `/v2/ugcPosts` personal) + `scripts/discovery/stage8_image_generator.py` (Google Image directo) | aprobar el criterio de DISABLE y el PR | **diseñar** el guardrail fail-closed (este plan §5); un PR de código futuro tras GO | DISABLE real / edición de esos scripts en este plan; mezclarlo con rotaciones | Claude Code (PR futuro) | S–M | ADR-009-A, ADR-006 |

## 3. Orden recomendado de GOs

1. **GO-B2** (urgente): rotar/eliminar perfil Vertex — es una credencial cloud live re-emitida por un bug que se dispara con un comando de diagnóstico rutinario. David rota en GCP; el fix del guard/CLI va como PR aparte después.
2. **GO-B1** (urgente): rotar password de la VM y migrar a vault; borrar del script. David.
3. **GO-B3** (higiene): revisar `env.rick` y `token-map.csv`, mover/rotar lo que aplique. David. Se agrupa con B1/B2 porque comparte el criterio de rotación, pero sin fuga demostrada por git no bloquea.
4. **GO-B4** (contención): aprobar el diseño del guardrail y, luego, el PR de código. Independiente de las rotaciones; **no** entra en la misma ventana que B1–B3.

Regla: cada GO es por ítem. Ningún GO agrupa una rotación (B1/B2/B3) con un cambio de código (B4).

## 4. Runbooks humanos (SIN valores) — B1, B2, B3

### B1 — Password de la VM OpenClaw en `vm_script.ps1`
- **Evidencia**: `05-…:120` (`vm_script.ps1`, propósito Invoke-Command a la VM Hyper-V "OpenClaw", última mod. 2026-02-19, `SECURITY_RISK`, valor NO reproducido); `05-…:129,143,147` (recomendación de rotar + migrar a vault). Confirmado read-only: **no está en git** (`git ls-files` vacío para ese patrón).
- **Riesgo si no se hace**: credencial de administración de la VM en texto plano ~5 meses, copiable por accidente en bundles/backups/pantalla; permite Invoke-Command a la VM si se filtra.
- **Procedimiento (David, sin exponer valores)**:
  1. Cambiar el password de la cuenta que usa la VM "OpenClaw" (rotación real; invalida el valor viejo).
  2. Guardar el nuevo secreto en Credential Manager / DPAPI (no en el script).
  3. Editar `vm_script.ps1` para leer la credencial del vault (p. ej. `Get-StoredCredential`), sin literal.
  4. Borrar cualquier copia del valor viejo (script, historial de shell, notas).
- **Verificación post-cambio**: el script sigue autenticando contra la VM usando el vault; `Select-String -Path vm_script.ps1 -Pattern 'ConvertTo-SecureString.*-AsPlainText|password\s*='` no devuelve literales. (David corre esto; el agente no abre el archivo.)
- **Rollback**: si el vault falla, restaurar acceso con una credencial temporal desde Credential Manager; **no** volver a hardcodear. El password viejo ya no sirve (rotado), así que el rollback nunca reintroduce el secreto expuesto.
- **Destinatario**: David (rotación + edición) · opcional Copilot Windows (plantilla de lectura-de-vault, sin valores).
- **Tamaño**: S. **Depende de**: —. **Gate**: `GO_B1_ROTATE_VM_CRED`.

### B2 — Fingerprint parcial Google Vertex emitido por `openclaw models status`
- **Evidencia**: `06-…:79` (el CLI emitió un fingerprint parcialmente enmascarado de una credencial Vertex; omitido, `SECURITY_RISK`, rotar fuera del mandato read-only); `06-…:305,311,486` (perfil `google-vertex` presente en el auth store, sin smoke; rotación recomendada según `secret-output-guard`). El operador ya usó `secret-output-guard` con `sed` de redacción (`06-…:77`).
- **Riesgo si no se hace**: `openclaw models status` es un comando de diagnóstico habitual; cada corrida re-emite el fingerprint a stdout/logs/capturas → fuga incremental de una credencial cloud live que además hoy **no rutea tráfico** (perfil huérfano, solo-definido), así que rotarla/eliminarla no rompe runtime.
- **Procedimiento (David, sin exponer valores)**:
  1. En Google Cloud, rotar o **eliminar** la API key / service account del perfil Vertex (dado que no se usa, eliminar es preferible).
  2. Retirar el perfil del auth store del gateway con el comando `openclaw` de gestión de perfiles (David/operador con GO), no editando el store a mano.
  3. Registrar el bug del CLI (fingerprint en salida) para el fix de `secret-output-guard` (B2-agente, PR aparte).
- **Verificación post-cambio**: `openclaw models status` **a través del guard** ya no muestra el perfil Vertex (o lo muestra sin fingerprint); el perfil no aparece en `models status`. (Siempre con `secret-output-guard`; nunca crudo.)
- **Rollback**: si algún flujo dependía de Vertex (no evidenciado — perfil sin smoke), re-crear una credencial **nueva** en GCP y re-registrar el perfil; nunca restaurar la credencial rotada.
- **Destinatario**: David (rota/elimina en GCP + retira perfil) · Claude Code (fix del guard/CLI como PR futuro).
- **Tamaño**: S. **Depende de**: —. **Gate**: `GO_B2_ROTATE_VERTEX_PROFILE`.

### B3 — `env.rick` local + `token-map.csv`
- **Evidencia**: inventario §7 S-7 (`token-map.csv` en `_audit-2026-07`, no abierto, posible sensible) y S-8 (`env.rick`, 45 claves en texto plano, local, no-git); `05-…:121,138`. Confirmado read-only: `env.rick` **existe en la raíz pero está gitignored** (`git check-ignore env.rick` → positivo; `git ls-files` no lo lista); `token-map.csv` **no está en git**.
- **Riesgo si no se hace**: secretos en texto plano en el filesystem local (segundo caso tras B1) — copiables por accidente; `token-map.csv` de contenido desconocido podría mapear tokens.
- **Procedimiento (David, sin exponer valores)**:
  1. Revisar `env.rick`: confirmar qué claves siguen vigentes; mover el archivo fuera del árbol del repo (a `~/.config/umbral/` o a un vault) o eliminarlo si el runtime ya no lo usa; rotar cualquier clave que haya podido quedar expuesta.
  2. Abrir `token-map.csv` (solo David), decidir si contiene material sensible; si sí, rotar y borrar; si no, archivar. No ingerirlo en ningún flujo automatizado.
- **Verificación post-cambio**: `env.rick` ya no está en el árbol del repo (`Test-Path .\env.rick` → false) o queda solo fuera del repo; `git status` limpio; el worker/gateway siguen arrancando (su env real vive en `~/.config/openclaw/env`, no en `env.rick` — nombres verificados en `06-…:366-367`).
- **Rollback**: si algún proceso local dependía de `env.rick`, recrear un env mínimo **fuera** del repo con claves rotadas.
- **Destinatario**: David. **Tamaño**: S. **Depende de**: comparte criterio de rotación con B1/B2. **Gate**: `GO_B3_RELOCATE_LOCAL_SECRETS`.

> En B1/B2/B3 el agente **no** abre, mueve ni imprime ningún archivo de secretos. Lo verificable por el agente sin leer secretos (p. ej. `git check-ignore`, presencia de un nombre de entrada en un vault) puede prepararse como checklist; la ejecución es de David.

## 5. Diseño del paquete agente — B4 (solo alcance, sin DISABLE real)

- **Superficies (verificadas, existen)**:
  - `scripts/discovery/stage9c_linkedin_publish.py` — publica a `POST /v2/ugcPosts` (`LINKEDIN_UGC_PATH`), identidad `urn:li:person` (`AUTHOR_URN_PLACEHOLDER = "urn:li:person:__TODO_RESOLVE_AT_PUBLISH__"`). Es un CLI manual (`argparse`, `--dry-run`, `--max-posts` default 1, `--author-urn`/`LINKEDIN_AUTHOR_URN`). **Sin caller** en `scripts/`, `config/`, `.github/`.
  - `scripts/discovery/stage8_image_generator.py` — usa Google Image directo; ADR-006 declara ese proveedor superado por Magnific.
- **Contrato que se viola**: ADR-009-A (`docs/adr/ADR-009-linkedin-company-api.md`) exige LinkedIn **Company Page** vía `/rest/posts` con el handler `editorial.publish.linkedin_org` (que no existe). Además `worker/tasks/editorial_publish.py:20-21` afirma "LinkedIn/X are never auto-published" — contradicción con la existencia de un publisher personal ejecutable.
- **Criterio de DISABLE (a implementar en el PR futuro, fail-closed)**:
  1. **stage9c**: introducir un guard que rechace la publicación salvo que se cumplan **todas**: (a) endpoint = `/rest/posts` (Company), (b) autor = `urn:li:organization:*` resuelto (no placeholder, no `urn:li:person`), (c) un flag explícito de habilitación (p. ej. `RICK_LINKEDIN_ORG_PUBLISH_ENABLED`, default off). Mientras no exista `editorial.publish.linkedin_org`, el guard **siempre** bloquea el POST real y deja `--dry-run` como único camino. Así una invocación manual accidental no publica bajo identidad personal.
  2. **stage8**: guard que impida la llamada directa a Google Image; exigir el proveedor vigente (Magnific) según ADR-006, o degradar a no-op documentado hasta re-cablear.
  3. **Coherencia**: alinear el comentario de `editorial_publish.py:20-21` con el estado real y referenciar ADR-009-A/ADR-006 en ambos scripts.
- **Archivos candidatos del PR**: `scripts/discovery/stage9c_linkedin_publish.py`, `scripts/discovery/stage8_image_generator.py`, un test que pruebe "sin flag/identidad org → no hay POST real" (patrón `urlopen`/`post_ugc` mockeado, como en `editorial_publish` tests), y una nota en el/los ADR.
- **Qué NO hace el PR**: no publica, no toca tokens LinkedIn, no cablea el handler org (eso es trabajo aparte). Solo **contiene** la vía personal/legacy.
- **Tamaño**: S–M. **Depende de**: ADR-009-A, ADR-006. **Gate**: `GO_B4_DISABLE_STAGE9C_STAGE8`.

## 6. Anti-recomendaciones

- NO agrupar B4 (código) con B1/B2/B3 (rotaciones) en un mismo GO ni PR.
- NO ejecutar `openclaw models status` sin `secret-output-guard` mientras B2 esté abierto.
- NO abrir, mover ni imprimir `vm_script.ps1`, `env.rick` ni `token-map.csv` desde ningún agente; son de David.
- NO editar el auth store del gateway a mano ni tocar los checkouts dirty `/tmp/*wt*` (siguen `DO_NOT_TOUCH`, `06-…:445-451`).
- NO restaurar jamás un secreto rotado en el rollback; el rollback usa credencial **nueva**.
- NO ampliar a A6, n8n local, higiene de ramas ni Tanda C/D/E en esta tanda.
- NO asumir que un perfil "presente en el auth store" está en uso: Vertex no tiene smoke (`06-…:494`) — eliminarlo es de bajo riesgo runtime.

## 7. Lista de GOs listos para orquestar

| Gate | Qué autoriza | Destinatario | Naturaleza |
|---|---|---|---|
| `GO_B2_ROTATE_VERTEX_PROFILE` | David rota/elimina la credencial Vertex en GCP y retira el perfil del gateway | David | rotación (humano) |
| `GO_B1_ROTATE_VM_CRED` | David rota el password de la VM, migra a vault, borra del script | David | rotación (humano) |
| `GO_B3_RELOCATE_LOCAL_SECRETS` | David revisa/mueve `env.rick` y `token-map.csv`, rota lo expuesto | David | higiene (humano) |
| `GO_B2_GUARD_FIX` | Claude Code abre PR que endurece `secret-output-guard`/CLI contra fingerprints en salida | Claude Code | código (PR futuro) |
| `GO_B4_DISABLE_STAGE9C_STAGE8` | Claude Code abre PR con el guardrail fail-closed de stage9c/stage8 + test + nota ADR | Claude Code | código (PR futuro) |

## 8. UNKNOWNs (requieren GO de verificación read-only)

- Contenido de `token-map.csv` — no abierto por diseño; solo David decide (S-7).
- Si algún flujo local depende de `env.rick` hoy (el runtime canónico usa `~/.config/openclaw/env`; `env.rick` parece residual, sin confirmar).
- Versión desplegada del gateway vs CVEs OpenClaw 2026 (fuentes secundarias en Perplexity) — fuera de B; se verifica antes de cualquier exposición, no ahora.

---
**Gate**: `PKG_TANDA_B_PLAN_READY`. No implementa, no despliega, no rota, no edita runtime, no mergea.
