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
```

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
