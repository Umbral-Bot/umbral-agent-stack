# Audit — C-Vía 3: GHCR privado + PAT en Key Vault para AECO KB Pipeline

**Fecha**: 2026-05-15 · **Autor**: GitHub Copilot (Coordinador de Agentes) · **Autorización**: David Moreira · **Sub-task**: O16.2/053

---

## 1. Decisión

Mantener los packages container del pipeline AECO KB (`ghcr.io/umbral-bot/aeco-source-crawler`, `aeco-pdf-parser`, `aeco-index-pipeline`) como **privados en GHCR** y desplegar los ACA Jobs usando un **PAT classic** almacenado en **Azure Key Vault** (`kv-umbral-agents-prod`, secret `ghcr-pat`), pasado a cada job vía `registries[].passwordSecretRef`.

Esta vía se denomina internamente **C-Vía 3**, en contraste con:
- **C-Vía 1**: hacer públicos los packages (descartada — ver sección 2).
- **C-Vía 2**: migrar a Azure Container Registry (ACR) con UAMI + AcrPull RBAC (deferida a Q3).

---

## 2. Por qué NO dejamos los packages public

| Razón | Detalle |
|---|---|
| **Política org Umbral-Bot** | Los packages container son artefactos internos. Hacerlos públicos los expone a scraping sin valor comercial agregado. |
| **Trazabilidad de pulls** | GHCR provee analytics de pull cuando son privados (con scope `read:packages`). Públicos = anonymous pulls sin métricas. |
| **Coste cero adicional** | Mantenerlos privados no agrega coste vs públicos en el plan org actual. |
| **Defensa en profundidad** | Si una imagen contiene config secrets accidentales (URLs internas, tags de modelo), público amplifica el blast radius. |
| **Reversibilidad fácil** | Pasar de privado → público es trivial; al revés requiere rotación de PATs y revisar quién pulleó la imagen. |

---

## 3. Resultado Fase 1 — Preflight (PASS)

