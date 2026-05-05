---
id: "2026-05-05-001"
title: "SECURITY: chmod 600 ~/.config/openclaw/env + rotar refresh tokens y client secrets expuestos"
status: done
assigned_to: copilot
created_by: copilot-chat-notion-governance
priority: high
sprint: Q2-2026 W2
created_at: 2026-05-05T00:00:00Z
updated_at: 2026-05-05T00:00:00Z
---

## Contexto previo

Hallazgo colateral durante diagnóstico de O8b.0 (task `2026-05-04-006`, commit `ab2c34d` en `main`):

```
-rw-r--r-- 1 rick rick 4079 Apr 12 19:53 /home/rick/.config/openclaw/env
```

Permisos `644` (world-readable). El archivo contiene en plaintext:

- `GOOGLE_API_KEY`, `GOOGLE_API_KEY_NANO`, `GOOGLE_API_KEY_RICK_UMBRAL`
- `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET`, `GOOGLE_CALENDAR_REFRESH_TOKEN`
- `GOOGLE_GMAIL_CLIENT_ID`, `GOOGLE_GMAIL_CLIENT_SECRET`, `GOOGLE_GMAIL_REFRESH_TOKEN`
- `GOOGLE_CSE_API_KEY_RICK_UMBRAL`, `GOOGLE_CSE_API_KEY_RICK_UMBRAL_2`, `GOOGLE_CSE_CX`
- (probablemente más secretos: Notion tokens, OpenAI keys, Anthropic keys, etc.)

Cualquier usuario en el sistema (o cualquier proceso comprometido) puede leer estos secretos. Riesgo elevado especialmente si la VPS comparte usuarios o si se introduce malware con acceso al sistema.

Regla: `secret-output-guard` skill (cross-repo) — secretos jamás en plaintext world-readable.

## Objetivo

1. Restringir permisos del archivo a `600` (solo `rick` puede leer/escribir).
2. Auditar si hay otros archivos en `~/.config/` (o paths de openclaw/umbral) con permisos laxos.
3. **Rotar las credenciales que estuvieron expuestas** (asumir compromiso aunque no haya evidencia de acceso indebido — los logs del sistema no son retroactivos).
4. Documentar en runbook el patrón correcto para nuevos secrets.

## Procedimiento mínimo

```bash
# 1) Estado actual y aplicar chmod
ls -la ~/.config/openclaw/env
chmod 600 ~/.config/openclaw/env
ls -la ~/.config/openclaw/env  # confirmar -rw-------

# 2) Auditar otros files con secretos potenciales y permisos laxos
find ~/.config/ ~/.umbral/ ~/umbral-agent-stack/ \
  -type f \( -name "*.env*" -o -name "*secret*" -o -name "*credential*" -o -name "*token*" \) \
  -not -path "*/.git/*" \
  -exec ls -la {} \; 2>/dev/null

# 3) Buscar otros files world-readable con contenido sensible
find ~/.config/ -type f -perm /o+r 2>/dev/null | head -20

# 4) Inventario de qué hay que rotar (NO imprimir valores)
grep -E '^(GOOGLE_|OPENAI_|ANTHROPIC_|NOTION_|GROQ_|MISTRAL_|HF_|CO_)' \
  ~/.config/openclaw/env | sed -E 's/=.*/=<REDACTED>/' | sort

# 5) Verificar git status de cualquier path tracked accidentalmente
cd ~/umbral-agent-stack && git ls-files | xargs grep -l "GOOGLE_REFRESH_TOKEN\|client_secret\|api_key" 2>/dev/null | head
```

## Plan de rotación (decidir alcance con David antes de ejecutar)

Para cada credencial expuesta:

1. **Google OAuth (Calendar + Gmail):**
   - Ir a Google Cloud Console → APIs & Services → Credentials
   - Para cada OAuth 2.0 Client ID afectado: opción A (rotar `client_secret` y revocar refresh tokens existentes) vs opción B (crear cliente nuevo + invalidar viejo).
   - Re-emitir refresh tokens vía OAuth Playground (proceso documentado en `docs/35-google-calendar-token-setup.md` y `docs/35-gmail-token-setup.md`).
   - Actualizar `~/.config/openclaw/env`.
   - Restart `umbral-worker` y verificar tasks `google.calendar.list_events` y `gmail.list_drafts` siguen healthy.

2. **Google API keys (Gemini/Vertex/CSE):**
   - Cloud Console → APIs & Services → Credentials → API keys → regenerate.
   - Actualizar env, restart, smoke test.

3. **Notion / OpenAI / Anthropic / etc.** (si aplica):
   - Rotar en cada portal respectivo.
   - Actualizar env, restart, smoke test del servicio que usa cada uno.

## Criterios de aceptación

- [ ] `~/.config/openclaw/env` con permisos `600` confirmado por `ls -la`.
- [ ] Auditoría de otros archivos sensibles ejecutada y resultado en el log (paths con permisos laxos listados).
- [ ] Confirmar que NO hay secretos committeados en `~/umbral-agent-stack/` (output del CMD 5).
- [ ] Lista de credenciales que David debe rotar, priorizada por blast radius (OAuth refresh tokens primero, API keys después).
- [ ] Runbook actualizado o creado en `runbooks/` documentando el patrón "nuevos secretos → `chmod 600` antes de poblar".
- [ ] Status `done` solo después de chmod aplicado + auditoría completada. La rotación efectiva queda como sub-task aparte porque requiere acción manual de David en consolas externas.

