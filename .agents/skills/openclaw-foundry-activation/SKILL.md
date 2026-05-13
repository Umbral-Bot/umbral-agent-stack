---
name: openclaw-foundry-activation
description: Activar un deployment de Azure AI Foundry / Azure OpenAI como alias disponible en OpenClaw sin cambiar el default global. Coordina audit y configuración Foundry desde Copilot Windows con audit y patch del gateway desde Copilot-VPS, exigiendo autorización explícita de David para cualquier write.
---

# Skill — Activar modelo Foundry en OpenClaw

## Objetivo

Agregar un deployment de Azure AI Foundry / Azure OpenAI como alias disponible en OpenClaw sin cambiar el default global.

## Actores

- David: autoriza.
- Copilot Windows: gestiona Azure / Foundry.
- Copilot-VPS: gestiona OpenClaw runtime.
- ChatGPT: consultor externo opcional para revisar estrategia, prompts y riesgos.

## Flujo obligatorio

### 1. Foundry audit — Windows

Ejecutar desde Copilot Windows.

Obtener:

- subscription;
- resource group;
- account;
- endpoint;
- deployment name;
- model name;
- model version;
- API version;
- auth mode;
- region;
- provisioning state;
- capacity;
- smoke status.

No imprimir keys.

### 2. Foundry configuration — Windows

Solo con autorización explícita de David.

Copilot Windows puede:

- crear deployment;
- modificar deployment;
- ajustar capacity;
- configurar modelo en Foundry;
- probar deployment;
- validar API version;
- auditar Realtime;
- preparar datos para OpenClaw.

Debe:

- documentar comandos;
- no imprimir secrets;
- dejar evidencia;
- definir rollback si aplica;
- pedir confirmación antes de cambios irreversibles.

### 3. OpenClaw audit — VPS

Ejecutar desde Copilot-VPS.

Verificar:

- `openclaw-gateway.service`;
- `~/.openclaw/openclaw.json`;
- schema real;
- provider existente;
- modelos existentes;
- si LiteLLM está activo o no;
- si requiere restart.

No modificar archivos.
No reiniciar.

### 4. Preparar alias

Alias recomendado:
`azure-openai-responses/gpt-5.5`

Solo si:

- Foundry audit PASS;
- deployment existe;
- smoke Foundry PASS;
- OpenClaw audit identifica schema real.

No asumir schema.
No usar patch fijo si el schema real difiere.

### 5. Activación — VPS

Con autorización explícita:

- backup de `~/.openclaw/openclaw.json`;
- editar solo `.models.providers["azure-openai-responses"].models[]` o el path real detectado;
- no tocar `agents.list[*].model.primary`;
- no tocar defaults;
- no borrar modelos existentes;
- validar JSON;
- mostrar diff;
- reiniciar `openclaw-gateway.service`;
- smoke alias nuevo;
- smoke alias existente;
- reportar PASS / PARTIAL / FAIL.

### 6. Rollback

Documentar:

```bash
cp -a <backup> ~/.openclaw/openclaw.json
systemctl --user restart openclaw-gateway
```

No ejecutar rollback automático salvo falla grave o autorización.

## Stop conditions

Abortar si:

- Foundry audit no es PASS;
- deployment exacto no existe;
- smoke Foundry falla;
- falta API key;
- schema de OpenClaw no coincide;
- patch tocaría default global;
- se imprimirían secretos;
- restart no está autorizado;
- OpenClaw no vuelve a levantar;
- Azure configuration requiere cambios no autorizados;
- Realtime se intenta mezclar con chat normal.

## Realtime

Realtime no se mezcla con chat normal.

Realtime requiere:

- deployment realtime confirmado;
- endpoint WebSocket/WebRTC;
- compatibilidad OpenClaw;
- decisión de arquitectura separada.

No activar Realtime junto con GPT-5.5 chat.
