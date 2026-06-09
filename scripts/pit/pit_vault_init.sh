#!/usr/bin/env bash
# pit_vault_init.sh — bootstrap idempotente del umbral-pit-vault.
#
# Crea la estructura mínima del vault de torneos PIT (separado del vault
# personal pull-only de David) y, opcionalmente, sincroniza las plantillas
# del repo hacia templates/. No toca ~/.openclaw, no escribe secretos.
#
# Uso:
#   scripts/pit/pit_vault_init.sh [VAULT_PATH] [--with-templates REPO_PATH]
#
#   VAULT_PATH   default: $PIT_VAULT_PATH o $HOME/umbral-pit-vault
#   --with-templates REPO_PATH
#                copia (sin sobreescribir) openclaw/workspace-templates/pit-vault/templates/
#                del clone indicado hacia <vault>/templates/
#
# Verificación posterior:
#   PIT_VAULT_WRITE_SCOPE=pit python scripts/pit/pit_vault_check.py \
#     --vault-path "$VAULT_PATH" --require-write-scope
set -euo pipefail

VAULT_PATH="${1:-${PIT_VAULT_PATH:-$HOME/umbral-pit-vault}}"
WITH_TEMPLATES=""
if [ "${2:-}" = "--with-templates" ]; then
  WITH_TEMPLATES="${3:?--with-templates requires a repo path}"
fi

mkdir -p "$VAULT_PATH/pit" "$VAULT_PATH/templates" "$VAULT_PATH/archive"

README="$VAULT_PATH/README.md"
if [ ! -f "$README" ]; then
  cat > "$README" <<'EOF'
# umbral-pit-vault

Vault Obsidian de torneos PIT (Product Innovation Tournament). Separado del
vault personal de David (que es pull-only desde la VPS).

- `pit/` — UNICO arbol con escritura para agentes PIT: `pit/<pit_id>/...`
- `templates/` — plantillas (kanban, kpi-pack, outcome report); lectura para lanes
- `archive/` — torneos cerrados (mueve Rick al cierre, no las lanes)

Layout completo: docs/ops/pit-vault-layout.md en umbral-agent-stack.
Check: scripts/pit/pit_vault_check.py
Sin secretos: nada de .env, llaves privadas, tokens ni sesiones aqui.
EOF
  echo "created: $README"
fi

GITIGNORE="$VAULT_PATH/.gitignore"
if [ ! -f "$GITIGNORE" ]; then
  cat > "$GITIGNORE" <<'EOF'
.obsidian/workspace.json
.obsidian/workspaces.json
EOF
  echo "created: $GITIGNORE"
fi

if [ -n "$WITH_TEMPLATES" ]; then
  SRC="$WITH_TEMPLATES/openclaw/workspace-templates/pit-vault/templates"
  if [ -d "$SRC" ]; then
    # -n: nunca sobreescribir ediciones locales del vault.
    cp -rn "$SRC/." "$VAULT_PATH/templates/"
    echo "templates synced (no-clobber) from: $SRC"
  else
    echo "WARN: templates source not found: $SRC" >&2
  fi
fi

echo "PIT_VAULT_INIT_OK $VAULT_PATH"
