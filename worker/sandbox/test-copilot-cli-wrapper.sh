#!/usr/bin/env bash
# worker/sandbox/test-copilot-cli-wrapper.sh — F2.5 wrapper deny-list test.
#
# Runs the wrapper inside the sandbox image with a battery of strings
# (allowed and banned) and asserts the expected outcome:
#   - banned -> exit 126, stderr contains BANNED_SUBCOMMAND
#   - allowed -> exit 127 (binary missing) OR 0; never 126
#
# This script is offline (--network=none), uses no token, does not
# touch the host. All shell strings are passed AS A SINGLE ARG to the
# wrapper to mirror the realistic case of Copilot CLI proposing a
# command via shell-tool invocation.

set -u

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
TAG="$(bash "${SCRIPT_DIR}/refresh-copilot-cli.sh" --print)"

run_wrapper() {
    docker run --rm \
        --network=none --read-only \
        --tmpfs /tmp:size=16m,exec \
        --tmpfs /scratch:size=16m,mode=1777 \
        --tmpfs /home/runner/.cache:size=16m,mode=1777 \
        --cap-drop=ALL --security-opt no-new-privileges \
        --user 10001:10001 --ipc=none \
        --entrypoint /usr/local/bin/copilot-cli-wrapper \
        "${TAG}" \
        "$@"
}

pass=0; fail=0
expect_banned() {
    local label="$1"; shift
    local out
    out="$(run_wrapper "$@" 2>&1)"
    local code=$?
    if [ "${code}" = "126" ] && echo "${out}" | grep -q "BANNED_SUBCOMMAND"; then
        pass=$((pass+1))
        printf '  PASS  banned: %s\n' "${label}"
    else
        fail=$((fail+1))
        printf '  FAIL  banned (got code=%s out=%s): %s\n' "${code}" "${out}" "${label}"
    fi
}

expect_allowed() {
    local label="$1"; shift
    local out
    out="$(run_wrapper "$@" 2>&1)"
    local code=$?
    if [ "${code}" != "126" ]; then
        pass=$((pass+1))
        printf '  PASS  allowed (code=%s): %s\n' "${code}" "${label}"
    else
        fail=$((fail+1))
        printf '  FAIL  allowed but blocked: %s\n' "${label}"
    fi
}

echo "[wrapper-test] image=${TAG}"
echo "[wrapper-test] banned cases:"

expect_banned "git push"               git push
expect_banned "git push -f"            git push -f origin main
expect_banned "git push --force"       git push --force origin HEAD
expect_banned "git push --force-with-lease" git push --force-with-lease origin main
expect_banned "git push --mirror"      git push --mirror origin
expect_banned "git push --tags"        git push --tags origin
expect_banned "git push --delete"      git push --delete origin some-branch
expect_banned "git push --set-upstream" git push --set-upstream origin feat/x
expect_banned "git push -u"            git push -u origin feat/x
expect_banned "git push --no-verify"   git push --no-verify origin main
expect_banned "git remote add"         git remote add evil https://example.com/x.git
expect_banned "git remote set-url"     git remote set-url origin https://evil/x.git
expect_banned "git config --global"    git config --global user.email evil@x
expect_banned "git filter-branch"      git filter-branch --tree-filter rm
expect_banned "git update-ref"         git update-ref refs/heads/main HEAD
expect_banned "gh pr create"           gh pr create --title x
expect_banned "gh pr merge"            gh pr merge 1
expect_banned "gh pr comment"          gh pr comment 1 -b hi
expect_banned "gh pr review"           gh pr review 1 --approve
expect_banned "gh pr close"            gh pr close 1
expect_banned "gh pr edit"             gh pr edit 1 --title y
expect_banned "gh pr ready"            gh pr ready 1
expect_banned "gh pr reopen"           gh pr reopen 1
expect_banned "gh release create"      gh release create v1
expect_banned "gh release delete"      gh release delete v1
expect_banned "gh release upload"      gh release upload v1 file
expect_banned "gh repo create"         gh repo create x
expect_banned "gh repo delete"         gh repo delete x
expect_banned "gh repo edit"           gh repo edit --homepage x
expect_banned "gh repo rename"         gh repo rename y
expect_banned "gh repo archive"        gh repo archive x
expect_banned "gh secret set"          gh secret set X --body y
expect_banned "gh secret delete"       gh secret delete X
expect_banned "gh secret"              gh secret list
expect_banned "gh auth login"          gh auth login
expect_banned "gh auth logout"         gh auth logout
expect_banned "gh auth refresh"        gh auth refresh
expect_banned "gh auth setup-git"      gh auth setup-git
expect_banned "gh auth"                gh auth status
expect_banned "gh api"                 gh api /user
expect_banned "gh workflow run"        gh workflow run x.yml
expect_banned "gh workflow disable"    gh workflow disable x.yml
expect_banned "gh workflow enable"     gh workflow enable x.yml
expect_banned "gh ssh-key add"         gh ssh-key add /tmp/k
expect_banned "gh gpg-key add"         gh gpg-key add /tmp/k
expect_banned "rm -rf"                 rm -rf /
expect_banned "rm -fr"                 rm -fr /
expect_banned "chmod -R"               chmod -R 777 /
expect_banned "chown -R"               chown -R x /
expect_banned "dd if="                 dd if=/dev/zero of=/tmp/x
expect_banned "mkfs"                   mkfs.ext4 /dev/sdz
expect_banned "sudo"                   sudo whoami
expect_banned "su -"                   su - root

echo "[wrapper-test] allowed cases:"
expect_allowed "git status"            git status
expect_allowed "git log"               git log --oneline
expect_allowed "git diff"              git diff HEAD
expect_allowed "ls -la"                ls -la /work
expect_allowed "cat README"            cat /etc/hostname
expect_allowed "echo hello"            echo hello
expect_allowed "git fetch (no push)"   git fetch origin

printf '\n[wrapper-test] passes=%d fails=%d\n' "${pass}" "${fail}"
if [ "${fail}" -eq 0 ]; then
    printf 'WRAPPER_TEST_RESULT=ok\n'
    exit 0
else
    printf 'WRAPPER_TEST_RESULT=fail\n'
    exit 1
fi
