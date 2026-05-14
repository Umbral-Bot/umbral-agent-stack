---
name: windows-vps-execution-split
description: Evitar que Copilot confunda la workstation Windows con la VPS al ejecutar tareas que tocan Azure AI Foundry, Azure OpenAI, OpenClaw, deployments o `openclaw-gateway.service`. Define qué superficie ejecuta cada acción, qué requiere autorización explícita de David, y cómo se hace el handoff Windows → VPS.
---

# Skill — Windows/VPS Execution Split

## Propósito

Evitar que Copilot confunda la workstation Windows con la VPS.

Este skill se aplica cuando una tarea involucra:

- Azure AI Foundry;
- Azure OpenAI / Cognitive Services;
- OpenClaw;
- VPS;
- modelos;
- deployments;
- `openclaw-gateway.service`;
- prompts entre Copilot Windows y Copilot-VPS.

## Regla central

Copilot Windows gestiona Azure / Foundry.
Copilot-VPS gestiona OpenClaw / servicios en VPS.

Esto incluye:

- Copilot Windows audita Azure / Foundry.
- Copilot Windows también puede configurar Azure / Foundry cuando David lo autorice.
- Copilot-VPS audita y modifica OpenClaw runtime cuando David lo autorice.

Nunca invertir superficies salvo autorización explícita de David.

## Copilot Windows

Responsable de:

- Azure CLI;
- Azure AI Foundry;
- Azure OpenAI / Cognitive Services;
- deployments;
- subscriptions;
- resource groups;
- quotas;
- keys bajo manejo seguro;
- scripts PowerShell;
- smoke Foundry read-only;
- configuración Foundry/Azure autorizada;
- creación/modificación de deployments autorizada;
- Realtime probe desde Azure;
- generación de prompts para Copilot-VPS.

Puede, si David autoriza:

- crear deployment;
- modificar deployment;
- ajustar capacity;
- actualizar configuración Foundry;
- ejecutar smoke de deployments;
- preparar variables de entorno requeridas;
- generar prompts para que Copilot-VPS configure OpenClaw.

No debe:

- editar `~/.openclaw/openclaw.json`;
- reiniciar `openclaw-gateway.service`;
- modificar runtime de la VPS;
- asumir que OpenClaw usa LiteLLM sin auditar.

## Copilot-VPS

Responsable de:

- auditar OpenClaw runtime;
- leer/modificar `~/.openclaw/openclaw.json`;
- crear backups;
- reiniciar `openclaw-gateway.service`;
- revisar logs con `journalctl`;
- ejecutar smoke OpenClaw;
- validar aliases;
- crear evidencia en `~/.coord-ag-evidence/...`.

Puede, si David autoriza:

- editar configuración local de OpenClaw;
- reiniciar gateway;
- probar aliases;
- aplicar rollback de configuración local;
- documentar evidencia en VPS.

No debe:

- instalar Azure CLI salvo autorización excepcional;
- auditar Foundry si no tiene `az`;
- crear/modificar deployments Azure;
- asumir RG/account/deployment;
- imprimir secretos;
- abrir puertos sin autorización.

## ChatGPT como consultor externo opcional

David puede pasar outputs a ChatGPT para:

- evaluar riesgos;
- revisar prompts;
- confirmar orden de ejecución;
- simplificar decisiones técnicas;
- detectar errores de superficie.

ChatGPT no reemplaza la autorización de David.

## Handoff correcto

1. Copilot Windows ejecuta Foundry audit.
2. Copilot Windows configura Azure / Foundry si David lo autoriza.
3. Copilot Windows obtiene:
   - resource group;
   - account name;
   - endpoint;
   - deployment name;
   - model name/version;
   - API version;
   - auth mode;
   - smoke result.
4. Copilot Windows genera prompt para Copilot-VPS.
5. Copilot-VPS:
   - hace backup de `~/.openclaw/openclaw.json`;
   - agrega alias usando el schema real;
   - no cambia default global;
   - reinicia gateway solo con autorización;
   - prueba alias nuevo;
   - prueba alias existente;
   - reporta PASS / PARTIAL / FAIL.
6. Se documenta en `docs/audits/...`.

## Convención de nombres

Usar nombres explícitos:

- `Foundry 1 - Windows - Audit GPT 5.5 + Realtime`
- `Foundry 2 - Windows - Configure GPT 5.5 Deployment`
- `OpenClaw 1 - VPS - Audit Model Gateway`
- `OpenClaw 2 - VPS - Add GPT 5.5 Alias`
- `OpenClaw 3 - VPS - Smoke + Fallback`
- `Docs 1 - Repo - Activation Audit`

## Checklist antes de ejecutar

Antes de ejecutar, responder:

- ¿Estoy en Windows o VPS?
- ¿La tarea requiere Azure CLI?
- ¿La tarea requiere OpenClaw runtime?
- ¿Es read-only o write?
- ¿Tengo autorización para modificar?
- ¿Dónde quedará la evidencia?
- ¿Qué comandos son read-only?
- ¿Qué comandos son write/restart?
- ¿Cuál es el rollback?
- ¿Conviene consultar a ChatGPT antes de continuar?
