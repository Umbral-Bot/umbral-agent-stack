# Browser Named Page ID Fix Validation — 2026-03-12

## Context

Rick hit a real browser bug when trying to reuse a custom `page_id` via
`umbral_browser_navigate` and `umbral_browser_read_page`.

Observed failure before the fix:

- `browser.navigate` with a new named `page_id` returned `400`
- `browser.read_page` with that same `page_id` also failed
- interactive worker log showed:
  - `Unknown page_id: talana-fix`

## Root cause

`worker/browser/manager.py` only created a page when `page_id` was omitted.
If a caller supplied a new custom `page_id`, `_get_page_ref(..., create=True)`
still raised `ValueError` instead of creating a named page handle.

## Fix

Updated browser manager behavior:

- `_create_page()` now accepts an optional `page_id`
- `_get_page_ref(..., create=True)` now creates the page when a missing custom
  `page_id` is provided

Also kept the prior plugin-side routing fix in place so `umbral_browser_*`
continues going to the interactive VM worker (`8089`) instead of the generic
VM worker (`8088`).

## Validation

### Local tests

Executed:

```bash
python -m pytest tests/test_browser_manager.py tests/test_browser_tasks.py tests/test_gui_tasks.py -q
```

Result:

- `23 passed`

### Direct interactive worker validation

After deploying `worker/browser/manager.py` to the VM repo and restarting the
interactive worker via the scheduled task `StartInteractiveWorkerHiddenNow`,
these calls succeeded against `WORKER_URL_VM_INTERACTIVE`:

1. `browser.navigate` to `https://example.com` with `page_id=talana-fix-direct`
2. `browser.navigate` to `https://example.org` with the same `page_id`
3. `browser.read_page` with the same `page_id`

Observed result:

- first navigate: `ok=true`, `url=https://example.com/`
- second navigate: `ok=true`, `url=https://example.org/`
- read page: `ok=true`, `url=https://example.org/`

### Rick path validation

Executed through `main` with OpenClaw:

- `umbral_browser_navigate(page_id=talana-fix, url=https://example.com)`
- `umbral_browser_navigate(page_id=talana-fix, url=https://example.org)`
- `umbral_browser_read_page(page_id=talana-fix)`

Observed response:

- `ok`

This confirms the bug is fixed through the same gateway/plugin path used by
Rick.

## Deployment notes

- VM repo updated at:
  - `C:\GitHub\umbral-agent-stack\worker\browser\manager.py`
- interactive worker restarted via scheduled task:
  - `StartInteractiveWorkerHiddenNow`

## Conclusion

The original `Unknown page_id` bug is fixed and validated:

- locally
- directly against the interactive worker
- through Rick's real `main` tool path
