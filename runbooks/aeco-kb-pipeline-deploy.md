# Runbook — AECO KB Pipeline Deploy

**Owner**: Plataforma Umbral · **Última actualización**: 2026-05-15 · **Sub-task**: O16.2/053 (C-Vía 3)

Operacionaliza el deploy del pipeline AECO KB (3 ACA Jobs en `rg-umbral-agents-prod`) usando imágenes privadas en GHCR (`ghcr.io/umbral-bot/aeco-*`) con el PAT clásico almacenado en Key Vault `kv-umbral-agents-prod` como secret `ghcr-pat`.

---

## 1. Pre-requisitos

### 1.1 Tooling local
- Azure CLI ≥ 2.83 (`az --version`).
- PowerShell 7.x (`$PSVersionTable.PSVersion`).
- Acceso al repo `umbral-agent-stack` (rama `main` o feature branch derivada).

### 1.2 Permisos Azure (principal autenticado con `az login`)
| Scope | Rol mínimo |
|---|---|
| Subscription `f14f61f0-…` | Reader |
| RG `rg-umbral-agents-prod` | Contributor (para deploy) o Reader (para what-if) |
| Key Vault `kv-umbral-agents-prod` | Key Vault Secrets User |

### 1.3 Recursos Azure pre-existentes (validados por el script)
- UAMI con prefix `uami-umbral-agents` en el RG.
- Container Apps Environment (auto-discovered por nombre).
- Storage account `stumbralagentsprod`.
- AI Search service `srch-umbral-kb-prod`.
- Document Intelligence (FormRecognizer) en el RG.
- Key Vault `kv-umbral-agents-prod` con secret `ghcr-pat` enabled.

### 1.4 Imágenes container disponibles en GHCR (privadas)
- `ghcr.io/umbral-bot/aeco-source-crawler:v1` (o `:latest`)
- `ghcr.io/umbral-bot/aeco-pdf-parser:v1`
- `ghcr.io/umbral-bot/aeco-index-pipeline:v1`

---

## 2. Key Vault secret `ghcr-pat`

### 2.1 Atributos esperados
- **Nombre**: `ghcr-pat`
- **ContentType**: `GHCR PAT classic, scope read:packages, for ACA Jobs aeco-kb pipeline`
- **Expires**: T + 90 días desde la creación
- **Enabled**: true
- **Length**: ≥ 30 chars (PAT classic = 40 chars)

### 2.2 Verificar metadata sin revelar el valor
```powershell
az keyvault secret show `
  --vault-name kv-umbral-agents-prod `
  --name ghcr-pat `
  --query "{enabled:attributes.enabled, expires:attributes.expires, contentType:contentType}" `
  -o json
```

### 2.3 Cómo rotar el PAT (cada 90 días o ante incidente)

1. **Generar nuevo PAT classic** en GitHub (UI): Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (classic).
   - **Note**: `ghcr-pat-aca-aeco-kb-YYYYMMDD`
   - **Expiration**: 90 days
   - **Scope mínimo**: `read:packages`
   - **No marcar otros scopes**.

2. **Validar longitud externa** (Notepad u otro editor): debe ser exactamente 40 chars y empezar con `ghp_`.

3. **Cargar en Key Vault** (Read-Host con length guard):
   ```powershell
   $sec = Read-Host -AsSecureString -Prompt "Pega el GHCR PAT (oculto)"
   $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
   $plain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
   [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
   if ($plain.Length -lt 30) { Write-Host "ABORT: length $($plain.Length)"; return }
   $expiry = (Get-Date).AddDays(90).ToString("yyyy-MM-ddTHH:mm:ssZ")
   az keyvault secret set `
     --vault-name kv-umbral-agents-prod `
     --name ghcr-pat `
     --value $plain `
     --expires $expiry `
     --content-type "GHCR PAT classic, scope read:packages, for ACA Jobs aeco-kb pipeline" `
     --output none
   $plain = $null; Remove-Variable plain, sec, bstr -ErrorAction SilentlyContinue
   [GC]::Collect()
   ```