Validado en sesión 2026-05-15 (evidencia: `C:\GitHub\.coord-ag-evidence\053-cvia3-preflight-2026-05-15\`):

| Check | Resultado |
|---|---|
| Azure subscription + RG accesibles | ✅ `f14f61f0-…`, `rg-umbral-agents-prod`, eastus2 |
| KV `kv-umbral-agents-prod` existe | ✅ RBAC mode, soft-delete 90d, **purge protection ON** |
| Roles del principal `dm@umbralbim.cl` | ✅ Owner sub + Key Vault Administrator KV |
| 3 packages confirmados privados | ✅ HTTP 401 anonymous a `ghcr.io/v2/.../manifests/v1` |
| Org policy permite PAT classic | ✅ Sin approval workflow |
| Bicep modules aceptan `@secure() param ghcrPat` | ✅ 3 módulos + umbrella ya cableados |

---

## 4. Resultado Fase 2 — PAT en Key Vault (PASS con incidente recuperado)

Validado en sesión 2026-05-15 (evidencia: `C:\GitHub\.coord-ag-evidence\053-cvia3-pat-set-2026-05-15\`).

### 4.1 Resultado final
- Secret `ghcr-pat` cargado en `kv-umbral-agents-prod`.
- Active version: `d80f56…cdd0a`.
- Length: 40 chars (PAT classic estándar).
- ContentType: `GHCR PAT classic, scope read:packages, for ACA Jobs aeco-kb pipeline`.
- Expires: `2026-08-13T13:53:15Z` (90 días).
- Enabled: true.
- GHCR auth validada: 3/3 packages privados → HTTP 200 con `Bearer base64(PAT)`.

### 4.2 Incidente y recuperación

**Incidente**: en el primer intento de carga, el PAT v1 fue pasted en una pwsh shell errónea (no la del `Read-Host`) y ejecutado como comando, exponiéndose en `Last Command` y PSReadLine history.

**Mitigación inmediata**:
1. PAT v1 revocado en GitHub UI (mismo segundo).
2. PSReadLine history sanitizado (regex filter `^(ghp_|github_pat_|gho_|ghs_|ghr_)`).
3. Defensive temp backup eliminado.
4. Todas las pwsh shells cerradas para flush in-memory.

**Segundo intento (garbage value)**: Read-Host recibió solo 1 char visible (clipboard issue). KV quedó con secret de 1 char (version `8fe444…c7ba`). PAT NO expuesto en GitHub (solo 1 char entró al proceso).

**Recuperación con length guard**:
- Generado PAT v2.
- Validado externamente en Notepad (40 chars, prefix `ghp_`).
- KV secret recuperado de soft-delete (`az keyvault secret recover`).
- Nuevo `az keyvault secret set` con guard `if ($patLen -lt 30) ABORT` antes del CLI call.
- Resultado: nueva version `d80f56…cdd0a` con 40 chars válidos.

### 4.3 Hallazgo técnico clave

GHCR token endpoint (`/token?service=ghcr.io&scope=...`) NO valida Basic Auth standard como otros registries. Para autenticación desde scripts/curl el método correcto es:

```
Authorization: Bearer <base64(PAT)>
```

Validado: HTTP 200 a `/v2/.../manifests/v1` con este esquema. Variantes que NO funcionan:
- `Authorization: Basic <base64(user:pat)>` directo al manifest endpoint.
- `Authorization: Bearer <PAT raw>`.
- `Authorization: token <PAT>` (esto solo aplica a `api.github.com`).

Para ACA + `registries[].passwordSecretRef`, el runtime de containerd implementa el flow estándar internamente — **no requiere cambios en el bicep** ni un username específico (GHCR no valida el username, solo el PAT).

---

## 5. Diseño técnico C-Vía 3

### 5.1 Flujo end-to-end

```
GitHub UI  ─generate PAT classic─►  pwsh local
                                        │
                                        │ az keyvault secret set
                                        ▼
                              Key Vault (kv-umbral-agents-prod)
                                        │
                                        │ az deployment group create
                                        │  -p ghcrPat=$(az kv secret show ...)
                                        ▼
                              ACA Jobs (Microsoft.App/jobs)
                              configuration.secrets[name=ghcr-pat]
                              configuration.registries[server=ghcr.io,
                                                       passwordSecretRef=ghcr-pat]
                                        │
                                        │ pull on first run
                                        ▼
                              ghcr.io/umbral-bot/aeco-*:v1
```

### 5.2 Por qué KV (no env var, no bicep param hardcoded)

- **Rotación**: cambiar el secret en KV no requiere rebuild de la imagen ni edición del repo.
- **Audit**: KV diagnostic settings registran cada `secret show` (quién, cuándo, desde qué IP).
- **RBAC scope**: solo principals con `Key Vault Secrets User` pueden leerlo.
- **Soft-delete + purge protection**: ventana de 90d para recuperación.
- **No persistencia en disco/repo**: el script lo pasa inline al `az deployment` y limpia variables al final.

### 5.3 Por qué pasarlo como `@secure() param` en bicep

- Azure Resource Manager redacta el valor en logs y en el deployment history.
- El What-If FullResourcePayloads NO imprime `@secure()` params como plain text (validado).
- El secret queda inline en el ACA Job `configuration.secrets[]` — nunca expuesto via API.

### 5.4 Componentes nuevos en el repo (este PR)

| Path | Tipo | Propósito |
|---|---|---|
| `scripts/deploy/deploy-aeco-kb-pipeline.ps1` | Script | Orquestador what-if + deploy con confirmación |
| `runbooks/aeco-kb-pipeline-deploy.md` | Doc | Procedimiento operativo + rotación PAT |
| `docs/audits/2026-05-15-c-via-3-private-ghcr-pat-design.md` | Doc | Este archivo |
| `infra/azure/aeco-kb-pipeline.bicep` | Bicep | +1 param `deployPdfParser bool = false` |
| `infra/azure/modules/aeco-pdf-parser-job.bicep` | Bicep | Comentario actualizado (privado, no público) |

---

## 6. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| PAT expira sin rotar (90 días) | Media | ACA Jobs fallan al pull | Calendar reminder + KV secret expiry alert (Q3) |
| PAT se filtra por accidente (chat, log, commit) | Baja-Media | Lectura no autorizada de packages privados | Length guard + `@secure()` + cleanup variables + revisión de logs |
| Org Umbral-Bot deshabilita PAT classic | Baja | Auth deja de funcionar | Migrar a fine-grained PAT o ACR (C-Vía 2) |
| KV inaccesible (region outage) | Baja | Deploy bloqueado | KV es regional; usar SLA de Azure (no cross-region replica para secrets) |
| Bicep `@secure()` log leak | Muy baja | PAT en deployment history | Validar redacción en `az deployment group show --query properties` |
| Terminal handshake mal ejecutado en rotación | Media (humano) | PAT pegado en shell errónea | Protocolo terminal handshake + length guard documentados en runbook |

---

## 7. Rollback

### 7.1 Si C-Vía 3 falla post-deploy

| Síntoma | Acción |
|---|---|
| Job falla con `ImagePullBackOff` o equivalente ACA | Verificar `ghcr-pat` en KV, smoke GHCR, re-deploy si rotó |
| KV secret corrupto | Recover from soft-delete + nueva version (sección 2.3 del runbook) |
| ACA Job creado pero mal configurado | Re-deploy con bicep idempotente o `az containerapp job delete` |

### 7.2 Si decidimos abandonar C-Vía 3

| Destino | Pasos |
|---|---|
| C-Vía 1 (público) | Cambiar visibility en GHCR UI; remover `secrets`/`registries` del bicep; redeploy. |
| C-Vía 2 (ACR + UAMI) | Build + push images a ACR; ajustar `image:` en bicep modules; eliminar `secrets`/`registries`/`@secure() param`; UAMI ya tiene AcrPull. |

---

## 8. Próximos pasos

| Paso | Owner | Cuándo |
|---|---|---|
| Merge de este PR (con what-if PASS) | David | Tras review |
| Deploy real `-WhatIfOnly:$false` | David autoriza, Copilot ejecuta | Post-merge |
| Post-deploy: smoke `bash scripts/aeco-kb/run_pipeline.sh` | Copilot-VPS | Tras deploy |
| Calendar reminder rotación PAT (T-14d antes de 2026-08-13) | David | Programar ahora |
| Eval C-Vía 2 (ACR migration) | Plataforma | Q3 2026 |
| KV secret expiry alert via Action Group | Plataforma | Q3 2026 |

---

## 9. Evidencia

- `C:\GitHub\.coord-ag-evidence\053-cvia3-preflight-2026-05-15\` — 13 archivos Fase 1 (read-only).
- `C:\GitHub\.coord-ag-evidence\053-cvia3-pat-set-2026-05-15\01-kv-secret-attributes.json` — metadata KV final.
- `C:\GitHub\.coord-ag-evidence\053-cvia3-pat-set-2026-05-15\02-ghcr-auth-test.txt` — smoke 3 packages × HTTP 200.
- PR draft (este): `copilot/feat-c-via-3-private-ghcr-deploy-script` → main.

---

## 10. Autorizaciones registradas

| Fase | Autorización David | Fecha |
|---|---|---|
| Fase 1 (preflight read-only) | Sí | 2026-05-15 |
| Fase 2 (KV secret create) | Sí | 2026-05-15 |
| Fase 3 (script + runbook + audit + PR draft + what-if) | Sí | 2026-05-15 |
| Fase 3.1 (resolver drift de smoke residual antes de PR ready) | Sí | 2026-05-15 |
| Fase 4 (deploy real) | **PENDIENTE** | — |

---

## 11. Resolución de drift (Fase 3.1)

What-if inicial reveló 2 Modify a recursos existentes. Investigación read-only clasificó cada uno antes de tocar bicep:

### 11.1 `aeco-source-crawler` env vars `SOURCE_TYPE` + `MAX_DOCS`

**Clasificación**: runtime override, NO config base.

**Evidencia**:
- `scripts/aeco-kb/run_pipeline.sh` los pasa como `--args --source-type "$src"` (NO como `--env-vars`).
- `scripts/aeco-kb/source_crawler.py` línea 320: `--max-docs` flag con `default=int(os.environ.get("MAX_DOCS", "100"))`.
- `infra/azure/modules/aeco-source-crawler-job.bicep` línea 97 (pre-existente): comentario explícito `// Override per-invocation: SOURCE_TYPE, MAX_DOCS`.
- `MAX_DOCS=1` no aparece en ningún commit del repo — confirma que es smoke residual aplicado vía `az containerapp job update --set-env-vars` post-deploy.
- Task 048 (`2026-05-08-048`) lista `SOURCE_TYPE=buildingsmart` + `MAX_DOCS=30` como ejemplo de **invocación** (`job start --env-vars`), no como deploy spec.

**Decisión**: NO agregar al bicep. El re-deploy las limpiará — esto es **intencional** y restaura idempotencia. Las invocaciones reales pasarán SOURCE_TYPE/MAX_DOCS por `job start --env-vars` o `--args`.

### 11.2 `aeco-source-crawler` image tag `:latest` vs `o16.2-2e66dda`

**Clasificación**: pin inmutable intencional.

**Evidencia**:
- Commit `cd9f225b` (2026-05-10) task `coord-ag-2a-build-push-aeco-source-crawler-pinned` build+push del tag con flag `do_not_merge: true` y digest `sha256:ce04d7f5d8a96a82c9a7197394c86e60146350e21408b4eed03f868c2cbfeedc`.
- Task indica explícitamente: `LATEST_TOCADO: NO`, `V1_TOCADO: NO`. El tag es pin de trazabilidad O16.2.
- Update runtime aplicado por David: `az containerapp job update --image ghcr.io/umbral-bot/aeco-source-crawler:o16.2-2e66dda`.

**Decisión**: cambiar default del param `image` en `aeco-source-crawler-job.bicep` a `ghcr.io/umbral-bot/aeco-source-crawler:o16.2-2e66dda`. Ahora bicep es la fuente de verdad del pin; futuros pins se hacen via PR (no via `--image` manual).

### 11.3 `workloadProfileName: 'Consumption'` en los 3 jobs

**Clasificación**: ruido what-if (ARM lo agrega por default en CAE Consumption-only).

**Decisión**: declarar explícitamente `workloadProfileName: 'Consumption'` en los 3 módulos de jobs. Sin cambio funcional; elimina noise del what-if y hace el bicep self-documenting.

### 11.4 What-if post-fix

```
~ Microsoft.App/jobs/aeco-source-crawler [2024-03-01]
    ~ properties.template.containers: [
      ~ 0:
        ~ env: [
          - 3: { name: "SOURCE_TYPE", value: "buildingsmart" }
          - 4: { name: "MAX_DOCS",    value: "1"           }
        ]
      ]

= Microsoft.App/jobs/aeco-index-pipeline
* Microsoft.App/jobs/aeco-pdf-parser  (Ignore — deployPdfParser=false)
... 13 Ignore total
```

**Resultado**: 1 Modify (intencional, documentado), 1 NoChange, 13 Ignore, 0 Delete, 0 Create. Stop conditions: PASS.
