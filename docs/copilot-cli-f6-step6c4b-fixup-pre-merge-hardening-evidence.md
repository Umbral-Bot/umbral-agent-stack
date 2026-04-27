# F6 step 6C-4B-fixup — Pre-merge hardening of PR #269

**Branch:** `rick/copilot-cli-capability-design`
**Parent HEAD (pre-fixup):** `b5641f9`
**PR under review:** [#269](https://github.com/Umbral-Bot/umbral-agent-stack/pull/269) (Draft)
**Scope:** code/test/docs only. **No** merge, **no** flag flip, **no** restart, **no** Copilot real, **no** nft/Docker/Notion.

---

## Why this fixup exists

Reviewer pre-merge surfaced four concerns on PR #269. None blocked correctness, but every one widened either an attack surface or a CI surface. This fixup closes them in a single coupled commit so the next reviewer pass starts from a clean baseline.

| # | Finding | Fix |
|---|---|---|
| 1 | `repo_path` accepted any string. A misconfigured caller could pass `/`, `/home/rick`, a non-directory, or a path that escapes via symlink. Even with `would_run=false`, this leaks the path into the audit log and into any future execution path. | Canonicalize via `Path.resolve(strict=False)`, then enforce that the canonical path is a *descendant* of an explicit allowlist of repo roots. Reject everything else with stable error codes. |
| 2 | `scripts/verify_copilot_cli_env_contract.py` did `import pwd` unconditionally, breaking any Windows checkout (CI matrices, dev machines) at import time. The planner also emitted backslash-separated user-scope paths on Windows, breaking the assertion `paths["dropin_dir"] == "/home/rick/.config/systemd/user/..."`. | Wrap `pwd`/`grp` in try/except and skip POSIX checks when unavailable. Use `PurePosixPath` in `recommended_paths()` so user-scope strings are always POSIX (the deployment target is always Linux VPS). |
| 3 | Test fixtures contained literal token-shaped strings (`ghp_AAAA…`, `github_pat_DDDD…`) which trigger gitleaks / GitHub push-protection / trufflehog on every push. The values are synthetic but their *shape* is real-credential-shaped. | New `tests/_token_fixtures.py` constructs prefixes at runtime from disjoint fragments (`g + h + p + _`). Reassembled values still match the application redaction regex, but the source files no longer contain credential-shaped literals. |
| 4 | Shipped templates (`infra/env/*`, `infra/systemd/...`, `.env.example`) only documented `/etc/umbral/...` paths. That's correct for system-scope hosts but misleading for Rick's deployment, which actually uses user-scope `~/.config/openclaw/...` (staged in F6 step 6B). | Add comment blocks to all four files clarifying that user-scope is canonical for Rick; `/etc/umbral` is the system-scope fallback example. No actual paths shipped were changed. |

---

## Files changed

### Code
- `worker/tasks/copilot_cli.py`
  - Added `_HARDCODED_ALLOWED_REPO_ROOTS`, `_REPO_ROOTS_ENV` (`COPILOT_CLI_ALLOWED_REPO_ROOTS`), `_ALLOWED_REPO_ROOTS_OVERRIDE`.
  - Added `set_allowed_repo_roots_for_test()` test helper.
  - Added `_allowed_repo_roots()` (resolves + filters to existing dirs + merges env override).
  - Added `_validate_repo_path(raw)` raising `_ValidationError` with codes `repo_path_not_resolved`, `repo_path_not_found`, `repo_path_not_directory`, `repo_path_not_allowed`.
  - Wired `_validate_repo_path` into `_validate_input` immediately after the type check; the validated input now contains the canonical path string.
  - `_REAL_EXECUTION_IMPLEMENTED` **stays `False`**. No subprocess. No new I/O.

- `scripts/verify_copilot_cli_env_contract.py`
  - `import pwd` / `import grp` now under try/except → `_POSIX = False` on Windows.
  - `_resolve_owner_group()` returns `(None, None)` when `_POSIX is False`.
  - `check_perms()` is a no-op on non-POSIX.

- `scripts/plan_copilot_cli_live_staging.py`
  - `from pathlib import Path, PurePosixPath`.
  - `recommended_paths()` for user scope builds `dropin_dir` and `dropin_file` via `PurePosixPath` so output is always slash-separated.

### Tests
- `tests/_token_fixtures.py` (new) — `classic_pat()`, `server_token()`, `fine_grained_pat()`, `openai_key()`, `all_synthetic_tokens()`.
- `tests/test_copilot_cli.py`
  - Imports the new fixtures + `set_allowed_repo_roots_for_test`.
  - Replaced literal `ghp_AAAA…` / `Bearer abcdef…` strings with runtime-built equivalents.
  - Added `_sandbox_repo_root` autouse fixture that allowlists a tmp dir and `_publish_sandbox_repo_path` so `_ok_input` defaults to a real, allowlisted directory.
  - Added 8 new tests for `_validate_repo_path` (accepts root, accepts descendant, rejects `/`, rejects `/home/rick`, rejects nonexistent, rejects regular file, rejects `..` traversal, rejects symlink escape) plus a handler-level integration test asserting `error == "repo_path_not_allowed"`.
- `tests/test_verify_copilot_cli_env_contract.py`
  - Replaced 4 literal token strings with helper-built equivalents.
- `tests/test_plan_copilot_cli_live_staging.py`
  - Replaced 1 literal `github_pat_DO_NOT_LEAK_…` with `fine_grained_pat()`.

### Docs / templates
- `.env.example` — added user-scope canonical block, kept `/etc/umbral/*` as fallback note.
- `infra/env/copilot-cli.env.example` — clarified target paths.
- `infra/env/copilot-cli-secrets.env.example` — clarified target paths.
- `infra/systemd/umbral-worker-copilot-cli.conf.example` — added "two deployment scopes" header pointing operators at user-scope for Rick's VPS.
- `docs/copilot-cli-capability-design.md` — added D26 + §11 row `F6.step6C-4B-fixup`.

---

## Validation

### Tests
```
WORKER_TOKEN=test python -m pytest \
  tests/test_copilot_cli.py \
  tests/test_rick_tech_agent.py \
  tests/test_verify_copilot_egress_contract.py \
  tests/test_copilot_egress_resolver.py \
  tests/test_verify_copilot_cli_env_contract.py \
  tests/test_plan_copilot_cli_live_staging.py \
  -q
```
Result: **141 passed** (was 132 — +9 from the new repo_path test class).

### `git diff --check`
Clean.

### Secret scan against `origin/main...HEAD`

Scanning the **current tree** (post-fixup state) for token-shaped literals introduced by PR #269:

```
git ls-files | xargs grep -lE 'ghp_[A-Za-z0-9]{20}|github_pat_[A-Za-z0-9]{30}|ghs_[A-Za-z0-9]{20}'
```

Result: **0 PR-269 files match**. The only matches in the working tree are pre-existing `main`-branch files unrelated to this PR:
- `tests/test_github.py` (pre-existing GitHub task tests)
- `tests/test_hardening.py` (pre-existing redaction tests)
- `docs/34-rick-github-token-setup.md` (pre-existing setup runbook)

Scanning the **fixup diff itself** (this commit's added lines):

```
git diff HEAD~1 -- 'tests/' 'scripts/' 'worker/' 'infra/' '.env.example' 'docs/' \
  | grep -E '^\+' \
  | grep -iE 'ghp_[A-Za-z0-9]{20}|github_pat_[A-Za-z0-9]{30}|ghs_[A-Za-z0-9]{20}|sk-[A-Za-z0-9]{20}'
```

Result: **0 matches**.

> **Note on commit history**: earlier commits in PR #269 (before this fixup) did contain
> the literal token-shaped strings. Removing them from history would require a
> force-push, which is forbidden by the operator's hard rules. GitHub's push
> protection inspects each commit, but the *tree* visible in the PR's tip is
> clean post-fixup; reviewers can confirm via `git ls-files | xargs grep -lE …`
> on the merge tip.

---

## Invariants — all verified, none flipped

| Invariant | Required | Observed |
|---|---|---|
| `config/tool_policy.yaml :: copilot_cli.enabled` | `false` | `false` |
| `worker/tasks/copilot_cli.py :: _REAL_EXECUTION_IMPLEMENTED` | `False` | `False` |
| `~/.config/openclaw/copilot-cli.env :: RICK_COPILOT_CLI_EXECUTE` | `false` | `false` |
| `config/tool_policy.yaml :: copilot_cli.egress.activated` | `false` | `false` |
| Live worker MainPID | unchanged from 6C-2 | `1114334` |
| Live worker `/health` | 200 | 200 |
| Live worktree `/home/rick/umbral-agent-stack` HEAD | `e6128bc` | `e6128bc` |
| Live worktree branch | `main` | `main` |
| nftables rules added | none | none |
| Docker network created | none | none |
| Notion mutated | no | no |
| Gates marked | no | no |
| Token printed | no | no |
| Token committed | no | no |
| Copilot real executed | no | no |
| `gh` CLI used by agent | no (still unauthenticated on VPS) | no |

---

## Final delivery

- **Branch:** `rick/copilot-cli-capability-design`
- **HEAD before fixup:** `b5641f9`
- **Files changed:** 11 (1 new, 10 modified)
- **Tests:** 141/141 green
- **Secret scan on diff:** 0 hits
- **Live worker touched:** no
- **Worker restarted:** no
- **Flags changed:** no
- **Token printed:** no
- **Copilot real executed:** no
- **PR #269:** still draft, awaiting human review with these review-feedback items resolved.
- **Next recommended step:** human reviewer re-runs the 8-item PR checklist and decides on merge.
