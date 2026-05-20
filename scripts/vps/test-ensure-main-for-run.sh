#!/usr/bin/env bash
# test-ensure-main-for-run.sh — local sandbox test for ensure-main-for-run.sh.
#
# NOT invoked from cron. NOT installed on the VPS. Pure local validation.
#
# Creates a throwaway git sandbox, runs 4 scenarios, prints PASS/FAIL per case.
#
# Usage:
#   bash scripts/vps/test-ensure-main-for-run.sh
#
# Exit 0 if all 4 scenarios behave as expected, 1 otherwise.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HELPER="$SCRIPT_DIR/ensure-main-for-run.sh"

if [ ! -f "$HELPER" ]; then
    echo "FATAL: helper not found at $HELPER" >&2
    exit 1
fi

SANDBOX="$(mktemp -d)"
REMOTE_DIR="$SANDBOX/remote.git"
WORK_DIR="$SANDBOX/work"
LOG_FILE="$SANDBOX/ensure_main.log"

cleanup() {
    rm -rf "$SANDBOX"
}
trap cleanup EXIT

echo "Sandbox: $SANDBOX"

# 1. Build a bare remote with one commit on main.
git init --quiet --bare "$REMOTE_DIR"
git -c init.defaultBranch=main clone --quiet "$REMOTE_DIR" "$WORK_DIR"
cd "$WORK_DIR"
git checkout -q -B main
echo "hello" > README.md
git add README.md
git -c user.email=test@example.com -c user.name=Test commit --quiet -m "init"
git push --quiet origin main

PASS=0
FAIL=0

run_case() {
    local name="$1"
    local expected="$2"   # 0 or nonzero
    shift 2
    local actual=0
    REPO="$WORK_DIR" \
    ENSURE_MAIN_LOG="$LOG_FILE" \
    ENSURE_MAIN_THROTTLE_SEC=0 \
        bash "$HELPER" >/dev/null 2>&1 || actual=$?
    if [ "$expected" = "0" ]; then
        if [ "$actual" = "0" ]; then
            echo "PASS  $name (exit=$actual)"
            PASS=$((PASS + 1))
        else
            echo "FAIL  $name (expected exit=0, got $actual)"
            FAIL=$((FAIL + 1))
        fi
    else
        if [ "$actual" != "0" ]; then
            echo "PASS  $name (exit=$actual)"
            PASS=$((PASS + 1))
        else
            echo "FAIL  $name (expected nonzero exit, got 0)"
            FAIL=$((FAIL + 1))
        fi
    fi
}

# Case A: main, clean, up-to-date  -> should pass (exit 0).
run_case "A main clean up-to-date" 0

# Case B: feature branch  -> should block.
git checkout -q -b rick/test-feature
run_case "B branch != main" 1
git checkout -q main

# Case C: main with tracked dirty change  -> should block.
echo "dirty" >> README.md
run_case "C main tracked dirty" 1
git checkout -q -- README.md

# Case D: broken origin URL -> fetch fails  -> should block.
ORIG_URL="$(git remote get-url origin)"
git remote set-url origin "$SANDBOX/does-not-exist.git"
run_case "D fetch fails (bad remote)" 1
git remote set-url origin "$ORIG_URL"

# Case E (bonus): main with untracked file  -> should pass (we ignore untracked).
echo "stray" > .untracked
run_case "E main untracked file allowed" 0
rm -f .untracked

# Case F (bonus): main with simulated index.lock  -> should block.
touch "$WORK_DIR/.git/index.lock"
run_case "F index.lock present" 1
rm -f "$WORK_DIR/.git/index.lock"

# Case G (bonus): local commit on main not pushed -> should block.
echo "local-only" >> README.md
git add README.md
git -c user.email=test@example.com -c user.name=Test commit --quiet -m "local unpushed"
run_case "G local unpushed commit on main" 1
git reset --hard --quiet origin/main

echo ""
echo "Result: $PASS passed, $FAIL failed"
echo "Log tail:"
tail -20 "$LOG_FILE" 2>/dev/null || true

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
