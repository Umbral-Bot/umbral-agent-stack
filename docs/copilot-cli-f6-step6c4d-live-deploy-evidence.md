# F6 step 6C-4D — Live deploy evidence (post-merge of PR #269)

**Branch (this evidence):** `rick/copilot-cli-postmerge-evidence-6c4d`
**Base:** `main` at `e4de924` (merge commit of PR #269)
**Live worktree HEAD:** `e6128bc` → **`e4de924`**
**Live worker MainPID:** `1114334` → **`1124888`** (single restart)
**State after deploy:** capability **deployed live but locked at policy layer** — exactly the planned target.

---

## 1. Pre-deploy verification

```
$ git ls-remote origin refs/heads/main
e4de924e43f48da5509970cc04bbc5a5cf679a05  refs/heads/main

$ git fetch origin refs/heads/main:refs/remotes/origin/main
   e6128bc..e4de924  main  -> origin/main

$ git log --oneline -3 origin/main
e4de924 (origin/main) Merge pull request #269 from Umbral-Bot/rick/copilot-cli-capability-design
fa704e9 fix(copilot-cli): repair PR269 CI tests
f168608 fix(copilot-cli): harden PR269 pre-merge review findings

$ git merge-base --is-ancestor fa704e9 origin/main && echo YES
YES
```

### Diagnóstico de un susto previo (sin acción mutante)

Antes del merge real, mi `origin/rick/copilot-cli-capability-design` mostraba `181cbaa`
mientras GitHub UI mostraba `fa704e9`. Causa raíz:

```
$ git config --get-all remote.origin.fetch
+refs/heads/main:refs/remotes/origin/main
```

El `remote.origin.fetch` del repo principal (heredado por todos los worktrees, incluido
el live `/home/rick/umbral-agent-stack`) está **narrowed a `main`**. Por eso
`git fetch origin` nunca actualizaba refs `rick/*`. La autoridad real es
`git ls-remote origin <ref>` o un fetch explícito por refspec. Esto se documenta para
futura referencia operacional.

No se cambió la config; la operación funciona con explicit fetch cuando hace falta.

---

## 2. Pull en live worktree

```
$ cd /home/rick/umbral-agent-stack
$ git status --short
?? docs/ops/cand-003-ve-publication-options-run.md   # editorial untracked, preservado

$ git pull --ff-only origin main
…
 create mode 100644 worker/tasks/copilot_cli.py
 create mode 100644 tests/test_copilot_cli.py
 create mode 100644 scripts/verify_copilot_cli_env_contract.py
 …(40 files total, +7400 lines)

$ git rev-parse HEAD
e4de924e43f48da5509970cc04bbc5a5cf679a05

$ git status --short
?? docs/ops/cand-003-ve-publication-options-run.md   # still preserved
```

Pull was strict fast-forward. No merge commit, no conflicts. Editorial untracked
file preserved as required.

---

## 3. Single restart

```
$ systemctl --user restart umbral-worker.service

$ systemctl --user show umbral-worker.service -p MainPID -p ActiveState -p SubState
MainPID=1124888
ActiveState=active
SubState=running
```

Old MainPID `1114334` → new MainPID `1124888`. Exactly one restart. No further
restarts during this step.

---

## 4. Probes 1–6

### Probe 1 — `/health`

```
$ curl -s -o /dev/null -w 'http=%{http_code}\n' http://127.0.0.1:8088/health
http=200
```

### Probe 2 — `copilot_cli.run` is now registered AND blocked at policy

```
POST /run
{
  "task": "copilot_cli.run",
  "input": {
    "mission": "research",
    "prompt": "probe",
    "repo_path": "/home/rick/umbral-agent-stack",
    "dry_run": true,
    "max_wall_sec": 60,
    "metadata": {}
  }
}

Response (parsed):
{
  "ok": true,
  "task": "copilot_cli.run",
  "result": {
    "ok": false,
    "error": "capability_disabled",
    "capability": "copilot_cli",
    "reason": "policy_off",
    "would_run": false,
    "audit_log": "/home/rick/umbral-agent-stack/reports/copilot-cli/2026-04/8885ff32f20847bfaf66f903dba6c704.jsonl",
    "mission_run_id": "8885ff32f20847bfaf66f903dba6c704",
    "policy": {
      "env_enabled": true,
      "policy_enabled": false
    }
  }
}
```

State transition:

| Before deploy (worker on `e6128bc`) | After deploy (worker on `e4de924`) |
|---|---|
| `{"detail":"Unknown task: copilot_cli.run. Available: ['ping', 'notion.write_transcript', …]"}` | `{"ok":false,"error":"capability_disabled","reason":"policy_off","would_run":false}` |

The task is now registered → outer router accepts it. The policy gate
(`copilot_cli.enabled=false` in `config/tool_policy.yaml`) rejects before the
handler reaches subprocess, network, or token consumption.

### Probe 3 — Process env contains expected names only (no values printed)

```
$ tr '\0' '\n' < /proc/1124888/environ | awk -F= '{print $1}' | grep -E '^(COPILOT_GITHUB_TOKEN|RICK_COPILOT_CLI_ENABLED|RICK_COPILOT_CLI_EXECUTE)$' | sort -u
COPILOT_GITHUB_TOKEN
RICK_COPILOT_CLI_ENABLED
RICK_COPILOT_CLI_EXECUTE
```

Token name visible in process env (loaded from `~/.config/openclaw/copilot-cli-secrets.env`
via the user-scope drop-in). Token value never printed.

### Probe 4 — Invariants in repo + envfile

| Layer | Var / setting | Required | Observed |
|---|---|---|---|
| `config/tool_policy.yaml` | `copilot_cli.enabled` | `false` | `false` ✅ |
| `config/tool_policy.yaml` | `copilot_cli.egress.activated` | `false` | `false` ✅ |
| `worker/tasks/copilot_cli.py` | `_REAL_EXECUTION_IMPLEMENTED` | `False` | `False` ✅ |
| `~/.config/openclaw/copilot-cli.env` | `RICK_COPILOT_CLI_EXECUTE` | `false` | `false` ✅ |
| `~/.config/openclaw/copilot-cli.env` | `RICK_COPILOT_CLI_ENABLED` | `true` (only env-layer gate that's open) | `true` ✅ |

Net: env-layer says "Rick can ask the worker to consider this capability";
policy-layer + code-constant + execute-flag + egress all still say "no".

### Probe 5 — Network plane untouched

```
$ docker network ls | grep -i copilot
(no output)

$ sudo -n nft list ruleset | grep -i copilot
(no copilot rules)
```

No nft rules were applied. No Docker network was created. Egress would-be
profile in `infra/networking/copilot-egress.nft.example` remains a staged
artifact only.

### Probe 6 — Worker is on the merged code

```
$ git -C /home/rick/umbral-agent-stack rev-parse HEAD
e4de924e43f48da5509970cc04bbc5a5cf679a05

$ systemctl --user show umbral-worker.service -p MainPID --value
1124888

$ ls /home/rick/umbral-agent-stack/worker/tasks/copilot_cli.py
/home/rick/umbral-agent-stack/worker/tasks/copilot_cli.py        # exists
```

The handler module shipped in PR #269 is present in the live worktree, and the
worker process is running with code from this revision (the response payload
proves it — old code returned `Unknown task`).

---

## 5. Audit log inspection

```
$ ls -la /home/rick/umbral-agent-stack/reports/copilot-cli/2026-04/8885ff32f20847bfaf66f903dba6c704.jsonl
-rw-rw-r-- 1 rick rick 534 Apr 27 05:42 .../8885ff32f20847bfaf66f903dba6c704.jsonl

$ git -C /home/rick/umbral-agent-stack check-ignore reports/copilot-cli/2026-04/8885ff32f20847bfaf66f903dba6c704.jsonl
reports/copilot-cli/2026-04/8885ff32f20847bfaf66f903dba6c704.jsonl
# (gitignored: OK)

$ grep -E 'github_pat_|ghp_[A-Za-z0-9]{20}|ghs_[A-Za-z0-9]{20}|sk-[A-Za-z0-9]{20}' <log>
(no matches)
```

Structured contents (key names only):

```python
{
  'decision': 'capability_disabled_policy',
  'phase': 'F3',
  'task': 'copilot_cli.run',
  'mission': 'research',
  'repo_path': '/home/rick/umbral-agent-stack',
  'dry_run': True,
  'max_wall_sec': 60,
  'mission_run_id': '8885ff32f20847bfaf66f903dba6c704',
  'metadata_keys': [],
  'prompt_summary': '<redacted summary>',
  'policy': {
    'env_enabled': True,
    'policy_enabled': False,
    'execute_enabled': False,
    'real_execution_implemented': False,
    'phase_blocks_real_execution': True,
    'egress_activated': False,
    'missions_count': 4,
  },
  'ts': '2026-04-27T05:42:…+00:00',
}
```

Audit log is gitignored, contains the structural decision trace, and contains
no token-shaped strings.

---

## 6. Constraints honored

| Forbidden action | Status |
|---|---|
| Flip `copilot_cli.enabled` | not flipped — still `false` |
| Flip `RICK_COPILOT_CLI_EXECUTE` | not flipped — still `false` |
| Flip `_REAL_EXECUTION_IMPLEMENTED` | not flipped — still `False` |
| Activate `copilot_cli.egress` | not activated — `activated: false` |
| Copilot HTTPS | none — handler rejected before subprocess |
| nftables changes | none |
| Docker network creation | none |
| Notion / gates / publish | none |
| Additional restart | none — exactly one restart |
| Token printed | no — only names read from `/proc/<pid>/environ` |
| Token committed | no |
| Force-push / reset | none |
| Operations on live `/home/rick/umbral-agent-stack` outside `git pull --ff-only` | none |

---

## 7. Final state

| | Pre-deploy | Post-deploy |
|---|---|---|
| Live worktree HEAD | `e6128bc` | **`e4de924`** |
| Live worker MainPID | `1114334` | **`1124888`** |
| `/health` | 200 | 200 |
| `copilot_cli.run` HTTP probe | `Unknown task` | **`capability_disabled / policy_off`** |
| Untracked editorial file | preserved | preserved |
| Capability flags | all closed except none open at code/policy/execute/egress; env `RICK_COPILOT_CLI_ENABLED=true` since 6C-2 | unchanged |

**Net:** capability is **deployed live** (route present, handler reachable,
token loaded) but **locked at the policy layer** (master switch `false`),
the execute layer (`RICK_COPILOT_CLI_EXECUTE=false`), the code-constant
layer (`_REAL_EXECUTION_IMPLEMENTED=False`), and the egress layer
(`activated=false`). Any one of these still being false is enough to
prevent real Copilot HTTPS execution.

---

## 8. Validations on this evidence branch

- `git diff --check`: clean.
- Secret scan on diff: 0 hits.
- No additional restart triggered by writing this doc.
- No flag flipped by this doc.

## 9. Next recommended step

**F6 step 6C-4F (capability activation playbook, manual):** document the
exact 4-flag flip sequence (policy → execute → egress activate → code
constant) with rollback per flag, but DO NOT execute it. Activation
remains an explicit human decision per the F1 design.
