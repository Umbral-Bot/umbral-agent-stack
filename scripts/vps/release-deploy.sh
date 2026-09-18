#!/usr/bin/env bash
# =================================================================
# release-deploy.sh — producción ejecuta una revisión identificable y aprobada.
#
# Antes, el cron invocaba los scripts desde el árbol de trabajo
# (`~/umbral-agent-stack/scripts/vps/...`). Eso significa que cualquier edición
# local, con o sin commit, entraba en producción en el siguiente tic del cron.
# No es teórico: el 2026-09-18 a las 15:00 UTC el cron ejecutó un canario a medio
# escribir desde una rama sin integrar y emitió una alarma falsa (Linear UMB-276).
#
# `ensure-main-for-run.sh` no cubría esto: es una PUERTA y solo protege a los
# scripts que la llaman. `health-check.sh`, `notion-poller-cron.sh` y
# `scheduled-tasks-cron.sh` no la llamaban.
#
# Modelo:
#   ~/.umbral/releases/<sha>/   copia inmutable de un commit (git archive, sin .git)
#   ~/.umbral/current           enlace simbólico al release activo
#   El cron invoca SIEMPRE ~/.umbral/current/scripts/vps/...
#
# Un despliegue es un acto explícito y posterior al merge. Editar el árbol de
# trabajo deja de tener efecto en producción.
#
#   bash scripts/vps/release-deploy.sh [--ref origin/main] [--dry-run]
#   bash scripts/vps/release-deploy.sh --rollback
#   bash scripts/vps/release-deploy.sh --status
# =================================================================
set -uo pipefail

REPO_DIR="${REPO_DIR:-$HOME/umbral-agent-stack}"
RELEASES_DIR="${UMBRAL_RELEASES_DIR:-$HOME/.umbral/releases}"
CURRENT_LINK="${UMBRAL_CURRENT_LINK:-$HOME/.umbral/current}"
PREVIOUS_FILE="$RELEASES_DIR/.previous"
KEEP="${UMBRAL_RELEASES_KEEP:-5}"

REF="origin/main"
MODE="deploy"
DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --ref) REF="${2:-origin/main}"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --rollback) MODE="rollback"; shift ;;
    --status) MODE="status"; shift ;;
    *) shift ;;
  esac
done

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

ops_log() {
  local dir="${UMBRAL_OPS_LOG_DIR:-$HOME/.config/umbral}"
  mkdir -p "$dir"; printf '%s\n' "$1" >> "$dir/ops_log.jsonl"
}

# --- status -------------------------------------------------------
if [ "$MODE" = "status" ]; then
  if [ -L "$CURRENT_LINK" ]; then
    target="$(readlink -f "$CURRENT_LINK")"
    sha="$(cat "$target/RELEASE_SHA" 2>/dev/null || echo desconocido)"
    log "release activo : $sha"
    log "ruta           : $target"
    log "desplegado el  : $(cat "$target/RELEASE_AT" 2>/dev/null || echo desconocido)"
    [ -f "$PREVIOUS_FILE" ] && log "anterior       : $(cat "$PREVIOUS_FILE")"
    log "releases       : $(ls -1 "$RELEASES_DIR" 2>/dev/null | grep -vc '^\.' || echo 0)"
  else
    log "NO hay release desplegado: $CURRENT_LINK no existe"
    exit 1
  fi
  exit 0
fi

# --- rollback -----------------------------------------------------
if [ "$MODE" = "rollback" ]; then
  [ -f "$PREVIOUS_FILE" ] || { log "ERROR: no hay release anterior registrado"; exit 1; }
  prev="$(cat "$PREVIOUS_FILE")"
  [ -d "$RELEASES_DIR/$prev" ] || { log "ERROR: el release anterior $prev ya no existe"; exit 1; }
  cur="$(readlink -f "$CURRENT_LINK" 2>/dev/null || true)"
  cur_sha="$(cat "$cur/RELEASE_SHA" 2>/dev/null || echo desconocido)"
  ln -sfn "$RELEASES_DIR/$prev" "$CURRENT_LINK.tmp" && mv -Tf "$CURRENT_LINK.tmp" "$CURRENT_LINK"
  printf '%s' "$cur_sha" > "$PREVIOUS_FILE"
  log "ROLLBACK hecho: $cur_sha -> $prev"
  ops_log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"kind\":\"release_rollback\",\"from\":\"$cur_sha\",\"to\":\"$prev\"}"
  exit 0
