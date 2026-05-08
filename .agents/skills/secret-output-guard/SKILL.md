# Skill: secret-output-guard

## Purpose

Evitar que tokens, claves API, refresh tokens, contraseñas o credenciales aparezcan en outputs de agentes (chat transcripts, commits, mailbox messages, audit docs, retros).

## Why this skill exists

Incidente real **2026-04-26** (sesión `umbral-bot-copilot` AF-1k.16i1c → i1d): un gate token de Container App se imprimió completo en el transcript local del Copilot Chat. Costó una rotación inmediata + commit explícito de revocación. Plan Q2 §6 lista esto como riesgo activo.

Este skill es la **regla operativa cross-agent**: cualquier output sustantivo pasa por este checklist antes de quedar persistido.

## When to invoke

**Antes de cualquier de estos:**

- Imprimir output de comando que pueda incluir credenciales (`az`, `gh`, `curl` con headers, scripts que leen `.env`, `kubectl get secrets`, etc.).
- Commitear archivo (incluido `.md`, `.yaml`, `.json`, `.ps1`, `.py`).
- Escribir mensaje en `.agents/mailbox/`.
- Cerrar Friday retro.
- Mover páginas o adjuntos en Notion via MCP (un adjunto puede contener un screenshot con tokens).

## The checklist (8 patrones a buscar)

1. **Tokens explícitos:** `[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{6,}` (JWT-like), `ghp_`, `ghs_`, `gho_`, `github_pat_`, `sk-`, `sk_test_`, `sk_live_`, `Bearer `, `Basic `.
2. **Azure:** `DefaultEndpointsProtocol=`, `AccountKey=`, claves de Cognitive Services / OpenAI / Search (~32–88 chars base64), `client_secret=`.
3. **Google:** `AIza...`, `ya29.`, `1//0`, `GOOGLE_REFRESH_TOKEN=`.
4. **Notion / Granola:** `secret_...`, `ntn_`, integration tokens.
5. **MercadoPago / Stripe / pasarelas:** `APP_USR-...-...-...`, `whsec_`, `pi_`.
6. **SSH / GPG:** `BEGIN OPENSSH PRIVATE KEY`, `BEGIN PGP PRIVATE KEY`, `BEGIN RSA PRIVATE KEY`.
7. **Connection strings:** `mongodb+srv://`, `postgres://user:pass@`, `mysql://`, cualquier URL con `:.+@`.
8. **Variables de entorno con nombre sospechoso** mostradas con valor: cualquier env que contenga `KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API_KEY` en su nombre.

## What to do if you find one

| Situación | Acción |
|---|---|
| Token apareció en chat output (no commiteado) | Pedir a David rotación inmediata. Reemplazar valor por `[REDACTED]` antes de continuar. NO commitear el output. |
| Token ya está commiteado | **Stop.** Avisar a David. Rotar primero, después usar `git filter-repo` o equivalente. NO basta con un commit que borre — el token sigue en historia. |
| Variable de entorno con nombre sospechoso pero sin valor mostrado | OK — solo el nombre es información pública. |
| Comando va a imprimir token (ej: `az ad sp create-for-rbac`) | Redirigir output a archivo en `.gitignore`, leer con redacción, o usar flag `--query` para extraer solo lo no-secreto. |

## Reglas operativas para agentes

