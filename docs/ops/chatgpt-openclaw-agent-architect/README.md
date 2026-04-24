# Arquitecto de Agentes OpenClaw — ChatGPT Upload Pack

Este paquete contiene los archivos para crear en ChatGPT un agente consultivo llamado
`Arquitecto de Agentes OpenClaw`.

## Uso recomendado

1. Crear un GPT nuevo en ChatGPT.
2. Pegar el contenido de `INSTRUCTIONS.md` como instrucciones principales.
3. Subir como conocimiento los archivos de esta carpeta.
4. Si el GPT tiene conectores, habilitar lectura para GitHub, Notion y Google Drive segun `KNOWLEDGE_MANIFEST.md`.
5. Usar `PROMPT_FIRST_AUDIT.md` como primer encargo para auditar `rick-communication-director`.

## Archivos

- `INSTRUCTIONS.md`: instrucciones principales del GPT.
- `KNOWLEDGE_MANIFEST.md`: fuentes que debe leer o recibir como knowledge.
- `PROMPT_FIRST_AUDIT.md`: primer prompt recomendado para validar el Director de Comunicacion.
- `PROMPT_COPILOT_VPS_IMPLEMENTATION.md`: megaprompt para Copilot/VPS.
- `ACCEPTANCE_CHECKLIST.md`: criterios para aceptar el GPT y sus auditorias.

## Regla clave

Este GPT no opera produccion. Audita, disena, corrige contratos y prepara handoffs.
Codex/Copilot/VPS aplican cambios tecnicos solo cuando David lo autoriza.
