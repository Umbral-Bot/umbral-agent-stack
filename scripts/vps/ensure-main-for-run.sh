#!/usr/bin/env bash
# ensure-main-for-run.sh — BLOCKING GATE for cron/supervisor execution.
#
# Exit 0   : repo is on main, tracked-clean, no concurrent git op, and either
#            already up-to-date with origin/main or fast-forwarded successfully.
#            Caller is safe to proceed.
# Exit !=0 : any precondition failed. Caller MUST skip the run.
#
# Throttle: fetch+pull is only attempted at most once per ENSURE_MAIN_THROTTLE_SEC
#           (default 60s). The gate checks (branch, dirty, locks) always run.
# Locking : flock on $REPO/.git/ensure-main.lock serializes concurrent crons.
# Logging : appends to $ENSURE_MAIN_LOG (default /tmp/ensure_main_for_run.log)
#           with ISO timestamp + PID + result.
#
# Env:
#   REPO                       Path to the umbral-agent-stack checkout (required).
#   ENSURE_MAIN_LOG            Override log path.
#   ENSURE_MAIN_THROTTLE_SEC   Override throttle window in seconds.

set -u

REPO="${REPO:-$HOME/umbral-agent-stack}"
LOG="${ENSURE_MAIN_LOG:-/tmp/ensure_main_for_run.log}"
THROTTLE_SEC="${ENSURE_MAIN_THROTTLE_SEC:-60}"
LOCK_FILE="$REPO/.git/ensure-main.lock"
LAST_FILE="$REPO/.git/ensure-main.last"

log() {
    printf '%s [pid=%s] %s\n' "$(date -Iseconds 2>/dev/null || date)" "$$" "$*" >>"$LOG" 2>/dev/null || true
}

die() {
    log "BLOCK: $*"
    exit 1
}

if [ ! -d "$REPO/.git" ]; then
    log "BLOCK: $REPO is not a git checkout"
    exit 1
fi

cd "$REPO" || { log "BLOCK: cannot cd to $REPO"; exit 1; }

# Serialize concurrent invocations. If `flock` is not available (e.g. running
# the test on Git Bash for Windows), log and proceed without locking; the
# gate checks below still run and we just lose concurrent-run protection.
if command -v flock >/dev/null 2>&1; then
    exec 9>"$LOCK_FILE" 2>/dev/null || die "cannot open lock file $LOCK_FILE"
    if ! flock -w 5 9; then
        die "could not acquire lock within 5s (concurrent ensure-main running)"
    fi
else
    log "WARN: flock not available, proceeding without concurrent-run lock"
fi

# Gate 1: branch must be main.
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo UNKNOWN)"
if [ "$CURRENT_BRANCH" != "main" ]; then
    die "branch is '$CURRENT_BRANCH', not 'main'"
fi

# Gate 2: no tracked changes (staged or unstaged). Untracked files are allowed.
if ! git diff --quiet 2>/dev/null; then
    die "tracked unstaged changes present"
fi
if ! git diff --cached --quiet 2>/dev/null; then
    die "tracked staged changes present"
fi

# Gate 3: no other git operation in progress.
for marker in .git/index.lock .git/HEAD.lock .git/MERGE_HEAD .git/REBASE_HEAD .git/CHERRY_PICK_HEAD .git/REVERT_HEAD .git/rebase-merge .git/rebase-apply; do
    if [ -e "$marker" ]; then
        die "git operation in progress: $marker"
    fi
done

# Gate 4: throttle the fetch+pull, but the gate checks above always run.
NOW=$(date +%s)
SKIP_PULL=0
if [ -f "$LAST_FILE" ]; then
    LAST=$(cat "$LAST_FILE" 2>/dev/null || echo 0)
    case "$LAST" in
        ''|*[!0-9]*) LAST=0 ;;
    esac
    AGE=$((NOW - LAST))
    if [ "$AGE" -lt "$THROTTLE_SEC" ]; then
        SKIP_PULL=1
        log "OK: within throttle window (${AGE}s < ${THROTTLE_SEC}s), gate passed, skipping fetch+pull"
    fi
fi

if [ "$SKIP_PULL" -eq 0 ]; then
    if ! git fetch --quiet origin main 2>>"$LOG"; then
        die "git fetch origin main failed"
    fi

    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse origin/main)

    if [ "$LOCAL" != "$REMOTE" ]; then
        # Either fast-forward, or local has commits not in origin/main.
        BASE=$(git merge-base HEAD origin/main 2>/dev/null || echo "")
        if [ -z "$BASE" ]; then
            die "no common ancestor between HEAD and origin/main"
        fi
        if [ "$BASE" != "$LOCAL" ]; then
            # LOCAL is not an ancestor of REMOTE -> there are local commits
            # not present on origin/main. Refuse: cron must not execute
            # unreviewed local code.
            die "HEAD diverged from origin/main (local has unpushed commits on main)"
        fi
        # Safe to fast-forward.
        if ! git merge --ff-only --quiet origin/main 2>>"$LOG"; then
            die "git merge --ff-only origin/main failed"
        fi
    fi

    date +%s >"$LAST_FILE" 2>/dev/null || true
    log "OK: gate passed, fast-forwarded to $(git rev-parse --short HEAD)"
fi

exit 0
