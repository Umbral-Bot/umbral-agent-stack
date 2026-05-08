# Task: O18b — YAML LinkedIn ajustes menores P1

- **ID**: O18b-yaml-linkedin-minor-fixes
- **Owner**: Copilot VPS
- **Branch**: `copilot-vps/o18b-yaml-linkedin-minor-fixes`
- **Base**: `main`
- **Estado**: ready
- **Creada**: 2026-05-07
- **Ref**: PR #339 (spike O18), [`docs/spikes/O18-linkedin-auth-gap-report.md`](../../docs/spikes/O18-linkedin-auth-gap-report.md) §4 P1

## Contexto

PR #339 cerró el spike read-only O18 con veredicto: **el yaml sirve as-is con ajustes menores**. Esta tarea aplica los 7 ajustes P1 identificados en el reporte. **NO** implementa handler, **NO** toca runtime.

## Scope (7 ajustes en `config/auth_lifecycle.example.yaml` + 1 en `.env.example`)

1. **Renombrar** `credential_ref: linkedin_company_access_token` → `linkedin_personal_access_token`. Coincide con [ADR-005](../../docs/adr/ADR-005-publicacion-multicanal.md): Rick publica en perfil personal, sin Company Page por falta de entidad legal.
2. **Renombrar** `credential_ref: linkedin_refresh_authorization` → `linkedin_app_authorization`. Clarifica que es re-consentimiento del usuario al app, no un OAuth refresh_token.
3. **Agregar** campo `mdp_approved: false` explícito en la entrada de access_token. Permite que el handler valide antes de intentar refresh programático.
4. **Agregar** `expected_scopes: ["w_member_social"]` en la entrada de access_token. Permite detectar drift cuando LinkedIn devuelva scopes distintos a los esperados.
5. **Agregar comment** clarificando que el refresh_token de LinkedIn (si en el futuro David obtiene MDP) **NO rota**: el TTL se preserva desde la emisión inicial. Día 59 después de refrescar = 306 días restantes (365−59), no 365.
6. **Linkear** en el `reauth_playbook` el shortcut: https://www.linkedin.com/developers/tools/oauth/token-generator (Token Generator manual del Developer Portal — desbloquea el handler v0 sin OAuth callback completo).
7. **Stubs en `.env.example`** para:
   - `LINKEDIN_CLIENT_ID=`
   - `LINKEDIN_CLIENT_SECRET=`
   - `LINKEDIN_REDIRECT_URI=`
   - (NO incluir `LINKEDIN_ACCESS_TOKEN` con valor — solo si ya existe la línea, dejar vacío con comment "set after manual OAuth via Token Generator").

## Reglas duras

- **0** cambios en runtime (worker/, dispatcher/, identity/).
- **0** implementación de handler `linkedin.post_share` ni similar.
- **0** llamadas a LinkedIn API.
- **0** secretos en repo.
- Solo metadata, comments y stubs de variables vacías.

## Aceptación

PR contra `main` con:

- Diff de `config/auth_lifecycle.example.yaml` (1 archivo, ~10-15 líneas modificadas/agregadas).
- Diff de `.env.example` (1 archivo, ~3-4 líneas agregadas).
- Body del PR cita PR #339 y reporte de gap.
- Tests existentes siguen pasando (no debería romper nada — es metadata).
- Branch `copilot-vps/o18b-yaml-linkedin-minor-fixes` desde `main`.

## Referencias

- PR #339 spike O18: https://github.com/Umbral-Bot/umbral-agent-stack/pull/339
- Reporte gap: [`docs/spikes/O18-linkedin-auth-gap-report.md`](../../docs/spikes/O18-linkedin-auth-gap-report.md)
- ADR-005: [`docs/adr/ADR-005-publicacion-multicanal.md`](../../docs/adr/ADR-005-publicacion-multicanal.md)
