# Registry backup alert runbook

## Scope

This runbook covers the repo-side health check that alerts when the Windows registry backup fails on 2 consecutive calendar days. It does not install Task Scheduler jobs, change the backup destination repo, or modify VPS/OpenClaw runtime.

## Current scheduler pointer

- Scheduled task name: `UmbralRegistryBackupDaily`
- Canonical PowerShell entrypoint lives in the separate `notion-governance` repo:
  - `scripts/daily-registry-backup.ps1`
  - `scripts/registry-backup.ps1`
- Expected log folder on Windows: `%LOCALAPPDATA%\umbral-registry-backup\`

This repository only ships the alert checker that reads those logs.

## Manual alert check

### Default Windows path

```powershell
cd C:\path\to\umbral-agent-stack
python scripts/registry/check_backup_alert.py
```

### Override log directory

Use this when testing with fixtures or when the logs were copied elsewhere:

```powershell
$env:UMBRAL_REGISTRY_BACKUP_LOG_DIR = "C:\temp\umbral-registry-backup"
python scripts/registry/check_backup_alert.py
```

Behavior:

- Exit code `0`: no 2-day failure streak detected.
- Exit code `1`: alert condition detected.
- Output is a single-line summary safe to consume from CI or a wrapper script.

## Human response when alert fires

1. Confirm the two dates named in the alert summary and open the corresponding files under `%LOCALAPPDATA%\umbral-registry-backup\`.
2. Check Windows Task Scheduler for `UmbralRegistryBackupDaily`:
   - last run time
   - last run result
   - history tab entries for the two failed days
3. Re-run the canonical backup manually from the `notion-governance` repo on the Windows host:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\daily-registry-backup.ps1
```

4. If the manual run fails, inspect the log output and the underlying git/auth problem before retrying. Common causes are expired credentials, remote push rejection, or local checkout drift.
5. If the manual run succeeds, keep the alert result as evidence, then wait for the next scheduled daily run to confirm the streak is broken.
6. If failures continue after manual validation, escalate to the human owner before changing scheduler configuration or backup architecture.

## Notes

- The checker treats either an explicit `FAIL` marker or a non-zero exit code in a log as a failed daily run.
- Tests must use `UMBRAL_REGISTRY_BACKUP_LOG_DIR` or fixture paths only; do not point CI at a real `%LOCALAPPDATA%` directory.
