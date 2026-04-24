# Megaprompt para Copilot/VPS

```text
Contexto:
Estas trabajando en el repo `umbral-agent-stack` en la VPS. El branch debe mantenerse como branch draft: `codex/cand-002-source-driven-flow` o el branch actual si ya estas en el PR correcto. No hagas push directo a `main`. No hagas merge. No toques secretos. No publiques contenido. No marques gates humanos.

Objetivo:
Endurecer el agente OpenClaw `rick-communication-director` para que su estado `runtime-registered / read-only / dry-run` sea coherente y verificable. Debe poder auditar copy editorial y proponer variantes, pero no debe escribir en Notion, no debe modificar repos, no debe publicar, no debe activar routing autonomo, no debe tocar gates y no debe usar herramientas de VM/browser/gui.

Trabajo a realizar:

1. Lee primero:
   - `AGENTS.md`
   - `.agents/PROTOCOL.md`
   - `.agents/board.md`
   - `openclaw/workspace-agent-overrides/rick-communication-director/ROLE.md`
   - `openclaw/workspace-agent-overrides/rick-communication-director/HEARTBEAT.md`
   - `openclaw/workspace-templates/skills/director-comunicacion-umbral/SKILL.md`
   - `openclaw/workspace-templates/AGENTS.md`
   - `openclaw/workspace-templates/skills/openclaw-gateway/SKILL.md`
   - `docs/openclaw-config-reference-2026-03.json5`
   - `docs/03-setup-vps-openclaw.md`
   - `docs/ops/rick-communication-director-agent.md`
   - `tests/test_sync_openclaw_workspace_governance.py`

2. Corrige inconsistencias de estado:
   - En `ROLE.md`, elimina o actualiza cualquier texto residual que diga `design-only` si contradice `runtime-registered / read-only / dry-run`.
   - En `SKILL.md`, cambia `No activar runtime` por una regla mas precisa: `No crear routing autonomo, cron, publicacion, writes ni gate mutation`.
   - En `docs/ops/rick-communication-director-agent.md`, aseguralo como `runtime-registered / read-only / dry-run`, no como design-only.

3. Agrega una seccion `Tools and permissions` en `openclaw/workspace-agent-overrides/rick-communication-director/ROLE.md`.
   Debe incluir:
   - nota de que el ROLE.md es declarativo y que el enforcement real vive en `openclaw.json`;
   - recommended tools solo de lectura/sintesis, por ejemplo:
     - `notion.read_page`
     - `notion.read_database`
     - `notion.search_databases`
     - `llm.generate`
     - `research.web` solo para verificar contexto, no para publicar ni discovery primario
     - lectura de archivos del repo si la tool existe en OpenClaw
   - tools a evitar/prohibir:
     - `notion.upsert_*`
     - `notion.create_*`
     - `notion.update_*`
     - `notion.add_comment` salvo que David lo autorice explicitamente
     - `github.create_branch`
     - `github.commit_and_push`
     - `github.open_pr`
     - `windows.*`
     - `browser.*`
     - `gui.*`
     - `client.*`
     - cualquier tool de publicacion externa
   - excepciones: solo David puede autorizar una excepcion puntual, y aun asi nunca publicacion ni gates.

4. Endurece la referencia de `openclaw.json`.
   En `docs/openclaw-config-reference-2026-03.json5`, actualiza la entrada de `rick-communication-director` para incluir politica de tools/sandbox si el formato es compatible con la documentacion de `openclaw-gateway`.
   Usa la sintaxis real documentada en el repo. No inventes campos.
   Si no estas seguro de la sintaxis exacta, haz dos cosas:
   - deja el ejemplo minimo seguro como comentario/documentacion;
   - documenta explicitamente que la lista de tools debe validarse con `openclaw security audit --deep` antes de aplicarse en VPS.

   Objetivo de politica:
   - permitir solo lectura y sintesis;
   - negar Notion writes, GitHub writes, VM/browser/gui, client/admin y publicacion.

5. Actualiza blacklist y reglas de lenguaje:
   - En `ROLE.md`, `SKILL.md`, `rick-editorial/ROLE.md` y `rick-qa/ROLE.md`, bloquear tanto `escalacion` como `escalación` cuando aparezcan como sustantivo en copy publico.
   - Mantener reemplazos: `cuando escalar`, `a quien derivarlo`, `cuando levantar el problema`, `cuando subirlo de nivel`.

6. Ajusta el flujo mientras `rick-editorial` siga design-only:
   - En `openclaw/workspace-templates/AGENTS.md`, aclarar que el flujo ideal es:
     `orchestrator -> editorial -> communication-director -> qa -> orchestrator -> David`
   - Pero mientras `rick-editorial` no este activo, se permite handoff directo:
     `orchestrator/qa -> communication-director -> qa -> David`
   - Corregir la frase desactualizada `Rick opera como 3 runtime agents` para reflejar que hay agentes activos, design-only y read-only/dry-run.

7. Actualiza el runbook de VPS:
   En `docs/03-setup-vps-openclaw.md`, agregar comandos de validacion luego de registrar el agente:
   - `python3 scripts/sync_openclaw_workspace_governance.py --dry-run`
   - `python3 scripts/sync_openclaw_workspace_governance.py --execute`
   - `systemctl --user restart openclaw-gateway`
   - `/home/rick/.npm-global/bin/openclaw status --all`
   - `/home/rick/.npm-global/bin/openclaw agent --agent rick-communication-director -m 'Responde solo OK-COMMUNICATION-DIRECTOR'`
   - recomendar `openclaw security audit --deep` despues de cambios en tools/sandbox.

8. Tests y validaciones obligatorias:
   Ejecuta:
   - `python3 scripts/validate_skills.py`
   - `python3 -m pytest tests/test_skills_validation.py tests/test_sync_openclaw_workspace_governance.py -q`
   - `python3 scripts/sync_openclaw_workspace_governance.py --dry-run`
   - `git diff --check`

   Si estas en entorno Windows local, usa `python` en vez de `python3`. Si estas en VPS Linux, usa `python3`.

9. Seguridad:
   - No edites `.env`.
   - No imprimas tokens.
   - No cambies `~/.openclaw/openclaw.json` vivo salvo que David lo haya pedido explicitamente en esta sesion.
   - Si David pidio aplicar en vivo, primero haz backup de `~/.openclaw/openclaw.json`, aplica cambio minimo, corre dry-run/smoke, y reporta rollback exacto.
   - No actives routing autonomo ni cron para este agente.

10. Entrega final:
   Reporta:
   - branch;
   - archivos modificados;
   - resumen de cambios;
   - validaciones corridas y resultado;
   - si hubo o no cambios en runtime vivo;
   - comandos exactos para aplicar en VPS si quedaron solo documentados;
   - riesgos residuales.

Criterios de aceptacion:
- `rick-communication-director` queda coherente como runtime-registered / read-only / dry-run.
- La politica de tools/sandbox esta documentada y no contradice el ROLE.md.
- `escalacion` y `escalación` quedan bloqueadas como sustantivo en copy publico.
- El flujo directo temporal queda documentado mientras `rick-editorial` siga design-only.
- El runbook incluye smoke test del agente.
- Todas las validaciones indicadas pasan.
- No hay publicacion, no hay gates humanos, no hay writes en Notion, no hay runtime routing autonomo.
```
