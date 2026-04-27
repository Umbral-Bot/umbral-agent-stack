#!/usr/bin/env bash
# Deja el repo en la rama "rick/vps" para editar (creada desde main si no existe).
# Uso: bash scripts/vps/rick-branch-for-change.sh
# No se trabaja en main; este script deja listo el repo para editar en la rama rick.
# Ver runbook §7.0 y docs/34-rick-github-token-setup.md
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/umbral-agent-stack}"
BRANCH="rick/vps"

cd "$REPO_DIR"
if [ ! -d .git ]; then
  echo "Error: no es un repositorio git ($REPO_DIR)" >&2
  exit 1
fi

git fetch origin
git checkout main
git pull origin main

if git show-ref --quiet refs/heads/rick/vps; then
  git checkout rick/vps
  git merge main --no-edit
else
  git checkout -b rick/vps
fi

echo ""
echo "Rama activa: $BRANCH"
echo "Siguiente: haz tus cambios, luego:"
echo "  git add . && git commit -m 'descripción del cambio'"
echo "  git push -u origin rick/vps"
echo "  (abrir PR a main desde GitHub; el merge lo hace David/Cursor)"
echo "Tras el merge en la VPS: git checkout main && git pull origin main"
echo ""
