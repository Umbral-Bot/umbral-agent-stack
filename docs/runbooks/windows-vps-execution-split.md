# Runbook — Windows/VPS Execution Split

> Versión narrativa de [`.agents/skills/windows-vps-execution-split/SKILL.md`](../../.agents/skills/windows-vps-execution-split/SKILL.md). Para activar un modelo Foundry en OpenClaw end-to-end, ver también [`.agents/skills/openclaw-foundry-activation/SKILL.md`](../../.agents/skills/openclaw-foundry-activation/SKILL.md).

## Por qué existe este patrón

El Umbral Agent Stack vive en dos superficies muy distintas:

- **Workstation Windows** de David, donde corre Copilot dentro de VSCode y donde está instalado Azure CLI, las credenciales Foundry, y los scripts PowerShell.
- **VPS Linux** de Umbral, donde corre OpenClaw, el `openclaw-gateway.service`, los workers y los daemons en `systemd --user`.

El error más recurrente cuando un solo hilo intenta resolver una tarea cross-superficie es:

- pedirle a Copilot-VPS que instale Azure CLI solo para "verificar el deployment";
- pedirle a Copilot Windows que edite `~/.openclaw/openclaw.json`;
- asumir que OpenClaw usa LiteLLM sin auditar el schema real;
- declarar un cambio "aplicado" cuando en realidad solo está committeado.

Este runbook fija la división y el handoff explícito entre superficies.

## Roles

### David

Decide, prioriza y autoriza.

Cualquier acción de **escritura o configuración** en runtime, Azure, Foundry, OpenClaw, credenciales, despliegues o servicios requiere autorización explícita de David. No alcanza con que la tarea "tenga sentido" — el cambio se ejecuta solo después del go.

### Copilot Windows

- Gestiona Azure CLI, Azure AI Foundry, Azure OpenAI, subscriptions, resource groups, deployments, quotas, keys.
- **Audita** Foundry / Azure por defecto.
- **Configura** Foundry / Azure cuando David lo autoriza, incluyendo crear, modificar o eliminar deployments y ajustar capacity.
- Genera los prompts que se van a pegar en Copilot-VPS.
- No edita `~/.openclaw/openclaw.json`, no reinicia `openclaw-gateway.service`, no toca el runtime de la VPS directamente.

### Copilot-VPS

- Audita y opera OpenClaw runtime: `openclaw-gateway.service`, `~/.openclaw/openclaw.json`, `systemctl --user`, `journalctl --user`, smoke gateway, aliases.
- **Modifica** la configuración local de OpenClaw cuando David lo autoriza, con backup, diff y rollback documentado.
- No instala Azure CLI solo para auditar Foundry.
- No crea/modifica deployments en Azure.
- No abre puertos ni cambia el default global de modelo sin autorización.

### ChatGPT (consultor externo opcional)

- Revisa estrategia, prompts y outputs cuando David lo decide.
- Detecta riesgos y errores de superficie.
- No ejecuta cambios en repo, Azure, VPS u OpenClaw por sí mismo.
- No reemplaza la autorización de David.

Flujo recomendado: Copilot prepara → David puede pasar el resultado a ChatGPT para revisión → ChatGPT recomienda → David autoriza → Copilot ejecuta.

## Audit vs configuración

Es importante distinguir explícitamente:

- **Audit** = read-only. Lista deployments, lee `openclaw.json`, mira logs, hace smoke mínimo. No requiere autorización adicional siempre que no imprima secretos.
- **Configuración** = write. Crea/modifica deployments en Foundry, edita `openclaw.json`, reinicia gateway, ajusta capacity. **Siempre** requiere autorización explícita de David.

Si en una misma tarea hay audit + configuración, separarlos en pasos distintos y pedir el go entre ambos.

## Ejemplos correctos e incorrectos

### Correcto

- "Copilot Windows: audita el deployment `gpt-5.5` en Foundry, devuelve endpoint, deployment name, API version y smoke status. No imprimas keys."
- "Copilot Windows (autorizado por David): crea el deployment `gpt-5.5` en Foundry con capacity X, reporta provisioning state y smoke."
- "Copilot-VPS: audita `~/.openclaw/openclaw.json`, dime el schema real del provider `azure-openai-responses` sin modificar nada."
- "Copilot-VPS (autorizado por David): hacé backup de `openclaw.json`, agregá el alias `azure-openai-responses/gpt-5.5`, reiniciá gateway y corré smoke alias nuevo + alias existente."

