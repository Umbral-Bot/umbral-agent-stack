#!/usr/bin/env bash
# Pone el repo en la rama main y actualiza. Usar antes de ejecutar Worker, Dispatcher o crons
# que corran código del repo, para que el stack siempre ejecute desde main (aunque la rama
# de trabajo de Rick sea rick). Ver runbook §7.0 y docs/rick-instrucciones-vps-rama-rick.md
set -euo pipefail
REPO="${REPO:-$HOME/umbral-agent-stack}"
cd "$REPO"
git fetch origin
git checkout main
git pull origin main