4. **Si el secret está soft-deleted** (purge protection ON):
   ```powershell
   az keyvault secret recover --vault-name kv-umbral-agents-prod --name ghcr-pat
   Start-Sleep -Seconds 15  # esperar a que la operación se propague
   # luego ejecutar el `az keyvault secret set` del paso 3
   ```

5. **Smoke GHCR auth** (sin imprimir el PAT):
   ```powershell
   $pat = az keyvault secret show --vault-name kv-umbral-agents-prod --name ghcr-pat --query value -o tsv
   $b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($pat))
   $r = Invoke-WebRequest -Uri "https://ghcr.io/v2/umbral-bot/aeco-source-crawler/manifests/v1" `
                          -Headers @{Authorization="Bearer $b64"; Accept='application/vnd.oci.image.manifest.v1+json'} `
                          -SkipHttpErrorCheck
   Write-Host "GHCR HTTP: $($r.StatusCode)"  # esperado: 200
   $pat = $null; $b64 = $null; Remove-Variable pat, b64 -ErrorAction SilentlyContinue
   [GC]::Collect()
   ```

6. **Revocar el PAT viejo** en GitHub UI (mismo Settings → Tokens classic → Delete).

7. **NO** pushear commits con scripts/notes que contengan el PAT. Limpiar PSReadLine history si se pegó por accidente:
   ```powershell
   Clear-History
   $h = (Get-PSReadLineOption).HistorySavePath
   $clean = Get-Content $h | Where-Object { $_ -notmatch '^(ghp_|github_pat_|gho_|ghs_|ghr_)' }
   Set-Content -Path $h -Value $clean -Encoding UTF8
   ```

---

## 3. What-if (read-only, seguro)

```powershell
cd C:\GitHub\umbral-agent-stack
.\scripts\deploy\deploy-aeco-kb-pipeline.ps1
```

Comportamiento:
- Resuelve params Azure (read-only).
- Lee `ghcr-pat` de KV (sin imprimir).
- Smoke GHCR auth (1 manifest, espera HTTP 200).
- Ejecuta `az deployment group what-if` con `--result-format FullResourcePayloads`.
- Termina sin deploy.

Inspeccionar el what-if:
- **Esperado**: `Create` para `Microsoft.App/jobs` (`aeco-source-crawler` + `aeco-index-pipeline`; `aeco-pdf-parser` solo si `-DeployPdfParser`).
- **Esperado**: NO `Delete` ni `Modify` sobre recursos pre-existentes.
- **STOP** si aparece `Delete` o `Modify` no anticipado.

### What-if con pdf-parser incluido
```powershell
.\scripts\deploy\deploy-aeco-kb-pipeline.ps1 -DeployPdfParser:$true
```

---

## 4. Deploy real (sólo con autorización explícita)

**Pre-requisito**: David autorizó el deploy en este momento concreto.

```powershell
.\scripts\deploy\deploy-aeco-kb-pipeline.ps1 -WhatIfOnly:$false
```

El script:
1. Re-ejecuta what-if.
2. Pide confirmación interactiva: escribir literalmente `DEPLOY` (mayúsculas).
3. Si la palabra coincide, ejecuta `az deployment group create`.
4. Si no, aborta sin tocar Azure.
5. Limpia el PAT de memoria al final (try/finally).

### Deploy con pdf-parser
```powershell
.\scripts\deploy\deploy-aeco-kb-pipeline.ps1 -WhatIfOnly:$false -DeployPdfParser:$true
```

---

## 5. Rollback

### 5.1 Si un job se creó pero está mal configurado
```powershell
# Opción A: re-deploy con bicep corregido (idempotente)
.\scripts\deploy\deploy-aeco-kb-pipeline.ps1 -WhatIfOnly:$false

# Opción B: borrar el job individualmente
az containerapp job delete `
  --resource-group rg-umbral-agents-prod `
  --name aeco-source-crawler `
  --yes
