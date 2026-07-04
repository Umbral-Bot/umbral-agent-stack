# Auditoría — Higiene de `models.json` per-agent OpenClaw (post política Azure-only)

- **Fecha:** 2026-07-04
- **Superficie:** VPS (`srv1431451`, usuario `rick`), runtime OpenClaw `~/.openclaw/agents/*/agent/models.json`
- **Autorización:** David — "AUTORIZADO David: limpiar runtime + doc en repo + PR (sin secretos en git)"
- **Skill aplicada:** `.agents/skills/openclaw-vps-operator/SKILL.md` (preflight, backup, patch, validación, smoke)
- **Veredicto:** `OPENCLAW_MODELS_HYGIENE=YES` — 2 agents parcheados, 4 campos de secreto eliminados, smoke PASS, sin restart de gateway.

## Problema

Dos agents conservaban snapshots per-agent de `models.json` (fechados 23–24 abril) con un
bloque completo del provider `azure-openai-responses` que incluía:

1. **API key embebida en el JSON** — anti-patrón. El secreto aparecía en **dos campos**
   (`apiKey` y `headers.api-key`) por archivo, en texto plano en disco durante ~2.5 meses.
2. **Catálogo Azure retirado** — snapshots de `gpt-4.1`, `gpt-5.2-chat`, `kimi-k2.5`,
   `gpt-5.4-pro` (todos eliminados del catálogo global en el Track B) y **sin** `gpt-5.5`
   (el primary vigente).
3. **baseUrl obsoleta** — host `*.cognitiveservices.azure.com`, corregido globalmente a
   `*.openai.azure.com` en junio (bug de `store` en openai-responses).

Agents afectados:

| Agent | Archivo | Estado previo |
|---|---|---|
| `rick-communication-director` | `~/.openclaw/agents/rick-communication-director/agent/models.json` | 2771 B, snapshot Apr 23, 2 campos secreto, 5 modelos retirados |
| `rick-linkedin-writer` | `~/.openclaw/agents/rick-linkedin-writer/agent/models.json` | 2771 B, snapshot Apr 24, 2 campos secreto, 5 modelos retirados |

Los otros 6 agents (`main`, `rick-delivery`, `rick-ops`, `rick-orchestrator`, `rick-qa`,
`rick-tracker`) ya tenían el stub estándar limpio (274 B: solo stubs `github-copilot` +
`openai-codex` con `models: []`, sin secretos).

## Política

- **Auth vive solo en la config global del provider** (`~/.openclaw/openclaw.json` →
  `models.providers.azure-openai-responses`) y en `~/.config/openclaw/env`. Nunca
  embebida en archivos per-agent.
- **Selección de modelo per-agent** (`primary` + `fallbacks`) vive en
  `agents.list[].model` de `openclaw.json` — **no** en `models.json` per-agent — y quedó
  alineada Azure-only el 2026-07-04: primary `azure-openai-responses/gpt-5.5`, fallback
  único `azure-openai-responses/gpt-5.4`.
- Por lo tanto el `models.json` per-agent correcto es el **stub estándar sin bloque
  azure**: el runtime resuelve el provider desde la config global.

## Acción aplicada (runtime VPS, 2026-07-04 ~15:00 -04:00)

1. **Backup** de ambos archivos → `*.bak-models-hygiene-20260704` (junto al original).
2. **Inventario** de los 8 `models.json` con scanner Python (solo rutas/longitudes,
   nunca valores): 2 archivos con `SECRET_FIELD`, 0 refs `openai/`·`google/` en los 8.
3. **Patch**: eliminación del bloque `providers.azure-openai-responses` completo en los
   2 archivos con drift (escritura atómica, permisos `600`). Resultado: ambos idénticos
   al stub estándar de 274 B.
4. **Validación**: los 8 archivos JSON válidos, 0 campos de secreto, 0 refs prohibidas;
   `openclaw.json` global JSON válido; gateway `active` **sin restart** (config global
   no cambió).
5. **Smoke**: `openclaw agent --agent rick-orchestrator --message "Responde solo:
   MODELS_HYGIENE_OK"` → **PASS** (`MODELS_HYGIENE_OK`). Los primeros intentos dieron
   429 de Azure; journal confirmó 36 ocurrencias de rate-limit en las 2 h **previas** al
   patch (preexistente, no regresión) y **0 errores de auth** post-patch. La cadena de
   failover registrada pide exactamente `gpt-5.5 → gpt-5.4` azure-only.

### Before / after (solo counts, sin valores)

| Métrica | Before | After |
|---|---|---|
| Agents con `models.json` con drift | 2 | 0 |
| Campos de secreto embebidos (total) | 4 (2 × `apiKey` + 2 × `headers.api-key`) | 0 |
| Snapshots de modelos retirados (total) | 10 (5 × 2 archivos) | 0 |
| Refs `openai/` · `google/` en los 8 archivos | 0 | 0 |
| Errores de auth en journal post-patch | — | 0 |

## Recomendación de seguridad (follow-up)

La API key embebida correspondía al recurso Azure con host `cognitiveservices` y estuvo
en texto plano en disco desde abril. Aunque ya no existe en runtime, se recomienda
**rotar esa key en Azure Portal** (superficie Copilot Windows, autorización de David)
por higiene. Los backups `*.bak-models-hygiene-*` la conservan (permisos `600`, solo
lectura local de `rick`); purgar los backups tras confirmar estabilidad + rotación.

## Rollback

```bash
# Restaurar snapshot previo (por agent):
cp ~/.openclaw/agents/rick-communication-director/agent/models.json.bak-models-hygiene-20260704 \
   ~/.openclaw/agents/rick-communication-director/agent/models.json
cp ~/.openclaw/agents/rick-linkedin-writer/agent/models.json.bak-models-hygiene-20260704 \
   ~/.openclaw/agents/rick-linkedin-writer/agent/models.json
# No requiere restart de gateway (archivos leídos por sesión de agent).
```

## Referencias

- Track B (catálogo global + aliases): evidencia VPS
  `~/.coord-ag-evidence/openclaw-catalog-cleanup-2026-07-04.md`
  (backup `~/.openclaw/openclaw.json.bak-catalog-cleanup-20260704`).
- Política Azure-only (defaults + 8 agents): evidencia VPS
  `~/.coord-ag-evidence/openclaw-azure-only-policy-2026-07-04.md`
  (backup `~/.openclaw/openclaw.json.bak-azure-only-20260704`).
- Auditoría Azure Foundry del deployment vigente:
  [`foundry-gpt-5.5-audit-20260606.md`](./foundry-gpt-5.5-audit-20260606.md).
- Activación alias gpt-5.5:
  [`openclaw-gpt-5.5-alias-activation-20260606.md`](./openclaw-gpt-5.5-alias-activation-20260606.md).
- Evidencia de esta ejecución (VPS):
  `~/.coord-ag-evidence/openclaw-models-hygiene-2026-07-04.md`.
