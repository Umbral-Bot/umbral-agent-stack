# P1.2 — RESCUE_SELECTIVE de la fila 2 (export-vscode-config.ps1) — 2026-08-06

> **Pack:** PKG-UAS-P1-2-KEEP2-RESCUE-PS1 · rama `claude/pkg-uas-p1-2-keep2-rescue-ps1-20260806` · base `e5a0f189`
> **GO de David:** "ok, go con lo siguiente" tras KEEP1 DONE — ejecutar fila 2 del brief
> [uas-p1-2-orphan-keep3-2026-08-06.md](uas-p1-2-orphan-keep3-2026-08-06.md): RESCUE_SELECTIVE
> solo del `.ps1`. Fila 3 (`rick/stage7_5-multiformat`) FUERA de este pack.

---

## 1. Fuente

- Rama: `origin/rescue/coordinador-dirty-2026-07-13` @ `16219f25` — verificada viva en el SHA
  esperado.
- Método: `git checkout origin/rescue/coordinador-dirty-2026-07-13 -- scripts/export-vscode-config.ps1`
  (solo ese path; el commit de origen también toca `docs/ops/editorial-publicaciones-human-review-
  contract.md`, explícitamente prohibido en este pack por su solapamiento ambiguo con el estado
  actual de `main`).

## 2. Archivo traído (exactamente 1)

| Archivo | Líneas | Qué hace |
|---|---|---|
| `scripts/export-vscode-config.ps1` | 251 | Utilidad de desarrollador: exporta settings/keybindings/prompts/skills/agentes/extensiones de VS Code + Copilot + Claude + `.agents` a un ZIP, para replicar el setup en otra máquina. Genera también `install-extensions.ps1` y un `RESTORE-README.md` dentro del ZIP |

## 3. Revisión de secretos/PII (antes de commitear)

Leído el script completo (251 líneas). **Sin hallazgos.**

- No hay tokens, API keys, passwords ni URLs con credenciales embebidas.
- El propio script **excluye explícitamente** credenciales de lo que exporta: *"Las credenciales
  (.claude/.credentials.json, tokens, .env) NO se exportan. Configurá las credenciales manualmente
  en la notebook."* (línea 229-230 del script).
- Usa `$env:COMPUTERNAME` y `$env:USERPROFILE` solo como referencias de entorno en tiempo de
  ejecución (para el nombre del ZIP y las rutas de copia), no como valores literales en el
  archivo.
- No se necesitó redacción — se trae el contenido tal cual, sin cambios.

## 4. Confirmación de exclusión

```
git diff --stat origin/main
→ scripts/export-vscode-config.ps1 | 251 +++++++++++++++++++++++++++++++++++++++
  1 file changed, 251 insertions(+)

git diff origin/main -- docs/ops/editorial-publicaciones-human-review-contract.md
→ (vacío — diff 0, no tocado)
```

## 5. Rama fuente `rescue/coordinador-dirty-2026-07-13`

**No se borró en este pack.** Su otro archivo (`editorial-publicaciones-human-review-contract.md`)
sigue sin resolver — la rama queda viva hasta que se decida qué hacer con ese doc o se autorice
el delete a pesar de dejarlo sin rescatar. Propuesto para `TU TURNO`.

## 6. Prohibido (respetado)

- Cero touch a `docs/ops/editorial-publicaciones-human-review-contract.md` (confirmado diff 0).
- Cero touch a fila 3 (`rick/stage7_5-multiformat`).
- Cero delete de la rama fuente en este pack.
- Cero self-merge.
