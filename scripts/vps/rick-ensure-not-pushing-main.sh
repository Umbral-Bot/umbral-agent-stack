#!/usr/bin/env bash
# Comprueba que la rama actual no sea main. Usar antes de git push desde la VPS.
# Si estás en main, falla (exit 1): no se debe hacer push a main desde la VPS.
# Uso: bash scripts/vps/rick-ensure-not-pushing-main.sh
# Opcional: en un hook pre-push o antes de scripts que hagan push.
# Ver runbook §7.0 — no hay clonación de main para trabajar; merge lo hace David/Cursor.
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/umbral-agent-stack}"
cd "$REPO_DIR"
CURRENT=$(git branch --show-current 2>/dev/null || true)

if [ -z "$CURRENT" ]; then
  echo "rick-ensure-not-pushing-main: no se pudo detectar la rama actual (detached HEAD?)." >&2
  exit 1
fi

if [ "$CURRENT" = "main" ]; then
  echo "rick-ensure-not-pushing-main: estás en 'main'. No hagas push a main desde la VPS." >&2
  echo "Ponte en la rama rick/vps con: bash scripts/vps/rick-branch-for-change.sh" >&2
  echo "Luego trabaja en la rama rick/vps, push y abre PR; el merge lo hace David/Cursor." >&2
  exit 1
fi

exit 0
