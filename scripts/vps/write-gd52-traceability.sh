#!/usr/bin/env bash
# Write G-D5.2 traceability report on VPS (no secret values).
set -euo pipefail

EVID="${HOME}/.coord-ag-evidence/G-D5.2"
ENV="${HOME}/.config/openclaw/env"
REPO="${HOME}/umbral-agent-stack"
mkdir -p "$EVID"

BACKUP=$(ls -t "${HOME}/.config/openclaw/env.bak.gd52."* 2>/dev/null | head -1 || true)
OLD_CLIENT=""
NEW_CLIENT=""
if [[ -n "$BACKUP" && -f "$BACKUP" ]]; then
  OLD_CLIENT=$(grep '^GOOGLE_GMAIL_CLIENT_ID=' "$BACKUP" | cut -d= -f2 | sed 's/.apps.googleusercontent.com//' | cut -c1-30)
fi
NEW_CLIENT=$(grep '^GOOGLE_GMAIL_CLIENT_ID=' "$ENV" | cut -d= -f2 | sed 's/.apps.googleusercontent.com//' | cut -c1-30)

HEAD=$(cd "$REPO" && git log -1 --oneline 2>/dev/null || echo "unknown")

cat > "$EVID/traceability-report.md" <<EOF
# G-D5.2 — Trazabilidad OAuth Rick (VPS)

- **Date:** $(date -u +%Y-%m-%dT%H:%M:%SZ)
- **Agent:** Cursor (deploy + verification)
- **Repo HEAD at report:** ${HEAD}
- **Account OAuth:** rick.asistente@gmail.com
- **GCP client name:** Rick OpenClaw (project future-yeti-455715-u7)

## 1. Qué dijo G-D5.1 (NO era “faltan variables”)

Fuente: \`~/.coord-ag-evidence/G-D5.1/audit-report.md\`

| Var | G-D5.1 state | Interpretación |
|---|---|---|
| GOOGLE_GMAIL_CLIENT_ID/SECRET/REFRESH_TOKEN | SET | Presentes — no restaurar |
| GOOGLE_CALENDAR_CLIENT_ID/SECRET/REFRESH_TOKEN | SET | Presentes — no restaurar |
| GOOGLE_CLOUD_LOCATION | SET | Presentes |
| GOOGLE_GMAIL_TOKEN | UNSET | **Esperado** (flujo refresh) |
| GOOGLE_CALENDAR_TOKEN | UNSET | **Esperado** |
| GOOGLE_SERVICE_ACCOUNT_JSON | UNSET | **Esperado** |
| Smoke Gmail + Calendar | PASS | Conectividad OK |

**Bloqueador G-D5.1:** scope drift ADR-16 (tokens/código con scopes más amplios que \`gmail.modify\` + \`calendar.events\`), no ausencia de líneas en env.

## 2. Qué cambió en G-D5.2 (SÍ — valores rotados)

| Campo | Antes (backup gd52) | Después (live env) |
|---|---|---|
| GOOGLE_GMAIL_CLIENT_ID prefix | ${OLD_CLIENT:-unknown} | ${NEW_CLIENT} |
| GOOGLE_CALENDAR_CLIENT_ID | mismo par que Gmail | mismo par (un solo OAuth client) |
| GOOGLE_*_CLIENT_SECRET | rotado | rotado (len cambió; valor no registrado) |
| GOOGLE_*_REFRESH_TOKEN | rotado | rotado (nuevo consent Playground) |
| Worker gmail.py scopes | gmail.compose + gmail.readonly | gmail.modify |
| Worker calendar.py scopes | calendar (full) | calendar.events |

Env backup pre-rotación: \`${BACKUP:-none}\`

**No se agregaron nombres de variables nuevos obligatorios.** Se reemplazaron valores de las 6 vars OAuth + se mantuvo GOOGLE_CLOUD_LOCATION / GCLOUD_LOCATION.

## 3. Verificación post-rotación

Ejecutar:

\`\`\`bash
bash ~/umbral-agent-stack/scripts/vps/audit-google-env-vs-gd51.sh
bash ~/umbral-agent-stack/scripts/vps/smoke-gd52-oauth.sh
\`\`\`

Criterio PASS:

- tokeninfo scopes = \`gmail.modify\` + \`calendar.events\`
- Gmail profile = rick.asistente@gmail.com
- Worker: \`gmail.list_drafts\` + \`google.calendar.list_events\` → ok:true

## 4. GCP / browser (Cursor)

- Client **Umbral-bot**: redirect OAuth Playground **eliminado** (solo umbralbim.io + Supabase).
- Client **Rick OpenClaw**: creado; redirect solo OAuth Playground.

## 5. Cierre G-D5.2 (2026-06-02)

| Hilo | VEREDICTO | Evidencia |
|---|---|---|
| Copilot-VPS closeout (015) | G_D52_VPS_CLOSEOUT_OK | closeout-audit.txt, tokeninfo, smokes |
| Copilot-VPS Calendar E2E (016) | G_D52_CALENDAR_E2E_OK | calendar-david-primary-list.json |
| Copilot Windows docs (PR #438) | GD52_DOCS35_MERGED | commit 1187eaa9 |
| Notion live §6 mirror | ADR16_LIVE_LOG_OK | Gobernanza Notion |

Pendiente gate formal: task 017 → **G_D52_GATE_CLOSED** (VPS sync + traceability refresh).

Skills OpenClaw Gmail/Calendar: task 018 (Codex).

## VEREDICTO

**G_D52_VPS_REOAUTH_OK** — vars G-D5.1 siguen SET; valores OAuth y scopes ADR-16 aplicados; worker en main alineado.
EOF

echo "Wrote $EVID/traceability-report.md"
