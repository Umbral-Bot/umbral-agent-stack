# Registry Backup Alert Runbook

## Scope

This runbook covers the post-MVP O2 alert check for the Windows registry backup.
It does not install or modify the backup task, backup destination, Notion, MCP, or
VPS runtime.

Canonical backup implementation lives in the `notion-governance` repo:

- `scripts/registry-backup.ps1`
- `scripts/daily-registry-backup.ps1`
- `scripts/install-registry-backup-task.ps1`

## Current Scheduler

The existing Windows Task Scheduler task is:

```powershell
UmbralRegistryBackupDaily
```

It is installed by `notion-governance/scripts/install-registry-backup-task.ps1` and
runs daily at 03:00 as the interactive Windows user. The action invokes:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<notion-governance>\scripts\daily-registry-backup.ps1"
```

The daily runner writes transcripts under:

```powershell
%LOCALAPPDATA%\umbral-registry-backup\
```

The expected file name shape is:

```text
run-YYYY-MM-DDTHHmmss.log
```

Successful runs print `OK`. Failed runs print `FAIL: ...` and exit non-zero.

## Manual Alert Check

From `umbral-agent-stack`:

```powershell
python scripts/registry/registry_backup_alert.py
```

For diagnostics or tests, override the log directory:

```powershell
python scripts/registry/registry_backup_alert.py --log-dir "C:\path\to\logs"
```

or:

```powershell
$env:UMBRAL_REGISTRY_BACKUP_LOG_DIR = "C:\path\to\logs"
python scripts/registry/registry_backup_alert.py
```

Exit codes:

| Exit | Meaning |
|---|---|
| `0` | No alert condition detected. |
| `2` | Two consecutive daily failures detected. |

The alert output is a single line and does not include raw log content.

## Alert Response

When the script exits `2`:

1. Do not change the backup destination or scheduled task automatically.
2. Inspect the latest two logs in `%LOCALAPPDATA%\umbral-registry-backup\`.
3. Run the backup manually from `notion-governance`:

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\daily-registry-backup.ps1
   ```

4. If the manual run fails, classify the failure:
   - backup repo unavailable
   - source script missing
   - registry backup script failure
   - git add/commit/push failure
5. Apply a human-approved fix only after identifying the failure class.
6. Re-run the alert check and confirm it returns `0`.

## CI Contract

Tests use fixture logs only. They must not read real Windows registry backup paths,
real `%LOCALAPPDATA%`, backup repos, Notion, or VPS state.