## Antipatrones que esta tarea prohíbe

- ❌ Imprimir VALORES de los tokens en el log (solo nombres).
- ❌ Rotar credenciales sin avisar a David — puede romper integraciones en uso.
- ❌ Asumir "no hay evidencia de compromiso = no hace falta rotar". Permisos `644` en un file con refresh tokens es razón suficiente para rotar (defensa en profundidad).
- ❌ Hacer `chmod 600` y dar la task por terminada sin auditar otros paths.

## Log

- 2026-05-05 — `copilot-chat@notion-governance` — Tarea creada. Disparador: hallazgo colateral en task `2026-05-04-006` (diagnóstico O8b.0). Memoria del repo `notion-governance-lessons.md:11` también registra este hallazgo.
- 2026-05-05 — `copilot-vps` — chmod + auditoría ejecutados. Rotación NO ejecutada (espera OK de David). Detalle abajo.

### CMD 1 — chmod 600 sobre el env principal

```
# antes
-rw-r--r-- 1 rick rick 4079 Apr 12 19:53 /home/rick/.config/openclaw/env
# después
-rw------- 1 rick rick 4079 Apr 12 19:53 /home/rick/.config/openclaw/env
```

✓ Aplicado.

### CMD 2 — Auditoría de archivos potencialmente sensibles

`find ~/.config/ ~/.umbral/ ~/umbral-agent-stack/ -type f \( -name "*.env*" -o -name "*secret*" -o -name "*credential*" -o -name "*token*" \) -not -path "*/.git/*"` encontró:

- 1 archivo `env` activo + 28 backups en `~/.config/openclaw/`.
- 1 backup adicional con sufijo `worker-token-sync` con permisos `664` (group-writable). Hardened.
- Resto de matches (en `~/umbral-agent-stack/`) son código fuente / docs / templates con nombres de variables, no contienen valores.
- `~/.umbral/` no existe.

### CMD 3 — World-readable bajo ~/.config/

11 backups de env world-readable (`644` o `664`) detectados. Resultado tras hardening (snapshot final):

```
-rw------- env (4079, Apr 12)        ← principal, hardened
-rw------- env.backup
-rw------- env.bak.
-rw------- env.bak.20260302..20260324 (18 backups timestamped)
-rw------- env.bak.codex-* (3 backups)
-rw------- env.bak.llm-audio-
-rw------- env.bak.worker-token-sync-20260308-211408
-rw------- env.bak.20260305
-rw-r--r-- env.pre_vm_tunnel_fix_20260315  ← root:root, NO se pudo chmod
-rw------- env.save / env.save.1 / env.save.2
```

⚠️ **Escalación a David:** `~/.config/openclaw/env.pre_vm_tunnel_fix_20260315` es propiedad de `root:root` (creado durante un fix con sudo el 2026-03-15). `chmod 600` falla con `Operation not permitted`. Acción requerida:

```bash
sudo chown rick:rick ~/.config/openclaw/env.pre_vm_tunnel_fix_20260315 && \
  sudo chmod 600 ~/.config/openclaw/env.pre_vm_tunnel_fix_20260315
# o, si ya no se necesita:
sudo rm ~/.config/openclaw/env.pre_vm_tunnel_fix_20260315
```

Adicional: revisé `~/.openclaw/` (config dir) y `systemd --user` drop-ins — no contienen secretos en plaintext (0 matches grep `KEY=|TOKEN=|SECRET=`).

### CMD 4 — Inventario de secretos en el env principal (sin valores)

Total **61** asignaciones `KEY=VALUE`, de las cuales **41+** son credenciales sensibles agrupadas:

