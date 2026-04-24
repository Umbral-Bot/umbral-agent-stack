# Acceptance Checklist

## Para aceptar el GPT en ChatGPT

- [ ] Las instrucciones principales son las de `INSTRUCTIONS.md`.
- [ ] `SKILL.md` fue subido como skill o knowledge del GPT.
- [ ] `CREATE_SKILL_INSTRUCTIONS.md` fue usado para configurar el GPT sin permisos write.
- [ ] El GPT tiene acceso de lectura a GitHub o se cargaron los documentos repo relevantes.
- [ ] El GPT tiene acceso de lectura a Notion o se cargo export de la Guia Editorial y Voz de Marca.
- [ ] El GPT tiene acceso de lectura a Drive o se cargaron las carpetas transversales relevantes.
- [ ] El GPT no tiene permisos de escritura por defecto.
- [ ] El GPT distingue evidencia, inferencia e hipotesis.
- [ ] El GPT no afirma runtime activo sin evidencia.
- [ ] El GPT produce prompts ejecutables para Codex/Copilot en vez de pedir operar produccion.

## Para aceptar una auditoria de agente OpenClaw

- [ ] Identifica si el agente es GPT, skill, ROLE.md, workspace, runtime o solo plan.
- [ ] Revisa scope, out_of_scope, permisos, handoffs y failure modes.
- [ ] Revisa tools permitidas y prohibidas.
- [ ] Revisa gates humanos.
- [ ] Revisa evidencia requerida.
- [ ] Detecta contradicciones entre docs, repo y runtime.
- [ ] Propone cambios concretos y testeables.
- [ ] Incluye prompt para implementador tecnico.

## Para aceptar el caso `rick-communication-director`

- [ ] No puede publicar.
- [ ] No puede marcar `aprobado_contenido`.
- [ ] No puede marcar `autorizar_publicacion`.
- [ ] No puede escribir en Notion.
- [ ] No puede modificar repos.
- [ ] No tiene routing autonomo ni cron.
- [ ] Bloquea `escalacion` y `escalación` en copy publico.
- [ ] Distingue `voz David` de `checklist QA`.
- [ ] Devuelve a QA si cambia claims, fuentes o atribucion.

## Para aceptar el deploy dry-run en VPS

- [ ] Copilot/VPS uso `PROMPT_COPILOT_VPS_DEPLOY_AND_PUBLICATION_VARIANT.md`.
- [ ] `rick-communication-director` responde a smoke test.
- [ ] El agente queda read-only/dry-run.
- [ ] No hubo publicacion.
- [ ] No hubo cambios en gates.
- [ ] No hubo writes en Notion.
- [ ] Se genero `docs/ops/cand-003-communication-director-v2.md`.
- [ ] La nueva variante elimina `escalacion` y `escalación` del copy publico.
