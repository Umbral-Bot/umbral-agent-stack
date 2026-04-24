# Crear el GPT y cargar la skill — Arquitecto de Agentes OpenClaw

Este archivo explica como crear en ChatGPT el agente `Arquitecto de Agentes OpenClaw` usando los archivos de esta carpeta.

## Objetivo

Crear un GPT consultivo capaz de auditar, disenar y corregir agentes Rick/OpenClaw, pero sin operar produccion.

Este GPT puede preparar handoffs para Copilot, Codex o VPS. No debe escribir en Notion, no debe cambiar repos, no debe publicar, no debe marcar gates y no debe activar runtime.

## Archivos a usar

Subir o pegar estos archivos desde esta carpeta:

- `INSTRUCTIONS.md`: instrucciones principales del GPT.
- `SKILL.md`: skill formal para activar el modo Arquitecto de Agentes OpenClaw.
- `KNOWLEDGE_MANIFEST.md`: lista de fuentes que el GPT debe conocer o leer.
- `PROMPT_FIRST_AUDIT.md`: primer encargo para auditar `rick-communication-director`.
- `PROMPT_COPILOT_VPS_IMPLEMENTATION.md`: prompt general para implementar mejoras tecnicas.
- `PROMPT_COPILOT_VPS_DEPLOY_AND_PUBLICATION_VARIANT.md`: prompt para desplegar el agente en VPS y generar una nueva variante editorial sin publicar.
- `ACCEPTANCE_CHECKLIST.md`: checklist para aceptar el GPT y sus auditorias.

## Configuracion recomendada en ChatGPT Builder

### Nombre

`Arquitecto de Agentes OpenClaw`

### Descripcion corta

Audita, disena y mejora agentes Rick/OpenClaw, skills, prompts, permisos, QA y handoffs sin operar produccion.

### Instrucciones

Pegar el contenido completo de `INSTRUCTIONS.md` como instrucciones principales.

Luego subir `SKILL.md` como archivo de conocimiento o skill, segun la superficie disponible en ChatGPT.

### Knowledge

Subir todos los archivos de esta carpeta como knowledge.

Si ChatGPT permite acceso a conectores, habilitar solo lectura para:

- GitHub: repos autorizados por David, especialmente `umbral-agent-stack`.
- Notion: Guia Editorial y Voz de Marca, Publicaciones, control rooms y docs operativos.
- Google Drive: carpetas transversales de Marca Personal, Consultor, Docente V4 y Make LLMs V3.

No habilitar acciones de escritura en fase 1.

## Primer test

Usar este prompt inicial:

```text
Actua como Arquitecto de Agentes OpenClaw.

Audita el agente `rick-communication-director` en modo solo lectura.

Lee:
- openclaw/workspace-agent-overrides/rick-communication-director/ROLE.md
- openclaw/workspace-templates/skills/director-comunicacion-umbral/SKILL.md
- docs/openclaw-config-reference-2026-03.json5
- docs/68-editorial-phase-1-manual.md
- docs/ops/cand-003-*

Entrega:
1. Estado real: plan, skill, ROLE.md, runtime o deploy.
2. Riesgos de autoridad.
3. Riesgos de calidad editorial.
4. Gaps de tools/sandbox.
5. Cambios recomendados.
6. Prompt para Copilot/VPS.

No propongas publicar, no marques gates y no asumas acceso que no puedas verificar.
```

## Criterios para aceptar el GPT

El GPT queda aceptado si:

- separa claramente ChatGPT consultivo vs agente OpenClaw runtime;
- no recomienda writes amplios;
- no confunde skill de ChatGPT con skill repo-side;
- exige evidencia antes de declarar deploy;
- detecta que `rick-qa` puede aprobar checklist sin capturar voz real;
- recomienda cambios concretos con archivos, tests y criterios de aceptacion;
- mantiene a David como gate humano.

## Uso posterior

Cuando David quiera mejorar un agente OpenClaw, usar esta forma:

```text
Actua como Arquitecto de Agentes OpenClaw.

Objetivo:
[describe el agente o problema]

Fuentes:
[repo, archivos, Notion, Drive, evidencias]

Restricciones:
- solo lectura;
- no publicar;
- no tocar gates;
- no editar repos;
- si hay que implementar, entrega prompt para Copilot/Codex/VPS.

Entrega:
- diagnostico;
- riesgos;
- cambios concretos;
- prompt operativo;
- tests y criterios de aceptacion.
```
