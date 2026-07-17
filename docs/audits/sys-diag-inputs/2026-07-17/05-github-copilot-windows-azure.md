---
fuente: GitHub Copilot (chat, Windows de David)
prompt_origen: Prompt 5 (docs/plans/sys-diag-capture-prompts-2026-07-17.md)
fecha_captura: 2026-07-17 (según David; confirmar al pegar)
superficie: extensiones, Actions, entornos GitHub/Azure, ramas/PRs, scripts locales
modo: read-only
estado_completitud: COMPLETE_WITH_VISIBILITY_LIMITS (ingerido verbatim por orquestador Cursor desde transcript de-9d13c3, linea 4342)
redacciones_por_ingesta: 0
---

## Salida final de la IA (verbatim)

Auditoría completa (solo lectura, sin disparar workflows ni exponer valores de secretos):

```yaml
extensiones_vscode:
  - {nombre: ms-copilotstudio.vscode-copilotstudio, ¿relacionada_a_umbral?: false, etiqueta: UNKNOWN}  # instalada pero sin evidencia de uso en repos Umbral auditados
  - {nombre: anthropic.claude-code, ¿relacionada_a_umbral?: true, etiqueta: ACTIVE_HEALTHY}  # coincide con ramas claude/* dominantes en umbral-agent-stack y umbral-bot-2
  - {nombre: openai.chatgpt, ¿relacionada_a_umbral?: true, etiqueta: ACTIVE_HEALTHY}  # coincide con oai-umbral-agents-prod / oai-j2dimqy6 (Azure OpenAI)
  - {nombre: google.geminicodeassist, ¿relacionada_a_umbral?: false, etiqueta: UNKNOWN}  # sin evidencia de GCP en el stack Umbral (100% Azure)
  - {nombre: googlecloudtools.cloudcode, ¿relacionada_a_umbral?: false, etiqueta: UNKNOWN}
  - {nombre: googlecloudtools.datacloud, ¿relacionada_a_umbral?: false, etiqueta: UNKNOWN}
  - {nombre: ms-windows-ai-studio.windows-ai-studio, ¿relacionada_a_umbral?: false, etiqueta: UNKNOWN}
  - {nombre: ms-vscode.vscode-chat-customizations-evaluations, ¿relacionada_a_umbral?: false, etiqueta: UNKNOWN}
  - {nombre: github.vscode-github-actions, ¿relacionada_a_umbral?: true, etiqueta: ACTIVE_HEALTHY}  # gestiona los workflows auditados abajo
  - {nombre: github.vscode-pull-request-github, ¿relacionada_a_umbral?: true, etiqueta: ACTIVE_HEALTHY}  # coincide con alto volumen de PRs abiertos
  - {nombre: ms-azuretools.vscode-azure-mcp-server, ¿relacionada_a_umbral?: true, etiqueta: ACTIVE_HEALTHY}  # usado en esta misma auditoría
  - {nombre: ms-azuretools.vscode-azure-github-copilot, ¿relacionada_a_umbral?: true, etiqueta: ACTIVE_HEALTHY}
  - {nombre: ms-azuretools.azure-dev, ¿relacionada_a_umbral?: true, etiqueta: ACTIVE_HEALTHY}
  - {nombre: ms-azuretools.vscode-azurecontainerapps, ¿relacionada_a_umbral?: true, etiqueta: ACTIVE_HEALTHY}  # todas las RG Umbral usan Container Apps
  - {nombre: ms-azuretools.vscode-azurefunctions, ¿relacionada_a_umbral?: true, etiqueta: ACTIVE_HEALTHY}  # func-umbral-editorial-prod, func-umbral-prod-webhooks
  - {nombre: ms-azuretools.vscode-azureappservice, ¿relacionada_a_umbral?: true, etiqueta: ACTIVE_HEALTHY}
  - {nombre: ms-azuretools.vscode-azurestaticwebapps, ¿relacionada_a_umbral?: true, etiqueta: ACTIVE_HEALTHY}  # stapp-umbral-prod, mpbim-swa
  - {nombre: ms-azuretools.vscode-azurestorage, ¿relacionada_a_umbral?: true, etiqueta: ACTIVE_HEALTHY}
  - {nombre: ms-azuretools.vscode-cosmosdb, ¿relacionada_a_umbral?: true, etiqueta: ACTIVE_HEALTHY}  # cosmos-umbral-agents-prod
  - {nombre: ms-azuretools.vscode-bicep, ¿relacionada_a_umbral?: true, etiqueta: UNKNOWN}  # no se confirmó IaC en repos; RGs pudieron crearse por CLI/portal
  - {nombre: ms-azuretools.vscode-azureresourcegroups, ¿relacionada_a_umbral?: true, etiqueta: ACTIVE_HEALTHY}
  - {nombre: ms-azuretools.vscode-containers, ¿relacionada_a_umbral?: true, etiqueta: ACTIVE_HEALTHY}
  - {nombre: ms-azuretools.vscode-azurevirtualmachines, ¿relacionada_a_umbral?: false, etiqueta: UNKNOWN}  # VM "OpenClaw" hallada es Hyper-V local, no Azure VM
  - {nombre: ms-vscode.azurecli, ¿relacionada_a_umbral?: true, etiqueta: ACTIVE_HEALTHY}
  - {nombre: ms-vscode.vscode-node-azure-pack, ¿relacionada_a_umbral?: true, etiqueta: ACTIVE_HEALTHY}  # umbral-bot-2 corre azure-web-ci (Node)
  - {nombre: ms-playwright.playwright, ¿relacionada_a_umbral?: true, etiqueta: ACTIVE_HEALTHY}  # workflow e2e-playwright-azure en umbral-bot-2
  - {nombre: ms-azure-load-testing.microsoft-testing, ¿relacionada_a_umbral?: false, etiqueta: UNKNOWN}  # sin evidencia de uso en Umbral

actions_workflows:
  - {repo: Umbral-Bot/umbral-agent-stack, workflow: Tests, trigger: "push, pull_request", ultima_corrida_estado: "success (2026-07-17)", etiqueta: ACTIVE_HEALTHY}
  - {repo: Umbral-Bot/umbral-agent-stack, workflow: "Tests (ID duplicado 241746553)", trigger: UNKNOWN, ultima_corrida_estado: "sin corridas en muestreo reciente", etiqueta: ACTIVE_NOISY}  # 2 workflows activos con el mismo nombre "Tests"
  - {repo: Umbral-Bot/umbral-agent-stack, workflow: "AECO KB GHCR Images", trigger: UNKNOWN, ultima_corrida_estado: "sin corridas en muestreo reciente (últimas 25)", etiqueta: UNKNOWN}
  - {repo: Umbral-Bot/umbral-agent-stack, workflow: "Copilot code review", trigger: pull_request (implícito), ultima_corrida_estado: "sin corridas en muestreo reciente", etiqueta: UNKNOWN}
  - {repo: Umbral-Bot/umbral-agent-stack, workflow: "Copilot cloud agent", trigger: dynamic, ultima_corrida_estado: "sin corridas en muestreo reciente", etiqueta: UNKNOWN}
  - {repo: Umbral-Bot/umbral-bot-2, workflow: azure-web-ci, trigger: "push, pull_request", ultima_corrida_estado: "success (2026-07-17)", etiqueta: ACTIVE_HEALTHY}
  - {repo: Umbral-Bot/umbral-bot-2, workflow: "Azure production deploy (SWA + ACA)", trigger: workflow_dispatch, ultima_corrida_estado: "success (2026-07-16)", etiqueta: ACTIVE_HEALTHY}
  - {repo: Umbral-Bot/umbral-bot-2, workflow: "beta-anon-live", trigger: UNKNOWN, ultima_corrida_estado: "sin corridas en muestreo reciente", etiqueta: UNKNOWN}
  - {repo: Umbral-Bot/umbral-bot-2, workflow: "e2e-playwright-azure", trigger: UNKNOWN, ultima_corrida_estado: "sin corridas en muestreo reciente", etiqueta: UNKNOWN}
  - {repo: Umbral-Bot/umbral-bot-2, workflow: Test, trigger: UNKNOWN, ultima_corrida_estado: "sin corridas en muestreo reciente", etiqueta: UNKNOWN}
  - {repo: Umbral-Bot/umbral-bot-2, workflow: "Copilot code review", trigger: pull_request (implícito), ultima_corrida_estado: "sin corridas en muestreo reciente", etiqueta: UNKNOWN}
  - {repo: Umbral-Bot/umbral-bot-2, workflow: "Copilot cloud agent", trigger: dynamic, ultima_corrida_estado: "sin corridas en muestreo reciente", etiqueta: UNKNOWN}
  - {repo: Umbral-Bot/mp-bim-radar, workflow: ci, trigger: pull_request, ultima_corrida_estado: "success (2026-07-08)", etiqueta: ACTIVE_HEALTHY}
  - {repo: Umbral-Bot/mp-bim-radar, workflow: "ingest-daily", trigger: schedule, ultima_corrida_estado: "success (2026-07-08); 1 startup_failure el 2026-07-02 y 1 failure el 2026-06-22", etiqueta: ACTIVE_NOISY}
  - {repo: Umbral-Bot/mp-bim-radar, workflow: "weekly-cost-report", trigger: schedule, ultima_corrida_estado: "success (2026-07-06)", etiqueta: ACTIVE_HEALTHY}
  - {repo: Umbral-Bot/mp-bim-radar, workflow: "swa-dashboard", trigger: workflow_dispatch, ultima_corrida_estado: "success (2026-06-19)", etiqueta: ACTIVE_HEALTHY}
  - {repo: Umbral-Bot/mp-bim-radar, workflow: "build-image", trigger: push, ultima_corrida_estado: "success (2026-06-19)", etiqueta: ACTIVE_HEALTHY}
  - {repo: Umbral-Bot/mp-bim-radar, workflow: "deploy-azure", trigger: UNKNOWN, ultima_corrida_estado: "sin corridas en muestreo reciente", etiqueta: UNKNOWN}
  - {repo: Umbral-Bot/notion-governance, workflow: "Copilot cloud agent", trigger: dynamic, ultima_corrida_estado: "success (2026-04-11), única corrida registrada", etiqueta: OBSOLETE}
  - {repo: Umbral-Bot/visor-ifc, workflow: "(ninguno)", trigger: "N/A", ultima_corrida_estado: "N/A — sin workflows en el repo", etiqueta: NEVER_SHIPPED}
  - {repo: Umbral-Bot/umbral-agent-forge, workflow: "(ninguno)", trigger: "N/A", ultima_corrida_estado: "N/A — sin workflows en el repo", etiqueta: NEVER_SHIPPED}
  - {repo: Umbral-Bot/umbral-bim, workflow: "(ninguno)", trigger: "N/A", ultima_corrida_estado: "N/A — sin workflows en el repo", etiqueta: NEVER_SHIPPED}

entornos_github:
  - {repo: Umbral-Bot/mp-bim-radar, "environments/secrets POR NOMBRE": "env: production | secrets(repo): ACS_EMAIL_CONNECTION_STRING, ACS_EMAIL_SENDER, AZURE_CLIENT_ID, AZURE_RESOURCE_GROUP, AZURE_STATIC_WEB_APPS_API_TOKEN, AZURE_SUBSCRIPTION_ID, AZURE_TENANT_ID, MP_TICKET, PG_AZURE_PASSWORD, PG_DB, PG_HOST, PG_PASSWORD, PG_PORT, PG_SSLMODE, PG_USER", etiqueta: ACTIVE_HEALTHY}
  - {repo: Umbral-Bot/umbral-bot-2, "environments/secrets POR NOMBRE": "envs: copilot, production | secrets(repo): ninguno detectado (probable auth por OIDC vía id-umbral-gha-prod-deploy)", etiqueta: ACTIVE_HEALTHY}
  - {repo: Umbral-Bot/umbral-agent-stack, "environments/secrets POR NOMBRE": "env: copilot | secrets(repo): GHCR_PAT", etiqueta: ACTIVE_HEALTHY}
  - {repo: Umbral-Bot/notion-governance, "environments/secrets POR NOMBRE": "env: copilot | secrets(repo): ninguno detectado", etiqueta: ACTIVE_HEALTHY}
  - {repo: Umbral-Bot/visor-ifc, "environments/secrets POR NOMBRE": "sin environments, sin secrets detectados", etiqueta: UNKNOWN}
  - {repo: Umbral-Bot/umbral-agent-forge, "environments/secrets POR NOMBRE": "sin environments, sin secrets detectados", etiqueta: ORPHAN}
  - {repo: Umbral-Bot/umbral-bim, "environments/secrets POR NOMBRE": "sin environments, sin secrets detectados", etiqueta: ORPHAN}
  - {repo: "Umbral-Bot (org-level)", "environments/secrets POR NOMBRE": "403 Forbidden — requiere scope admin:org, no visible con el token actual", etiqueta: UNKNOWN}

ramas_y_prs:
  - repo: Umbral-Bot/umbral-agent-stack
    ramas_remotas_sin_merge_conteo: "236 de 264 totales (89%)"
    prs_abiertos:
      - {num: 541, rama: "claude/plan-sys-diag-openclaw-worksystem-2026-07-17", edad: "~0 días"}
      - {num: 521, rama: "copilot/docs-openclaw-models-hygiene-20260704", edad: "~13 días"}
    ramas_stale_top5: ["copilot/create-umbral-agent-stack-repo (2026-02-26)", "cursor/development-environment-setup-6340 (2026-02-27)", "rick/windows-fs-tools (2026-03-02)", "rick/windows-fs-b64 (2026-03-02)", "cursor/development-environment-setup-ac64 (2026-03-04)"]
    etiqueta: ACTIVE
  - repo: Umbral-Bot/notion-governance
    ramas_remotas_sin_merge_conteo: "3 de 5 totales"
    prs_abiertos:
      - {num: 6, rama: "docs/workspace-megadiagnostico-2026-05-20", edad: "~58 días (draft)"}
      - {num: 3, rama: "copilot/policy-force-push-safety-2026-05-06", edad: "~71 días"}
    ramas_stale_top5: ["copilot/policy-force-push-safety-2026-05-06 (2026-05-06)", "docs/workspace-megadiagnostico-2026-05-20 (2026-05-21)", "chore/mirror-sync-secret-output-guard-triage-2026-05-21 (2026-05-21)"]
    etiqueta: ACTIVE
  - repo: "Umbral-Bot/umbral-bot (NO EXISTE tal cual — se usó umbral-bot-2 como equivalente más cercano)"
    ramas_remotas_sin_merge_conteo: "84 de 91 totales (92%)"
    prs_abiertos:
      - {num: 463, rama: "cursor/fix-settings-hide-training-placeholder-20260715", edad: "~2 días"}
      - {num: 449, rama: "copilot/docs-pr448-swa-closeout-20260713", edad: "~4 días"}
      - {num: 442, rama: "copilot/docs-b3-pr441-evidence", edad: "~6 días"}
      - {num: 429, rama: "claude/spike-loading-lab-20260709", edad: "~7 días"}
      - {num: 413, rama: "claude/ops-azure-cost-optimization-2026-07", edad: "~10 días"}
      - {num: 378, rama: "umbralbim-copilot-investigate-notion-mcp", edad: "~14 días"}
    ramas_stale_top5: ["cursor/development-environment-setup-bf93 (2026-03-03)", "antigravity/main (2026-03-05)", "claude/main (2026-03-05)", "codex/main (2026-03-05)", "cursor/main (2026-03-05)"]
    etiqueta: ACTIVE

azure_vinculado:
  - {recurso: "rg-umbral-agents-prod (eastus2): Cosmos DB, AI Search, Azure OpenAI, Document Intelligence, Speech, Service Bus, 3x Container App Jobs (aeco-pdf-parser/source-crawler/index-pipeline), Function App editorial, Key Vault, Log Analytics", para_qué: "Backend de producción del stack de agentes IA + pipeline AECO KB de umbral-agent-stack", ¿activo?: true, etiqueta: ACTIVE_HEALTHY}
  - {recurso: "rg-umbral-prod-centralus: Static Web App, Front Door+WAF, PostgreSQL Flexible Server, Container App+ACR, CIAM (umbralbimcustomers), Email/Communication Services (dominio umbralbim.io), identidad federada GHA", para_qué: "Producción del SaaS Umbral BIM (umbral-bot-2), dominio umbralbim.io", ¿activo?: true, etiqueta: ACTIVE_HEALTHY}
  - {recurso: "rg-umbral-nonprod-centralus: PostgreSQL, ACR, App Config, Container App, + storage/func 'consultor-generator' (¡de otro proyecto!)", para_qué: "Entorno no-prod de Umbral, MEZCLADO con recursos del proyecto 'Consultor' (func-consultor-generator-dm/v1)", ¿activo?: true, etiqueta: ACTIVE_NOISY}
  - {recurso: "rg-mp-bim-radar (brazilsouth): Container App 'metabase', Container App Job ingest, Static Web App, Email/Communication Services", para_qué: "Backend + dashboard de mp-bim-radar (BI/ingesta)", ¿activo?: true, etiqueta: ACTIVE_HEALTHY}
  - {recurso: "rg-visor-ifc + rg-visor-ifc-secure (eastus2): Container Apps (api, ladybug), ACR, Storage; variante 'secure' añade Azure OpenAI", para_qué: "Visor IFC/BIM con análisis ambiental (Ladybug); variante secure para datos sensibles", ¿activo?: true, etiqueta: ACTIVE_HEALTHY}
  - {recurso: "rg-umbral-strangler-staging (eastus2): solo 1 Static Web App", para_qué: "Aparente entorno de staging para migración 'strangler fig', muy poco poblado", ¿activo?: UNKNOWN, etiqueta: ORPHAN}
  - {recurso: "2x 'MCPP Subscription' (fbb6fa43…, a0d082b9…)", para_qué: "Solo contienen RG 'mcpp-purchase' (marketplace), sin relación con Umbral", ¿activo?: false, etiqueta: UNKNOWN}

scripts_locales:
  - {path: "C:\\GitHub\\umbral-agent-stack-codex\\scripts\\vm\\start_granola_vm_raw_intake_hidden.ps1", propósito: "Tarea programada diaria (GranolaVmRawIntake) — intake VM", última_modificación: UNKNOWN (no inspeccionado directamente), etiqueta: ACTIVE_HEALTHY}
  - {path: "C:\\GitHub\\umbral-agent-stack-codex\\scripts\\vm\\start_granola_vm_raw_intake_startup_hidden.ps1", propósito: "Tarea al inicio de sesión (GranolaVmRawIntakeStartup) — ÚLTIMO RESULTADO: fallo (código 1) el 2026-07-15", última_modificación: UNKNOWN, etiqueta: ACTIVE_NOISY}
  - {path: "C:\\GitHub\\umbral-agent-stack-codex\\scripts\\vm\\start_primary_worker_hidden.ps1", propósito: "Tarea al inicio de sesión (UmbralWorkerPrimary) — último resultado OK", última_modificación: UNKNOWN, etiqueta: ACTIVE_HEALTHY}
  - {path: "C:\\GitHub\\notion-governance\\scripts\\daily-registry-backup.ps1", propósito: "Backup diario 03:00 del registro canónico de agentes IA (ver ADR-04 de notion-governance)", última_modificación: UNKNOWN, etiqueta: ACTIVE_HEALTHY}
  - {path: "C:\\Users\\david\\vm_script.ps1", propósito: "Invoke-Command a VM Hyper-V 'OpenClaw' para chequear versión/doctor de openclaw", última_modificación: "2026-02-19", etiqueta: SECURITY_RISK}  # credencial en texto plano hardcodeada, valor NO reproducido aquí
  - {path: "C:\\Users\\david\\Documents\\_audit-2026-07\\ (scan-*.ps1, exec\\d19-lote-*\\rollback.ps1, token-map.csv, etc.)", propósito: "Kit ad-hoc de auditoría/remediación previa (escaneo de superficies, duplicados, ejecución por lotes con rollback)", última_modificación: "hasta 2026-07-14/17", etiqueta: ACTIVE_NOISY}
  - {path: "C:\\Users\\david\\.coord-ag-evidence\\pit-p10-sec63-retry-20260623\\ (poller, watchdog, fastclose)", propósito: "Evidencia/orquestación de coordinación multi-agente ligada a trabajo P10 de umbral-agent-stack", última_modificación: "2026-07-17 (hoy)", etiqueta: ACTIVE_HEALTHY}
  - {path: "C:\\Users\\david\\.coord-ag-evidence\\pit-p10-*-20260622\\, pit-dry-run\\, etc. (11 carpetas más)", propósito: "Evidencia histórica de rondas de coordinación de agentes (P1B/P4/P5/P6/P9/P10) ya cerradas", última_modificación: "2026-06-10 a 2026-06-22", etiqueta: OBSOLETE}
  - {path: "C:\\Users\\david\\.codex\\skills\\forja-agente-mcs\\sync-a-agentes.ps1 (+ copias en .cursor\\ y .gemini\\)", propósito: "Sincronización del skill 'Forja Agentes M365' (Umbral BIM) hacia agentes/herramientas", última_modificación: UNKNOWN, etiqueta: ACTIVE_HEALTHY}
  - {path: "C:\\Users\\david\\.agents\\hooks\\scripts\\track-telemetry.ps1", propósito: "Hook de telemetría genérico para skills de Azure Copilot (no específico de Umbral)", última_modificación: "2026-05-21", etiqueta: UNKNOWN}

oportunidades:
  - "umbral-agent-stack tiene 236/264 ramas remotas sin mergear (89%) — implementar auto-delete de rama post-merge y una limpieza puntual del backlog de ramas viejas (varias de feb/mar 2026)."
  - "vm_script.ps1 en el home de David expone una credencial en texto plano para la VM OpenClaw — rotar el password y migrar a un vault (DPAPI/Credential Manager/Key Vault) de inmediato."
  - "GranolaVmRawIntakeStartup falla en su última ejecución y depende de un clon local no listado como proyecto (C:\\GitHub\\umbral-agent-stack-codex) — investigar el fallo y consolidar/documentar ese clon o eliminarlo si es redundante."
  - "rg-umbral-nonprod-centralus mezcla recursos de Umbral con recursos del proyecto 'Consultor' (func-consultor-generator-*) — separar en RGs propios para evitar confusión de costos/gobernanza."
  - "Hay un workflow 'Tests' duplicado (2 IDs distintos, mismo nombre) en umbral-agent-stack — auditar cuál es el vigente y eliminar/renombrar el redundante."

unknowns:
  - "No existe repo 'Umbral-Bot/umbral-bot' exacto en la org; se interpretó como umbral-bot-2 (el más activo/cercano al nombre)."
  - "Umbral-Bot/umbral-bot-copilot, referenciado por un proyecto local configurado, devuelve 404 en GitHub — no se pudo determinar si fue renombrado o borrado."
  - "Secrets a nivel organización de Umbral-Bot: no visibles (403, requiere scope admin:org)."
  - "Contenido de token-map.csv (dentro de _audit-2026-07) no fue abierto — podría contener mapeos sensibles; requiere revisión manual del propio usuario."
  - "rg-umbral-strangler-staging con un solo recurso: no se pudo determinar si es un experimento activo o un remanente abandonado."
  - "Fechas exactas de última modificación de varios scripts en C:\\GitHub\\*\\scripts\\ no se inspeccionaron directamente (se infirió actividad desde el historial de Scheduled Tasks, no desde el filesystem)."
```

**Nota de seguridad**: encontré una contraseña en texto plano en `vm_script.ps1` — no la reproduje en este reporte, pero recomiendo rotarla cuanto antes.

Entregué la auditoría YAML solo-lectura del stack Umbral (GitHub + Windows local), cubriendo las 8 secciones pedidas: extensiones VS Code relevantes a agentes/IA/Azure, workflows de Actions (Umbral-Bot org), environments/secrets por nombre, ramas y PRs de umbral-agent-stack/notion-governance/umbral-bot-2, recursos Azure vinculados (7 resource groups, todos en la suscripción "Azure subscription 1"), scripts locales (incluyendo tareas programadas), oportunidades concretas y unknowns.

Hallazgo destacado que requiere atención inmediata: `C:\Users\david\vm_script.ps1` contiene una contraseña en texto plano para una VM Hyper-V ("OpenClaw") — no se reprodujo el valor en el reporte, pero se recomienda rotarla y moverla a un vault.

No se modificó, borró ni disparó nada: los clones bare usados para analizar ramas se hicieron en una carpeta temporal aparte y ya fueron eliminados.
