#!/usr/bin/env bash
# tournament-lane-worktree.sh — tournament v1.1 hardening (D3.4 RC-4 / D3.6 Fase 4)
#
# Isolated git worktree per tournament lane. Prevents the shared-worktree
# conflicts seen in D3.3 (retro RC-4) where one lane checked out a delivery
# branch in the shared clone while another lane was still working.
#
# Usage:
#   tournament-lane-worktree.sh create <repo_path> <tournament_id> <specialty> [base]
#   tournament-lane-worktree.sh remove <repo_path> <tournament_id> <specialty>
#
# create:
#   - Adds a git worktree at
#     ${TOURNAMENT_WORKTREE_ROOT:-$HOME/.coord-ag-evidence/worktrees}/<tournament_id>/lane-<specialty>
#   - On branch tournament/<tournament_id>/lane-<specialty> from origin/<base> (default main).
#   - Idempotent: re-running for the same lane reports the existing worktree and exits 0.
#
# remove:
#   - Removes only this lane's worktree (refuses if it has uncommitted changes
#     unless TOURNAMENT_WORKTREE_FORCE=1) and prunes stale administrative files.
#   - Never deletes the lane branch (keep-losers / forensic retention).
#   - Idempotent: a missing worktree is reported as already absent (exit 0).
#
# Parseable stdout (one KEY=VALUE per line):
#   WORKTREE_PATH=<path>
#   BRANCH=<branch>
#   WORKTREE_VERDICT=CREATED|EXISTS|REMOVED|ABSENT
#
# Safety: the target path is derived solely from <tournament_id>/<specialty>;
# remove never uses a recursive rm and refuses to touch the main worktree, so it
# cannot delete another lane's work.
set -euo pipefail

SEGMENT_RE='^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$'
BASE_RE='^[A-Za-z0-9_./-]+$'

die() { echo "ERROR: $*" >&2; exit 2; }

usage() {
  cat >&2 <<'EOF'
Usage:
  tournament-lane-worktree.sh create <repo_path> <tournament_id> <specialty> [base]
  tournament-lane-worktree.sh remove <repo_path> <tournament_id> <specialty>
EOF
  exit 2
}

[[ $# -ge 4 ]] || usage
action="$1"
repo_path="$2"
tournament_id="$3"
specialty="$4"
base="${5:-main}"

[[ "$tournament_id" =~ $SEGMENT_RE ]] || die "invalid tournament_id: '$tournament_id'"
[[ "$specialty" =~ $SEGMENT_RE ]] || die "invalid specialty: '$specialty'"
[[ "$base" =~ $BASE_RE ]] || die "invalid base: '$base'"
[[ -e "$repo_path/.git" ]] || die "repo_path is not a git repo: $repo_path"

worktree_root="${TOURNAMENT_WORKTREE_ROOT:-$HOME/.coord-ag-evidence/worktrees}"
branch="tournament/$tournament_id/lane-$specialty"
worktree_path="$worktree_root/$tournament_id/lane-$specialty"

git_repo() { git -C "$repo_path" "$@"; }

# Echo the path of the registered worktree whose checked-out branch is $1.
# Returns non-zero when no worktree holds that branch.
worktree_path_for_branch() {
  local want="refs/heads/$1" cur_path="" cur_branch=""
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ -z "$line" ]]; then
      [[ "$cur_branch" == "$want" ]] && { printf '%s\n' "$cur_path"; return 0; }
      cur_path=""
      cur_branch=""
      continue
    fi
    case "$line" in
      worktree\ *) cur_path="${line#worktree }" ;;
      branch\ *) cur_branch="${line#branch }" ;;
    esac
  done < <(git_repo worktree list --porcelain)
  [[ "$cur_branch" == "$want" ]] && { printf '%s\n' "$cur_path"; return 0; }
  return 1
}

branch_exists() { git_repo show-ref --verify --quiet "refs/heads/$branch"; }

# Prefer origin/<base>; fall back to a local <base> branch.
resolve_base_ref() {
  if git_repo rev-parse --verify --quiet "origin/$base" >/dev/null; then
    printf 'origin/%s\n' "$base"
    return 0
  fi
  if git_repo rev-parse --verify --quiet "refs/heads/$base" >/dev/null; then
    printf '%s\n' "$base"
    return 0
  fi
  return 1
}

emit() {
  echo "WORKTREE_PATH=$1"
  echo "BRANCH=$branch"
  echo "WORKTREE_VERDICT=$2"
}

do_create() {
  git_repo worktree prune >/dev/null 2>&1 || true

  local existing
  if existing="$(worktree_path_for_branch "$branch")"; then
    emit "$existing" "EXISTS"
    return 0
  fi

  mkdir -p "$(dirname "$worktree_path")"
  if [[ -e "$worktree_path" ]]; then
    if [[ -n "$(ls -A "$worktree_path" 2>/dev/null || true)" ]]; then
      die "worktree path exists and is not empty, refusing to clobber: $worktree_path"
    fi
    rmdir "$worktree_path" 2>/dev/null || true
  fi

  git_repo fetch origin "$base" --quiet 2>/dev/null || true

  if branch_exists; then
    git_repo worktree add "$worktree_path" "$branch" >&2
  else
    local base_ref
    base_ref="$(resolve_base_ref)" || die "cannot resolve base ref 'origin/$base' or '$base'"
    git_repo worktree add -b "$branch" "$worktree_path" "$base_ref" >&2
  fi

  emit "$worktree_path" "CREATED"
}

do_remove() {
  git_repo worktree prune >/dev/null 2>&1 || true

  local target=""
  if target="$(worktree_path_for_branch "$branch")"; then
    :
  elif [[ -d "$worktree_path" ]]; then
    target="$worktree_path"
  fi

  if [[ -z "$target" ]]; then
    emit "$worktree_path" "ABSENT"
    return 0
  fi

  local main_path
  main_path="$(git_repo rev-parse --show-toplevel 2>/dev/null || echo "$repo_path")"
  if [[ "$target" == "$main_path" ]]; then
    die "refusing to remove the main worktree: $target"
  fi

  local force_flag=()
  if [[ "${TOURNAMENT_WORKTREE_FORCE:-0}" == "1" ]]; then
    force_flag=(--force)
  fi
  git_repo worktree remove "${force_flag[@]}" "$target" >&2
  git_repo worktree prune >/dev/null 2>&1 || true

  emit "$target" "REMOVED"
}

case "$action" in
  create) do_create ;;
  remove) do_remove ;;
  *) usage ;;
esac