```

### 5.2 Si el PAT en KV es inválido
- Rotar (sección 2.3) y re-ejecutar what-if.
- ACA Jobs pre-existentes seguirán fallando al iniciar replica hasta que se redeploye con el nuevo PAT (porque el secret va inline en el job).

### 5.3 Si la imagen GHCR no existe (404 en pull)
- Verificar tag con: `gh api /orgs/Umbral-Bot/packages/container/<pkg>/versions`.
- Re-build + push de la imagen desde el repo de origen.
- No requiere re-deploy del job (el pull es runtime, no deploy-time).

---

## 6. Restricciones operativas

| Acción | Permitida sin autorización | Requiere autorización explícita |
|---|---|---|
| `az ... show / list` (read) | ✅ | — |
| Leer `ghcr-pat` de KV | ✅ (script lo hace en memoria) | — |
| Imprimir el PAT en stdout/log | ❌ NUNCA | — |
| Imprimir Authorization header | ❌ NUNCA | — |
| Commitear el PAT a git | ❌ NUNCA | — |
| `az deployment group what-if` | ✅ | — |
| `az deployment group create` | — | ✅ David |
| `az containerapp job start` | — | ✅ David (operación runtime) |
| Modificar/borrar recursos existentes | — | ✅ David + plan documentado |
| Editar bicep modules | — | ✅ via PR review |

### 6.1 Anti-patrones bloqueados
- Hardcodear el PAT en el bicep (debe venir como `@secure() param`).
- Pasar el PAT como variable de entorno persistente (`$env:GHCR_PAT`) — usar solo memoria de la sesión PS y limpiar al final.
- Usar el secret `ghcr-pat` para un scope distinto de `read:packages` (rotar a un PAT distinto si se necesita write).
- Compartir el PAT entre humanos / chats / Notion / mailbox de agentes.
- Aplicar parámetros runtime (`SOURCE_TYPE`, `MAX_DOCS`, fechas, etc.) con `az containerapp job update --set-env-vars` — eso crea drift bicep ↔ runtime que reaparece como Modify en cada what-if. **Siempre** pasarlos por invocación: `az containerapp job start --env-vars KEY=value` o vía `--args` (ver `scripts/aeco-kb/run_pipeline.sh`).
- Cambiar el `image` de un job con `containerapp job update --image` sin actualizar el bicep en la misma PR — si el pin es intencional, debe quedar como default del param `image` en `infra/azure/modules/aeco-source-crawler-job.bicep` (ver Fase 3.1 del audit doc).

---

## 7. Próximos pasos (Q3+)

- **Migrar GHCR → ACR** (`crumbralagentsprod.azurecr.io`): elimina la dependencia del PAT (UAMI + AcrPull RBAC).
- **CI/CD push a ACR** desde GitHub Actions con federated credentials (sin secrets de larga duración).
- **Service Bus + KEDA event-driven** para encadenar los 3 jobs (reemplaza `scripts/aeco-kb/run_pipeline.sh`).
- **Continuous monitoring** del KV secret expiry → alertar 14 días antes del vencimiento.

---

## 8. Referencias

- Audit doc: [docs/audits/2026-05-15-c-via-3-private-ghcr-pat-design.md](../docs/audits/2026-05-15-c-via-3-private-ghcr-pat-design.md)
- Script: [scripts/deploy/deploy-aeco-kb-pipeline.ps1](../scripts/deploy/deploy-aeco-kb-pipeline.ps1)
- Bicep umbrella: [infra/azure/aeco-kb-pipeline.bicep](../infra/azure/aeco-kb-pipeline.bicep)
- Modules: [infra/azure/modules/aeco-*-job.bicep](../infra/azure/modules/)