### Incorrecto

- "Copilot-VPS, instalá `az` para revisar Foundry."
- "Copilot Windows, editá `openclaw.json` por SSH."
- "Reiniciá el gateway si te parece" (sin autorización explícita).
- Una sola tarea que mezcla "audit Foundry + crear deployment + patch OpenClaw + restart" sin separar pasos ni pedir go entre ellos.
- Cambiar el default global de modelo "de paso".

## Flujo Foundry → OpenClaw

1. **Foundry audit (Windows, read-only).** Devuelve subscription, resource group, account, endpoint, deployment name, model name/version, API version, auth mode, region, provisioning state, capacity, smoke status.
2. **Foundry configuration (Windows, autorizada).** Si falta el deployment o hay que ajustar capacity, Copilot Windows ejecuta los cambios bajo autorización explícita y vuelve a hacer smoke.
3. **OpenClaw audit (VPS, read-only).** Confirma estado de `openclaw-gateway.service`, lee `~/.openclaw/openclaw.json`, identifica el schema real del provider y los modelos existentes.
4. **Preparar alias.** Solo si los pasos 1–3 dieron PASS y el schema real fue identificado. Alias recomendado: `azure-openai-responses/gpt-5.5`.
5. **Activación (VPS, autorizada).** Backup → patch del path real → validar JSON → mostrar diff → reiniciar gateway → smoke alias nuevo + alias existente → PASS / PARTIAL / FAIL.
6. **Documentar.** Resultado en `docs/audits/...` (sin secretos).

## Evidencia

Toda operación deja evidencia:

| Superficie | Path |
|---|---|
| Windows | `C:\GitHub\.coord-ag-evidence\...` |
| VPS | `~/.coord-ag-evidence/...` |
| Repo final | `docs/audits/...` |

Nunca guardar secrets, tokens ni keys en evidencia.

## Rollback

Patch de `openclaw.json`:

```bash
cp -a <backup> ~/.openclaw/openclaw.json
systemctl --user restart openclaw-gateway
```

Configuración Foundry / deployment:

- Documentar comando `az` inverso al inicio de la tarea, antes de aplicar.
- No ejecutar rollback automático: pedir confirmación a David salvo falla grave en runtime.

## Tabla de responsabilidades

| Acción | Superficie | Autorización requerida |
|---|---|---|
| `az account show`, `az resource list` | Copilot Windows | No (read-only, sin secretos) |
| Listar deployments Foundry | Copilot Windows | No |
| Smoke Foundry sin imprimir keys | Copilot Windows | No |
| Crear / modificar / eliminar deployment Azure | Copilot Windows | Sí (David explícito) |
| Ajustar capacity / quota | Copilot Windows | Sí |
| Configurar Realtime en Foundry | Copilot Windows | Sí |
| Leer `~/.openclaw/openclaw.json` | Copilot-VPS | No |
| `systemctl --user status`, `journalctl --user` | Copilot-VPS | No |
| Smoke gateway sin escribir | Copilot-VPS | No |
| Backup + patch `openclaw.json` | Copilot-VPS | Sí |
| Reiniciar `openclaw-gateway.service` | Copilot-VPS | Sí |
| Cambiar default global de modelo | Copilot-VPS | Sí (excepcional) |
| Instalar Azure CLI en VPS | Copilot-VPS | Sí (excepcional) |
| Editar repo, abrir PR draft | Coordinador | No (mientras no toque runtime ni secretos) |
| Mergear PR, push a runtime, escribir Notion productivo, activar cron | Cualquier agente | Sí |

## Cuándo invocar este runbook

- Cualquier tarea que mencione Foundry, Azure OpenAI, OpenClaw, gateway, deployments, modelos o aliases.
- Cualquier prompt que vaya a ser pegado en Copilot-VPS.
- Antes de generar un megaprompt cross-superficie.
- Cuando aparezca duda sobre quién ejecuta qué.
