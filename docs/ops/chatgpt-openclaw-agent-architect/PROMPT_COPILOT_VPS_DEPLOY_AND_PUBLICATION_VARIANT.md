# Megaprompt para Copilot/VPS — Desplegar `rick-communication-director` y generar variante CAND-003

Destinatario: GitHub Copilot trabajando en la VPS de Rick/OpenClaw.

Objetivo: desplegar o dejar invocable `rick-communication-director` en modo `read-only dry-run`, corregir los gaps de configuracion detectados, ejecutar smoke tests y generar una nueva version de sugerencia editorial para CAND-003 sin publicar ni tocar gates.

```text
Actua como operador tecnico Copilot/VPS para `umbral-agent-stack`.

Objetivo:
Desplegar y verificar el agente OpenClaw `rick-communication-director` en modo read-only/dry-run, y luego usarlo para generar una nueva version de sugerencia de publicacion para CAND-003, corrigiendo el problema de tono detectado por David.

Branch:
Mantener el branch actual `codex/cand-002-source-driven-flow` o el branch del PR #267 si la VPS ya esta en ese branch. No cambiar a `main`.

Contexto:
David rechazo la redaccion actual de CAND-003 aunque aprobo la premisa. El problema principal no fue la tesis, sino la voz: suena generica, de checklist y con terminos poco naturales como `escalación`. Ya existe un agente disenado llamado `rick-communication-director`, pero hay que verificar que este realmente desplegado, endurecer su configuracion y probarlo en modo seguro.

Fuentes obligatorias a leer antes de tocar nada:
- `AGENTS.md`
- `.agents/PROTOCOL.md`
- `.agents/board.md`
- `openclaw/workspace-agent-overrides/rick-communication-director/ROLE.md`
- `openclaw/workspace-templates/skills/director-comunicacion-umbral/SKILL.md`
- `openclaw/workspace-templates/AGENTS.md`
- `scripts/sync_openclaw_workspace_governance.py`
- `docs/openclaw-config-reference-2026-03.json5`
- `docs/03-setup-vps-openclaw.md`
- `docs/68-editorial-phase-1-manual.md`
- `docs/ops/cand-003-*`
- `docs/ops/cand-002-*`
- `docs/ops/editorial-source-attribution-policy.md`
- `docs/ops/rick-editorial-candidate-payload-template.md`

Restricciones fuertes:
- No publicar.
- No marcar `aprobado_contenido`.
- No marcar `autorizar_publicacion`.
- No cambiar `gate_invalidado` salvo que David lo pida explicitamente.
- No tocar CAND-002.
- No editar Notion en esta tarea, salvo lectura o si David dio autorizacion explicita en esta misma tarea.
- No activar runtime de publicacion.
- No cambiar secretos.
- No imprimir tokens.
- No usar Notion AI.
- No convertir el agente en write-enabled.
- No hacer merge.

Parte A - Diagnostico previo:
1. Verificar estado local:
   - `pwd`
   - `git branch --show-current`
   - `git status --short`
   - `git log --oneline -5`
2. Confirmar que estas en el repo correcto de VPS, normalmente `/home/rick/umbral-agent-stack`.
3. Confirmar si `rick-communication-director` existe como:
   - ROLE.md repo-side;
   - skill repo-side;
   - entry en config reference;
   - entry en config viva de OpenClaw;
   - agente invocable por CLI.
4. Documentar el estado real. No asumir deploy si solo existe en docs.

Parte B - Corregir gaps repo-side antes del deploy:
Aplicar estos ajustes si siguen pendientes:

1. `docs/openclaw-config-reference-2026-03.json5`
   - Asegurar que `rick-communication-director` tenga politica explicita de read-only/dry-run.
   - Si el formato real de OpenClaw soporta tools allow/deny, sandbox o permisos por agente, usar los campos reales existentes en el repo/config.
   - Si no hay sintaxis confirmada, NO inventar campos. Documentar el gap y dejarlo como pendiente antes de tocar config viva.

2. `openclaw/workspace-agent-overrides/rick-communication-director/ROLE.md`
   - Eliminar texto obsoleto que diga que el rol es solo `design-only` si ya se esta desplegando como dry-run.
   - Mantener claramente: fase `read-only dry-run`, sin publicacion, sin gates, sin writes.
   - Asegurar que `escalacion` y `escalación` esten prohibidas en copy publico salvo justificacion tecnica excepcional.

3. `openclaw/workspace-templates/skills/director-comunicacion-umbral/SKILL.md`
   - Cambiar cualquier frase que diga `No activar runtime` por una formulacion correcta:
     `No activar publicacion ni acciones write; este skill puede operar en agente dry-run si la config OpenClaw lo permite`.
   - Asegurar que la salida del agente incluya:
     - diagnostico de tono;
     - frases que David probablemente no diria;
     - variantes controladas;
     - score editorial;
     - handoff a QA si cambia claim o atribucion.

4. `openclaw/workspace-templates/AGENTS.md`
   - Corregir conteos obsoletos como `Rick opera como 3 runtime agents` si ya hay mas agentes listados.
   - Diferenciar agentes activos, design-only y dry-run.

5. `docs/68-editorial-phase-1-manual.md`
   - Aclarar ruta temporal mientras `rick-editorial` siga design-only:
     `rick-orchestrator` o David pueden invocar directamente `rick-communication-director` para curaduria narrativa dry-run, y luego enviar a `rick-qa`.
   - No presentar `rick-editorial -> rick-communication-director` como unica ruta si `rick-editorial` no esta runtime.

6. `docs/03-setup-vps-openclaw.md`
   - Agregar smoke test especifico para `rick-communication-director`.

Parte C - Validacion repo-side:
Ejecutar:
- `python3 scripts/validate_skills.py`
- `python3 -m pytest tests/test_skills_validation.py tests/test_sync_openclaw_workspace_governance.py -q`
- `python3 scripts/sync_openclaw_workspace_governance.py --dry-run`
- `git diff --check`

Si algun test falla, corregirlo antes de continuar. Si el fallo no esta relacionado, documentarlo y no ocultarlo.

Parte D - Sync a workspace OpenClaw:
1. Ejecutar sync en modo real solo despues del dry-run limpio:
   - `python3 scripts/sync_openclaw_workspace_governance.py --execute`
2. Verificar que se copio:
   - `ROLE.md` de `rick-communication-director`;
   - skill `director-comunicacion-umbral`;
   - `AGENTS.md` actualizado.

Parte E - Config viva OpenClaw:
1. Localizar la config viva real de OpenClaw, probablemente `~/.openclaw/openclaw.json` o la ruta documentada en VPS.
2. Hacer backup antes de cualquier cambio:
   - `cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak.$(date +%Y%m%d-%H%M%S)`
3. Comparar con `docs/openclaw-config-reference-2026-03.json5`.
4. Si la sintaxis real confirma como registrar agentes:
   - agregar o actualizar `rick-communication-director`;
   - apuntar al workspace compartido correcto;
   - usar el mismo modelo recomendado por el repo salvo que haya restriccion de capacidad;
   - aplicar read-only/dry-run si la config soporta tools/sandbox por agente.
5. Si la sintaxis real no confirma tools/sandbox por agente:
   - registrar solo si el agente no tiene herramientas write disponibles;
   - si existe riesgo de write, detener y pedir decision a David.
6. No hardcodear secretos ni imprimir env vars.

Parte F - Reinicio y smoke test:
1. Reiniciar OpenClaw gateway usando el mecanismo real documentado en VPS.
2. Ejecutar:
   - `openclaw status --all`
   - `openclaw agent --agent rick-communication-director --message "Responde exactamente: OK-COMMUNICATION-DIRECTOR"`
3. El smoke pasa solo si devuelve exactamente `OK-COMMUNICATION-DIRECTOR` o una respuesta equivalente sin intentar escribir, publicar ni pedir permisos extra.
4. Si existe comando de seguridad, ejecutar:
   - `openclaw security audit --deep`
   y reportar hallazgos.

Parte G - Generar nueva variante CAND-003:
Usar `rick-communication-director` para generar una nueva version de sugerencia editorial. Debe ser dry-run y evidencia repo-side.

Prompt para el agente:

"""
Actua como rick-communication-director.

Objetivo:
Generar una nueva version de sugerencia editorial para CAND-003, manteniendo la premisa aprobada por David pero corrigiendo tono, naturalidad y lenguaje.

Contexto:
David aprobo la premisa "criterio antes que automatizacion", pero rechazo la redaccion actual. El copy suena generico, demasiado validado por checklist y usa terminos poco naturales como `escalación`.

Fuentes:
- docs/ops/cand-003-payload.md
- docs/ops/cand-003-source-driven-flow.md
- docs/ops/cand-003-rick-qa-attribution-result.md
- docs/ops/cand-003-rick-qa-voice-result.md
- docs/ops/cand-003-rick-qa-result.md
- docs/ops/editorial-source-attribution-policy.md
- Notion CAND-003 solo si esta accesible en lectura.
- Guia Editorial y Voz de Marca solo si esta accesible en lectura. Si no esta accesible, declarar que trabajas contra resumen autorizado.

Restricciones:
- No cambiar la premisa sin proponerlo como alternativa.
- No cambiar fuentes.
- No inventar datos.
- No citar fuentes nuevas.
- No publicar.
- No tocar gates.
- No editar Notion.
- No usar `escalación` ni `escalacion` en copy publico.
- Mantener atribucion y trazabilidad.

Entrega:
1. Diagnostico breve de por que la version anterior falla en voz.
2. Lista de frases o palabras que David probablemente no diria.
3. Copy LinkedIn V2, una sola version recomendada.
4. Copy X V2, una sola version recomendada.
5. Score editorial:
   - voz David;
   - naturalidad;
   - densidad AEC/BIM;
   - ausencia de slop;
   - claridad de tesis;
   - riesgo de claim.
6. Riesgos de atribucion o claim.
7. Handoff recomendado para rick-qa.
8. Estado: dry-run, no publicado, gates intactos.
"""

Guardar la salida en:
- `docs/ops/cand-003-communication-director-v2.md`

Formato del archivo:
- fecha/hora;
- agente invocado;
- modelo si OpenClaw lo reporta;
- fuente de voz usada: Guia viva o resumen autorizado;
- prompt usado o resumen del prompt;
- resultado completo;
- verificacion de que no hubo publicacion ni gates.

Parte H - Commit y push:
1. Revisar `git status --short`.
2. Asegurar que no se agregaron secretos ni logs con tokens.
3. Ejecutar grep de seguridad sobre cambios:
   - `git diff --cached` antes del commit, si ya hay staged;
   - buscar `NOTION_API_KEY`, `OPENAI_API_KEY`, `AZURE_OPENAI_API_KEY`, `Bearer`, `secret`, `password`.
4. Commit sugerido:
   - `docs: deploy communication director dry-run and add CAND-003 v2`
5. Push al branch actual.
6. No abrir PR nuevo si ya existe PR #267; comentar el PR solo si `gh` esta autenticado y sin exponer secretos.

Entrega final para David:
- estado del deploy: hecho / bloqueado / parcial;
- page id o URL de CAND-003 si se leyo Notion;
- confirmacion de no publicacion;
- confirmacion de gates intactos;
- comandos ejecutados;
- tests ejecutados y resultado;
- ruta del archivo `docs/ops/cand-003-communication-director-v2.md`;
- resumen de la nueva variante;
- riesgos pendientes.
```
