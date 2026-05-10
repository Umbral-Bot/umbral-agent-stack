# O16.2 — n8n applicability scan (2026-05-10)

**Owner:** Copilot Chat (autonomous mandate, dm@umbralbim.cl)
**Hilo origen:** Coordinador de Agentes / Automatización Agentes — O16.2
**Status:** SCAN. Nada implementado. Veredicto por caso de uso.

## Contexto

La VPS Hostinger tiene n8n instalado y operativo, y Rick tiene capacidad comprobada de
crear/configurar workflows. Documentación de referencia: `https://docs.n8n.io/llms-full.txt`.

Este scan evalúa si n8n entra al frente O16.2 ahora, después, o nunca, **caso por caso**.

## Reglas duras (no negociar)

1. **n8n NO reemplaza** el pipeline Azure (ACA Jobs), Bicep, Docker/GHCR, ni los scripts
   Python (`scripts/aeco-kb/*.py`).
2. **n8n NO ejecuta** acciones destructivas o de alto privilegio sin autorización
   explícita por prompt (no `az role assignment create`, no `docker push`, no `ssh root`).
3. **n8n SÍ** puede entrar como capa de coordinación/notificación/registro/checklist,
   siempre que arranque como **manual-trigger o read-only**.
4. Cualquier workflow n8n que llame a Azure debe usar credencial scoped (Service Principal
   con rol `Reader` solamente, salvo que un caso justifique escritura y se autorice).
5. Cualquier workflow n8n debe ser auditable: log persistente + ejecución visible en el
   panel n8n. Nada de cron oculto.

## Tabla de aplicabilidad

| # | Caso de uso | ¿n8n aplica? | Momento | Riesgo | Decisión |
|---|---|---|---|---|---|
| 1 | Checklist previa al smoke (pre-flight: RBAC, jobs ACA, connection Foundry, index alias) | SÍ — read-only ideal para n8n | v0 antes de FASE F (semana 2026-06-09) | Bajo (HTTP GET a Azure ARM con SP Reader) | **documentar para después.** Implementar como workflow v0 manual-trigger antes del smoke, NO ahora. |
| 2 | Botón manual "run O16.2 smoke buildingsmart-only" | NO recomendado | n/a | Alto (botón que dispara `run_pipeline.sh` en VPS = side-effects en blob + Search index) | **descartar.** Mantener como `bash scripts/aeco-kb/run_pipeline.sh buildingsmart` ejecutado por Copilot-VPS con prompt explícito. n8n añade indirección sin reducir riesgo. |
| 3 | Notificación inicio/fin/error de jobs ACA | SÍ — caso típico n8n | v0 después de FASE C | Bajo (webhook ACA → n8n → Slack/email/Notion comment) | **documentar para después.** Útil pero no bloqueante para Q2. Postergar a Q3 o ventana buffer 2026-06-16. |
| 4 | Captura de status de ACA Jobs (último run, exit code, duración) | SÍ — read-only | v0 antes de FASE F | Bajo (HTTP GET ARM, SP Reader sobre rg-umbral-agents-prod) | **documentar para después.** Combinar con caso #1 en un solo workflow "O16.2 health check". |
| 5 | Registro de evidencia para audit (output del smoke → archivo persistente / Notion comment) | SÍ — pero sin escribir Notion sin autorización | v0 día del smoke (semana 2026-06-09) | Medio si escribe Notion, bajo si escribe a blob/issue GitHub | **documentar para después.** Versión v0: append a un GitHub Gist o issue comment. Notion solo si David autoriza. |
| 6 | Alerta si falla RBAC / crawler / parser / index / Foundry / File Search | SÍ — caso clásico monitoreo | v0 después de FASE D | Bajo (read-only + send notification) | **documentar para después.** Útil pero no bloqueante. Q3 candidate. |
| 7 | Preparación de Friday retro (snapshot index, seed list, screenshot del bot) | Parcial — n8n puede agregar el paquete | v0 día retro 2026-06-26 | Bajo | **documentar para después.** Manual checklist sigue siendo más confiable para el primer retro. |
| 8 | Registro de costos del smoke (consumo ACA + Search + Foundry) | Marginal | n/a | Bajo | **descartar para Q2.** Cost reporting Azure se hace nativo en portal o Cost Management; n8n no aporta. Reabrir Q3 si hay multi-tenant. |
| 9 | Workflow de rollback / checklist de emergencia (borrar index versionado, revertir alias, etc.) | NO recomendado | n/a | Alto (un click destructivo desde n8n = riesgo de borrar índice productivo por error) | **descartar.** Rollback debe ser comando `az` explícito ejecutado por humano con prompt copy-paste. n8n no reduce riesgo, lo amplifica. |

