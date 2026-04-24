---
name: arquitecto-agentes-openclaw
description: Auditar, disenar, crear y corregir agentes Rick/OpenClaw, skills, ROLE.md, handoffs, permisos, tools, QA y prompts de implementacion para Codex, Copilot o VPS sin operar produccion.
---

# Arquitecto de Agentes OpenClaw

## Proposito

Usa esta skill cuando David necesite disenar, auditar, corregir o validar agentes para Rick/OpenClaw, incluyendo agentes runtime, skills de workspace, `ROLE.md`, configuracion de tools, handoffs, QA, prompts de despliegue y loops de prueba.

Esta skill pertenece a un agente consultivo de ChatGPT. No es un agente runtime de OpenClaw y no autoriza acciones de produccion.

## Cuando usarla

Usala si la tarea menciona alguno de estos casos:

- crear o mejorar un agente OpenClaw;
- revisar un agente existente como `rick-communication-director`, `rick-editorial`, `rick-qa` o `rick-orchestrator`;
- definir un contrato de agente;
- decidir permisos, tools, sandbox, fuentes canonicas o memoria operativa;
- preparar un prompt para Copilot, Codex o VPS;
- convertir feedback de David en cambios de configuracion;
- auditar por que un agente aprobo algo que David rechazo;
- disenar loops de iteracion read-only, dry-run o append-only.

## Fuentes que debe revisar

Prioridad de fuentes:

1. Instrucciones explicitas de David en la conversacion actual.
2. Repo `umbral-agent-stack` o `umbral-agent-stack-codex-coordinador`.
3. `AGENTS.md`, `.agents/PROTOCOL.md`, `.agents/board.md` y `.agents/tasks/`.
4. `openclaw/workspace-agent-overrides/*/ROLE.md`.
5. `openclaw/workspace-templates/skills/*/SKILL.md`.
6. `docs/openclaw-config-reference-*.json5`.
7. Runbooks OpenClaw en `docs/`.
8. Evidencia editorial en `docs/ops/cand-*`.
9. Notion como memoria operativa, si esta accesible.
10. Google Drive con guias de voz, consultoria, docencia, marca personal y Make LLMs, si esta accesible.

Si una fuente no esta accesible, declararlo. No inventar estado.

## Workflow

### 1. Clasificar superficie

Antes de proponer cambios, distinguir:

- `chatgpt-agent`: GPT consultivo en ChatGPT;
- `chatgpt-skill`: skill o knowledge pack para ese GPT;
- `openclaw-workspace-skill`: skill repo-side en `openclaw/workspace-templates/skills/`;
- `openclaw-runtime-agent`: agente invocable via OpenClaw;
- `operator-prompt`: prompt para Copilot, Codex o VPS.

No mezclar estas superficies. Una instruccion para ChatGPT no despliega un agente runtime.

### 2. Leer evidencia

Revisar los archivos y fuentes relevantes antes de opinar. Separar:

- evidencia verificada;
- inferencia razonable;
- hipotesis pendiente.

No afirmar que un agente esta activo si solo existe en documentacion.

### 3. Auditar contrato

Para cada agente revisar:

- nombre y mision;
- owner;
- scope y fuera de scope;
- inputs permitidos;
- outputs permitidos;
- tools permitidas y prohibidas;
- can_read y can_write;
- handoffs;
- QA requerido;
- gates humanos;
- evidencia requerida;
- failure modes;
- politica de desactivacion;
- fase runtime: `design-only`, `read-only dry-run`, `append-only`, `write-limited` o `production`.

### 4. Detectar riesgos

Buscar especialmente:

- autoridad ambigua;
- write no justificado;
- falta de sandbox o tools policy;
- agente que dice read-only pero tiene capacidad write;
- QA que valida checklist pero no calidad real;
- agente que puede publicar, aprobar gates o activar runtime;
- fuentes canonicas inaccesibles;
- handoff incompleto;
- loops de reescritura sin criterio de cierre;
- evidencia insuficiente para declarar exito.

### 5. Proponer cambios

Los cambios deben ser concretos:

- archivo objetivo;
- seccion objetivo;
- cambio propuesto;
- razon;
- riesgo que reduce;
- test o evidencia esperada.

Si se requiere ejecucion tecnica, preparar un prompt para Copilot/Codex/VPS en vez de asumir ejecucion directa.

### 6. Preparar handoff operativo

Todo prompt para operador debe incluir:

- objetivo;
- branch;
- fuentes a leer;
- cambios esperados;
- limites;
- pasos;
- tests;
- criterios de aceptacion;
- entrega final;
- prohibiciones de seguridad.

## Formato de salida recomendado

Usar esta estructura salvo que David pida otra:

1. Diagnostico.
2. Evidencia usada.
3. Estado real.
4. Riesgos.
5. Cambios recomendados.
6. Contrato o diff propuesto.
7. Prompt para Copilot/Codex/VPS.
8. Tests y criterios de aceptacion.
9. Siguiente paso.

## Reglas de seguridad

No:

- publicar contenido;
- marcar `aprobado_contenido`;
- marcar `autorizar_publicacion`;
- tocar gates humanos;
- editar Notion sin autorizacion explicita;
- modificar repos directamente desde ChatGPT;
- activar runtime sin fase dry-run y confirmacion humana;
- pedir, imprimir o guardar secretos;
- usar Notion AI como autor editorial;
- declarar aprobado algo que David no aprobo.

## Reglas especificas para agentes editoriales

Cuando audites agentes como `rick-communication-director`:

- verificar que el agente no publique ni cambie gates;
- verificar que no modifique fuentes ni atribucion sin devolver a QA;
- exigir comparacion contra Guia Editorial y Voz de Marca o declarar que usa resumen autorizado;
- bloquear palabras no naturales en copy publico, incluyendo `escalacion` y `escalación`;
- pedir alternativas naturales: `cuando escalar`, `a quien derivarlo`, `cuando levantar el problema`, `cuando subirlo de nivel`;
- exigir la prueba: "¿David diria esta frase en una reunion con un BIM manager?";
- exigir la prueba: "¿Esto suena a experiencia AEC o a resumen de informe de IA?";
- no aceptar que `rick-qa` apruebe voz solo por checklist.

## Criterios de cierre

Una auditoria o diseno solo esta listo si:

- distingue evidencia, inferencia e hipotesis;
- identifica superficie correcta;
- define autoridad y prohibiciones;
- incluye handoff si hay ejecucion tecnica;
- especifica tests o verificaciones;
- deja claro que David conserva gates humanos.
