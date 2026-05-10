"""Runtime flags contract for the publish path (Wave 2.A / #405).

Centralized, fail-closed evaluation of the four environment-driven flags
that gate any real publication attempt:

* ``PUBLISH_ENABLED`` — master kill switch (default ``false``).
* ``DRY_RUN`` — when ``true`` no real network write is permitted
  (default ``true``).
* ``MAX_POSTS`` — hard cap on real publishes per execution
  (default ``1``).
* ``MAX_POSTS_PER_DAY`` — hard cap on real publishes per UTC day
  (default ``1``); enforcement against ``published_history`` lands with
  #404-lite.

Defaults are chosen so that, with NO env vars set, ``allows_real_publish``
returns ``False``. Garbage values never raise — they fall to defaults and
emit a warning.

See ``docs/editorial-pipeline/runtime-flags-contract.md`` for the full
contract.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Mapping, Optional

__all__ = ["PublishFlags"]

_LOG = logging.getLogger(__name__)

_TRUTHY: frozenset[str] = frozenset({"1", "true", "yes", "on"})
_FALSY: frozenset[str] = frozenset({"0", "false", "no", "off", ""})

DEFAULT_PUBLISH_ENABLED = False
DEFAULT_DRY_RUN = True
DEFAULT_MAX_POSTS = 1
DEFAULT_MAX_POSTS_PER_DAY = 1


def _parse_bool(raw: Optional[str], default: bool, *, name: str) -> bool:
    """Parse a bool flag fail-closed.

    Missing / empty / unparseable values fall back to ``default``.
    Truthy: ``1 true yes on`` (case-insensitive). All else is ``false``.
    """
    if raw is None:
        return default
    val = raw.strip().lower()
    if val == "":
        return default
    if val in _TRUTHY:
        return True
    if val in _FALSY:
        return False
    _LOG.warning(
        "publish_flags: unparseable bool for %s=%r — falling back to default=%s",
        name,
        raw,
        default,
    )
    return default


def _parse_int(
    raw: Optional[str], default: int, *, name: str, min_value: int = 0
) -> int:
    """Parse a non-negative int flag fail-closed.

    Missing / empty / non-integer / below ``min_value`` falls back to
    ``default``. ``0`` is a valid value (means "no publishes permitted").
    """
    if raw is None:
        return default
    val = raw.strip()
    if val == "":
        return default
    try:
        parsed = int(val)
    except ValueError:
        _LOG.warning(
            "publish_flags: unparseable int for %s=%r — falling back to default=%d",
            name,
            raw,
            default,
        )
        return default
    if parsed < min_value:
        _LOG.warning(
            "publish_flags: %s=%d below min_value=%d — falling back to default=%d",
            name,
            parsed,
            min_value,
            default,
        )
        return default
    return parsed


@dataclass(frozen=True)
class PublishFlags:
    """Immutable snapshot of the publish-path runtime flags."""

    publish_enabled: bool
    dry_run: bool
    max_posts: int
    max_posts_per_day: int

    @classmethod
    def from_env(
        cls, env: Optional[Mapping[str, str]] = None
    ) -> "PublishFlags":
        """Build a :class:`PublishFlags` from a mapping (defaults to ``os.environ``).

        Never raises; unparseable values fall back to defaults.
        """
        source: Mapping[str, str] = os.environ if env is None else env
        return cls(
            publish_enabled=_parse_bool(
                source.get("PUBLISH_ENABLED"),
                DEFAULT_PUBLISH_ENABLED,
                name="PUBLISH_ENABLED",
            ),
            dry_run=_parse_bool(
                source.get("DRY_RUN"),
                DEFAULT_DRY_RUN,
                name="DRY_RUN",
            ),
            max_posts=_parse_int(
                source.get("MAX_POSTS"),
                DEFAULT_MAX_POSTS,
                name="MAX_POSTS",
            ),
            max_posts_per_day=_parse_int(
                source.get("MAX_POSTS_PER_DAY"),
                DEFAULT_MAX_POSTS_PER_DAY,
                name="MAX_POSTS_PER_DAY",
            ),
        )

    def allows_real_publish(self) -> bool:
        """Return True only if a real publish may proceed.

        Equivalent to ``publish_enabled AND not dry_run AND max_posts > 0``.

        Note: ``max_posts_per_day`` is intentionally NOT part of this
        decision; its enforcement requires ``published_history`` rows and
        lands with #404-lite.
        """
        return (
            self.publish_enabled
            and not self.dry_run
            and self.max_posts > 0
        )