1. **Default-deny.** Si tenés duda de si un valor es sensible, asumí que sí.
2. **Nunca pegar `.env` completo** en chat ni en commits, ni siquiera con valores fake.
3. **Comandos `az`/`gcloud`/`kubectl`/`gh` que retornan credenciales:** siempre con `--query` o `| ConvertFrom-Json | Select` para acotar.
4. **Si pedís a David un secreto:** que lo paste en input efímero (terminal interactivo), no en chat history.
5. **Workspace settings:** `.vscode/settings.json` no debe tener `terminal.integrated.persistentSessionReviveProcess: never` desactivado (los buffers de terminal pueden persistir en disco).
6. **Friday retro:** sección `Quality gate` incluye checkbox `[ ] No hay tokens/secrets en este doc`. No se commitea retro sin esa marca.
7. **Si un agente externo (Codex, otro hilo Copilot) pasó un secret en handoff via mailbox:** rechazar el mensaje con `status: cancelled` + razón, pedir reenvío sin secreto.
8. **Inspección de `/proc/$PID/environ` (Linux runtime forensics):** NUNCA `cat`, `strings`, ni `grep` con patrones que matcheen el VALOR del secret (ej: `grep "COPILOT"`, `grep "TOKEN"`, `grep "sk-"`). El environ contiene los secretos en plaintext y cualquier match imprime el valor completo. **Incidente motivante F-INC-001 (2026-05-07):** durante audit OpenClaw, un agente ejecutó `grep "COPILOT" /proc/$PID/environ` y volcó `COPILOT_GITHUB_TOKEN=ghp_...` al output → rotación inmediata. **Patrón aprobado** — listar solo nombres de var, o nombre + longitud + fingerprint:
   ```bash
   # Solo nombres (seguro siempre):
   tr '\0' '\n' < /proc/$PID/environ | awk -F= '{print $1}' | sort -u

   # Nombre + longitud + sha8 del valor (para confirmar fingerprint sin leak):
   tr '\0' '\n' < /proc/$PID/environ \
     | awk -F= '/(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)/ {
         val=$0; sub(/^[^=]*=/, "", val);
         "printf %s \"" val "\" | sha256sum | cut -c1-8" | getline h;
         printf "%s=<len=%d sha8=%s>\n", $1, length(val), h
       }' | sort
   ```
   Regla equivalente para cualquier dump de entorno (`env`, `printenv`, `ps eww`, `systemctl show --property=Environment`): aplicar el mismo filtrado nombre-only o nombre+fingerprint.

## Tool-emitted partial leaks

Algunas herramientas oficiales imprimen prefijos parcialmente enmascarados de secretos por defecto. Aunque "solo" sea el prefijo (ej: `gho_abcd******`), es suficiente para correlacionar tokens en audit logs y queda en transcripts de chat. Filtrar SIEMPRE.

| Herramienta | Patrón que leakea | Mitigación |
|---|---|---|
| `gh auth status` | `  - Token: gho_<REDACTED>` (prefijo parcial enmascarado) | `gh auth status 2>&1 \| grep -v "^  - Token:"` |
| `git config --list` (cuando hay creds en URLs o `extraheader`) | `url.https://USER:<REDACTED>@github.com/...`, `http.extraheader=AUTHORIZATION: bearer <REDACTED>` | `git config --list \| grep -v "url\.\\\|extraheader"` |
| `az account show` con credenciales en cache | algunos campos (`tenantDefaultDomain`, `homeAccountId`) son fingerprints válidos para correlación | `az account show --query "{name:name, id:id, state:state}" -o table` (whitelist explícita) |
| `gh api .../actions/secrets` | nombres de secrets son metadata pero pueden filtrar topología | OK exponer nombres si la org/repo es público; redactar en docs externos |
| `kubectl get secret <name> -o yaml` | volca `data.<key>: <base64>` que es trivialmente decodificable | NUNCA imprimir; usar `kubectl get secret <name> -o jsonpath='{.metadata.creationTimestamp}'` o describir solo metadata |
| `docker inspect <container>` | `Config.Env` lista todas las env vars con valor | `docker inspect <c> --format '{{range .Config.Env}}{{println (index (split . "=") 0)}}{{end}}'` (solo nombres) |
| `systemctl show <unit>` | `Environment=KEY=VALUE` con valor | `systemctl show <unit> --property=Environment \| sed 's/=[^[:space:]]*/=<REDACTED>/g'` o filtrar nombres con awk como en regla 8 |

**Regla general:** si una herramienta oficial imprime "parte" del secreto por conveniencia de UX, tratar ese prefijo como secreto completo. Mitigar con un pipe de filtrado documentado aquí; agregar entradas nuevas a esta tabla cuando se descubran.

**Origen de esta sección:** task O7c (`.agents/tasks/2026-05-08-O7c-gh-auth-status-leak-pattern.md` en `umbral-agent-stack`), durante el smoke O7 (PR #378) Copilot-VPS observó el leak de `gh auth status` y no había mitigación documentada.

**Ejemplos en esta tabla:** todos usan placeholder `<REDACTED>`. Nunca pegar tokens reales (ni siquiera enmascarados) como ejemplo.

## What this skill does NOT do

- No reemplaza un escáner real (`gitleaks`, `trufflehog`). Es un guardrail conductual.
- No es una garantía — los humanos siguen siendo la última defensa.
- No se aplica a runtime real de aplicaciones (donde los secrets sí existen y se manejan via env vars / key vault). Aplica solo a **outputs visibles para humanos**.

## Sugerencia futura

Cuando el repo tenga >50 commits con outputs estructurados, evaluar instalar `gitleaks` como pre-commit hook (`policies/05` §"Live agent contract changes" implica formalizar esto en `pre-commit-config.yaml`).
