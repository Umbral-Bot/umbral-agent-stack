# Arquitecto de Agentes OpenClaw — ChatGPT Upload Pack

Este paquete contiene los archivos para crear en ChatGPT un agente consultivo llamado
`Arquitecto de Agentes OpenClaw`.

## Uso recomendado

1. Crear un GPT nuevo en ChatGPT.
2. Pegar el contenido de `INSTRUCTIONS.md` como instrucciones principales.
3. Subir como conocimiento o skill el archivo `SKILL.md`.
4. Subir como conocimiento el resto de archivos de esta carpeta.
5. Si el GPT tiene conectores, habilitar lectura para GitHub, Notion y Google Drive segun `KNOWLEDGE_MANIFEST.md`.
6. Usar `PROMPT_FIRST_AUDIT.md` como primer encargo para auditar `rick-communication-director`.

## Archivos

- `INSTRUCTIONS.md`: instrucciones principales del GPT.
- `SKILL.md`: skill formal del Arquitecto de Agentes OpenClaw.
- `CREATE_SKILL_INSTRUCTIONS.md`: pasos para crear/configurar el GPT en ChatGPT.
- `KNOWLEDGE_MANIFEST.md`: fuentes que debe leer o recibir como knowledge.
- `PROMPT_FIRST_AUDIT.md`: primer prompt recomendado para validar el Director de Comunicacion.
- `PROMPT_COPILOT_VPS_IMPLEMENTATION.md`: megaprompt general para Copilot/VPS.
- `PROMPT_COPILOT_VPS_DEPLOY_AND_PUBLICATION_VARIANT.md`: megaprompt para desplegar `rick-communication-director` en VPS y generar CAND-003 V2 sin publicar.
- `ACCEPTANCE_CHECKLIST.md`: criterios para aceptar el GPT y sus auditorias.

## Regla clave

Este GPT no opera produccion. Audita, disena, corrige contratos y prepara handoffs.
Codex/Copilot/VPS aplican cambios tecnicos solo cuando David lo autoriza.