fi

# --- deploy -------------------------------------------------------
cd "$REPO_DIR" || { log "ERROR: no se puede entrar en $REPO_DIR"; exit 1; }

git fetch --quiet origin 2>/dev/null || log "AVISO: fetch fallo, se usa lo que haya en local"
SHA="$(git rev-parse --verify "$REF^{commit}" 2>/dev/null)" || { log "ERROR: ref '$REF' no resuelve"; exit 1; }

# Un release solo puede salir de algo que ya esta en origin/main. Esto es lo que
# impide desplegar una rama, un commit local o un arbol sucio.
if ! git merge-base --is-ancestor "$SHA" origin/main 2>/dev/null; then
  log "ERROR: $SHA no es ancestro de origin/main. Solo se despliega lo ya integrado."
  exit 2
fi

SHORT="${SHA:0:12}"
DEST="$RELEASES_DIR/$SHORT"
log "ref        : $REF"
log "commit     : $SHA"
log "destino    : $DEST"
if [ "$DRY" -eq 1 ]; then log "DRY RUN: no se escribe nada"; exit 0; fi

if [ -d "$DEST" ]; then
  log "el release $SHORT ya existe, se reutiliza (los releases son inmutables)"
else
  mkdir -p "$DEST"
  # git archive produce una copia SIN .git: el release no se puede editar con git
  # ni seguir una rama. Es inmutable por construccion.
  if ! git archive "$SHA" | tar -x -C "$DEST"; then
    log "ERROR: git archive fallo"; rm -rf "$DEST"; exit 1
  fi
  printf '%s' "$SHA" > "$DEST/RELEASE_SHA"
  date -u +%Y-%m-%dT%H:%M:%SZ > "$DEST/RELEASE_AT"
  # El entorno virtual es entorno, no codigo: se enlaza, no se copia.
  [ -d "$REPO_DIR/.venv" ] && ln -sfn "$REPO_DIR/.venv" "$DEST/.venv"
  chmod -R a-w "$DEST/scripts" 2>/dev/null || true
  log "release creado e inmutabilizado"
fi

prev_sha=""
if [ -L "$CURRENT_LINK" ]; then
  prev_sha="$(cat "$(readlink -f "$CURRENT_LINK")/RELEASE_SHA" 2>/dev/null || echo '')"
fi

mkdir -p "$(dirname "$CURRENT_LINK")"
# Cambio atomico: se crea un enlace temporal y se mueve encima. El cron nunca ve
# un estado intermedio.
ln -sfn "$DEST" "$CURRENT_LINK.tmp" && mv -Tf "$CURRENT_LINK.tmp" "$CURRENT_LINK"
[ -n "$prev_sha" ] && printf '%s' "${prev_sha:0:12}" > "$PREVIOUS_FILE"

log "DESPLEGADO: $CURRENT_LINK -> $DEST"
ops_log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"kind\":\"release_deploy\",\"sha\":\"$SHA\",\"ref\":\"$REF\",\"previous\":\"$prev_sha\"}"

# Poda: se conservan los ultimos $KEEP, y nunca el activo ni el anterior.
keep_sha="$SHORT"; keep_prev="$(cat "$PREVIOUS_FILE" 2>/dev/null || echo '')"
ls -1dt "$RELEASES_DIR"/*/ 2>/dev/null | tail -n +$(( KEEP + 1 )) | while read -r old; do
  b="$(basename "$old")"
  [ "$b" = "$keep_sha" ] && continue
  [ "$b" = "$keep_prev" ] && continue
  chmod -R u+w "$old" 2>/dev/null || true
  rm -rf "$old" && log "podado release antiguo: $b"
done
exit 0