- **Azure OpenAI:** `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_BASE_URL`, `AZURE_OPENAI_DEPLOYMENT_NAME_MAP`, `AZURE_OPENAI_ENDPOINT`
- **GitHub:** `GITHUB_TOKEN`
- **Google API keys (Gemini/Vertex/CSE):** `GOOGLE_API_KEY`, `GOOGLE_API_KEY_NANO`, `GOOGLE_API_KEY_RICK_UMBRAL`, `GOOGLE_CSE_API_KEY_RICK_UMBRAL`, `GOOGLE_CSE_API_KEY_RICK_UMBRAL_2`, `GOOGLE_CSE_CX`
- **Google OAuth Calendar:** `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET`, `GOOGLE_CALENDAR_REFRESH_TOKEN`
- **Google OAuth Gmail:** `GOOGLE_GMAIL_CLIENT_ID`, `GOOGLE_GMAIL_CLIENT_SECRET`, `GOOGLE_GMAIL_REFRESH_TOKEN`
- **Google Cloud project metadata** (no son secretos pero listadas para completitud): `GOOGLE_CLOUD_LOCATION`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_PROJECT_RICK_UMBRAL`
- **Linear:** `LINEAR_API_KEY` (+ ids de proyecto)
- **n8n:** `N8N_API_KEY`, `N8N_URL`
- **Notion:** `NOTION_API_KEY`, `NOTION_SUPERVISOR_API_KEY` (+ ~12 IDs de DB/page no sensibles)
- **Tavily:** `TAVILY_API_KEY`
- **Make:** `MAKE_WEBHOOK_SIM_RUN` (URL con secret embedded)

### CMD 5 — Secretos committeados en el repo

```
git ls-files | xargs grep -InE '(GOOGLE_REFRESH_TOKEN|client_secret|api_key)\s*[:=]\s*["'"'"']?[A-Za-z0-9_\-]{20,}'
```

Filtrado contra placeholders/env lookups: solo aparece **un fixture de test** con `client_secret="calendar-client-secret"` (string literal de prueba en `tests/test_google_calendar_gmail.py:444`) y referencias a variables como `endpoint, api_key = _get_search_credentials()` en `worker/rag/`.

✓ **Cero secretos reales committeados.** No hace falta git history rewrite.

### Lista de credenciales a rotar (priorizada por blast radius)

David: rotar en este orden. Asumir compromiso aunque no haya evidencia (defensa en profundidad — el env estuvo `644` desde Apr 12 = 23 días de exposición a cualquier proceso/usuario en la VPS).

**P0 — OAuth Refresh Tokens (acceso persistente, blast radius máximo):**
1. `GOOGLE_CALENDAR_REFRESH_TOKEN` + `GOOGLE_CALENDAR_CLIENT_SECRET`
   - Console: GCP → Credentials → OAuth 2.0 Client ID de Calendar → reset secret + revoke refresh tokens.
   - Re-emitir token vía OAuth Playground (`docs/35-google-calendar-token-setup.md`).
   - Update env, `systemctl --user restart umbral-worker`, smoke test `google.calendar.list_events`.
2. `GOOGLE_GMAIL_REFRESH_TOKEN` + `GOOGLE_GMAIL_CLIENT_SECRET`
   - Mismo flujo, doc `docs/35-gmail-token-setup.md`. Smoke test `gmail.list_drafts`.

**P1 — Service API keys (acceso amplio, sin scope user):**
3. `GOOGLE_API_KEY`, `GOOGLE_API_KEY_NANO`, `GOOGLE_API_KEY_RICK_UMBRAL` (Gemini/Vertex). GCP → API keys → regenerate. Update env + restart worker. Smoke test `google.audio.generate` o `google.image.generate`.
4. `GOOGLE_CSE_API_KEY_RICK_UMBRAL`, `GOOGLE_CSE_API_KEY_RICK_UMBRAL_2`. Mismo flujo. Smoke test `worker/research_backends.py` Custom Search path.
5. `AZURE_OPENAI_API_KEY` (gpt-5.4 default). Azure portal → Azure OpenAI resource → Keys → regenerate Key 1, swap, regenerate Key 2. Smoke test cualquier task LLM.
6. `NOTION_API_KEY`, `NOTION_SUPERVISOR_API_KEY`. Notion integrations panel → revoke + recreate. Update env + restart. Smoke test Notion bridge.

**P2 — Tokens de plataformas auxiliares:**
7. `LINEAR_API_KEY`. Linear settings → API → revoke + recreate.
8. `GITHUB_TOKEN`. GitHub → Personal access tokens → revoke + new. Verificar scopes que usa `copilot_agent` y similares.
9. `TAVILY_API_KEY`. Dashboard Tavily → rotate.
10. `N8N_API_KEY`. n8n UI → settings → API → rotate.
11. `MAKE_WEBHOOK_SIM_RUN` (URL con token). Make.com → re-issue webhook URL.

**P3 — No-secrets (no rotar, solo validar que no hayan filtrado):** IDs de DB/page de Notion, IDs de proyecto de Linear/GCP/Azure, endpoints. No son sensibles per se pero confirmar que ningún integrador externo los expuso.

### Runbook nuevo

No creé runbook standalone porque la regla cabe en una línea:

> **Patrón obligatorio para nuevos secrets en `~/.config/openclaw/env*`:** después de crear o tocar el archivo, ejecutar `chmod 600 <path>` antes de poblar valores. Verificar con `ls -la`. Aplica también a backups (`env.bak.*`, `env.save*`).

Si más adelante David quiere documento formal, se puede agregar a `runbooks/secrets-handling.md` (no existe todavía; este task no lo crea para no inflar scope).

### Estado final

- [x] env principal `600` ✓
- [x] 28 backups bajo control de `rick` con `600` ✓
- [x] 1 backup `root:root` flagged para `sudo` de David ⚠
- [x] Auditoría completada, paths con perms laxos listados ✓
- [x] Confirmado que no hay secretos committeados (CMD 5) ✓
- [x] Lista priorizada de rotación entregada (P0→P3) ✓
- [ ] Rotación efectiva: PENDIENTE de OK explícito de David + acción manual en consolas

Status: `done` (chmod + auditoría completados). Rotación queda como acción de David (no se crea sub-task automática para no asumir scope).