## Veredicto global

**n8n NO entra al core runtime de O16.2 en Q2.**

El primer caso razonable es un workflow **v0 health check + checklist** (combina casos
1 + 4 en un solo workflow read-only manual-trigger), implementable en la **ventana
buffer 2026-06-16 a 06-20**, después de que el smoke real haya pasado al menos una vez
manualmente. Esto valida el path crítico sin n8n y deja a n8n como capa de
observabilidad/coordinación, no como ejecutor.

Casos 3, 5, 6, 7 quedan documentados para Q3 (post-sponsorship-decision 2026-07-30).

Casos 2, 8, 9 descartados por costo/beneficio.

## Diseño tentativo del único workflow Q2-eligible (v0 health check)

**Trigger:** manual (botón en panel n8n)
**Pasos:**

1. HTTP GET → ARM API → `az containerapp job list -g rg-umbral-agents-prod --query "[].{name:name, state:properties.provisioningState}"` (vía SP Reader).
2. HTTP GET → ARM API → `az search index list --service-name srch-umbral-kb-prod --query "[?starts_with(name,'aeco-kb-es-v')].{name:name, docs:documentCount}"`.
3. HTTP GET → Foundry connection get (`aeco-kb-search`).
4. HTTP GET → role assignments del UAMI (verificar 5 roles esperados).
5. Aggregate → respuesta JSON con 4 secciones + flag overall `READY` / `NOT_READY`.
6. Output en panel n8n + opcional: copiar al portapapeles para pegar en Notion comment manual.

**Credencial requerida:** SP nuevo con rol `Reader` sobre `rg-umbral-agents-prod` y
`rg-dm-8454`. NO usar el UAMI productivo. NO usar credenciales de David personales.

**Implementación:** NO en este hilo. NO en Q2. Documentar como spec en
`docs/runbooks/n8n-o16-2-health-check-v0.md` antes de implementar (iteración futura).

## Fuera de scope para este hilo

- No se evalúa n8n como runtime alternativo a OpenClaw / dispatcher / worker (eso es
  decisión arquitectónica separada, fuera de O16.2).
- No se evalúa n8n para hilo RRSS Wave 2A (otro coordinador).
- No se evalúa n8n para hilo Granola (operacional, no de cambio).

## Decisión pendiente (David)

- [ ] Confirmar veredicto: n8n NO entra al core runtime O16.2 en Q2.
- [ ] Confirmar que el primer caso eligible (v0 health check) se implementa, si acaso,
      en ventana buffer 2026-06-16, no antes.
- [ ] Confirmar que casos 2/9 (botón ejecutor, rollback) quedan descartados sin reapertura.

## Referencias

- Decisión scope smoke: [2026-05-10-o16-2-buildingsmart-only-decision.md](2026-05-10-o16-2-buildingsmart-only-decision.md)
- Plan ejecución: [2026-05-10-o16-2-execution-plan.md](2026-05-10-o16-2-execution-plan.md)
- Política cross-thread: [docs/runbooks/cross-thread-vps-concurrency.md](../runbooks/cross-thread-vps-concurrency.md)
- Skill n8n local: `c:\Users\david\.claude\skills\n8n-expert\SKILL.md`
- Docs oficiales: <https://docs.n8n.io/llms-full.txt>
