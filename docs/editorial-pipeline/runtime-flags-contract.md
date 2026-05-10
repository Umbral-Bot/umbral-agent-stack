# Runtime flags contract — publish path

**Issue**: #405
**Wave**: 2.A
**Status**: draft

## Purpose

Centralize evaluation of runtime flags that gate any publication attempt.
Fail-closed by default. Single source of truth consumed by S10
`publish_guard` and any future publisher.

## Flags

| Flag | Type | Default | Semantics |
|---|---|---|---|
| `PUBLISH_ENABLED` | bool | `false` | Master kill switch. If false, no publish attempt may proceed past `publish_guard`. |
| `DRY_RUN` | bool | `true` | If true, `publish_guard` may evaluate gates and produce candidates but no real network write to the publish target is permitted. |
| `MAX_POSTS` | int | `1` | Hard cap on real publishes per single execution. `0` is allowed (means "no publishes permitted"). |
| `MAX_POSTS_PER_DAY` | int | `1` | Hard cap on real publishes per UTC day, enforced via `published_history`. `0` is allowed. |

## Bool parsing

Accepted truthy values (case-insensitive): `1`, `true`, `yes`, `on`.
Anything else → `false` (fail-closed).
Missing env var → default value.
Empty string → default value.
Unparseable → log + default value (NEVER raise on parse).

## Int parsing

Accepted: non-negative integers only. `0` is allowed (means "no publishes
permitted").
Negative or non-integer → log + default value (fail-closed).
Missing env var → default value.
Empty string → default value.

## Public API

`scripts/discovery/lib/publish_flags.py`:

```python
@dataclass(frozen=True)
class PublishFlags:
    publish_enabled: bool
    dry_run: bool
    max_posts: int
    max_posts_per_day: int

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "PublishFlags": ...

    def allows_real_publish(self) -> bool:
        """True only if publish_enabled AND not dry_run AND max_posts > 0."""

    def block_reasons(self) -> list[str]:
        """Ordered subset of {publish_disabled, dry_run_enabled, max_posts_zero}.

        Empty when allows_real_publish() is True. Consumed verbatim by
        publish_guard.assert_can_publish to populate the
        publish_guard.runtime_block ops_log event and the raised
        PublishBlockedError.reasons.
        """

    def cross_validation_warnings(self) -> list[str]:
        """Non-blocking diagnostic codes for suspicious flag combinations.

        Codes (stable):
          - publish_with_dry_run        # PUBLISH_ENABLED=true AND DRY_RUN=true
          - publish_with_zero_cap       # PUBLISH_ENABLED=true AND MAX_POSTS=0
          - daily_cap_below_per_run     # MAX_POSTS_PER_DAY < MAX_POSTS
          - daily_cap_not_enforced      # informational; #404-lite owns enforcement
        """
```

## Stop-button semantics (Wave 2.A / #405 hardening)

`publish_guard.assert_can_publish(..., flags=flags)` is the single
chokepoint between the editorial pipeline and any real publish target.

* **`flags=None` (legacy)** — byte-identical to the pre-#405 version:
  evaluates the 6 editorial gates and either `publish_guard.pass` or
  `publish_guard.block`. Verified by
  `tests/discovery/test_publish_guard_flags_integration.py::test_call_without_flags_preserves_legacy_behavior`.
* **`flags` explicit AND `flags.allows_real_publish() is False`** —
  raises `PublishBlockedError(reasons=flags.block_reasons(), ...)`
  BEFORE evaluating editorial gates or touching the DB. Emits exactly
  one `publish_guard.runtime_block` ops_log entry that echoes the parsed
  flags and the cross-validation warning codes for forensics.
  This is the **active stop button**: not a passive marker.
* **`flags` explicit AND `flags.allows_real_publish() is True`** — falls
  through to the gates path; outcome is `publish_guard.pass` or
  `publish_guard.block` exactly like the legacy path.

## `MAX_POSTS_PER_DAY` is NOT enforced in #405

`MAX_POSTS_PER_DAY` is parsed and exposed for visibility, but
`allows_real_publish()` and `block_reasons()` deliberately ignore it.
Real daily-cap enforcement requires querying `published_history` rows by
UTC day, which depends on the `publication_content_hash` schema (#402)
and the `publish_log.jsonl` (#404-lite). Until both land, treat
`MAX_POSTS_PER_DAY` as a configuration hint, NOT an operational
guarantee. `cross_validation_warnings()` emits `daily_cap_not_enforced`
on every call as a permanent reminder.

## Consumers

- S10 `publish_guard` (`scripts/discovery/lib/publish_guard.py`).
- Any future publisher (LinkedIn, blog, X, newsletter).

## Fail-closed semantics

If `from_env` cannot determine any flag with confidence, that flag falls to
its default. Defaults are chosen so the system NEVER publishes by accident:

- `PUBLISH_ENABLED=false` blocks every real write at the guard.
- `DRY_RUN=true` blocks every real write at the guard, even if the kill
  switch is on.
- `MAX_POSTS=1` and `MAX_POSTS_PER_DAY=1` cap blast radius even if both
  switches above are intentionally enabled.

`allows_real_publish()` returns `True` only when ALL of the following hold:

1. `publish_enabled is True`
2. `dry_run is False`
3. `max_posts > 0`

`MAX_POSTS_PER_DAY` is intentionally NOT part of `allows_real_publish()`;
its enforcement requires `published_history` rows and lands with #404-lite.

## What this does NOT solve

- Real publish target wiring (blog, LinkedIn).
- Cron scheduling.
- Token rotation.
- Daily-cap enforcement against real `published_history` rows (only the
  contract; real enforcement closes when #402 `publication_content_hash`
  + #404-lite log are in place).
- Dashboard.
