"""Runtime flags contract for the publish path (Wave 2.A / #405).

Centralized, fail-closed evaluation of the four environment-driven flags
that gate any real publication attempt:

* ``PUBLISH_ENABLED`` — master kill switch (default ``false``).
* ``DRY_RUN`` — when ``true`` no real network write is permitted
  (default ``true``).
* ``MAX_POSTS`` — hard cap on real publishes per execution
  (default ``1``).
* ``MAX_POSTS_PER_DAY`` — hard cap on real publishes per UTC day
  (default ``1``). NOT YET ENFORCED as a real daily cap: enforcement
  against ``published_history`` rows is deferred (out of #404-lite
  scope; lands with Wave 2.B or a follow-up issue). In #405 this flag
  is parsed and exposed for visibility, and a configuration warning is
  emitted if it is set inconsistently with ``MAX_POSTS``, but it MUST
  NOT be presented as an operational guarantee.

Defaults are chosen so that, with NO env vars set, ``allows_real_publish``
returns ``False``. Garbage values never raise — they fall to defaults and
emit a warning.

Public API
----------
* :class:`PublishFlags` — frozen dataclass snapshot.
* ``PublishFlags.from_env(env=None)`` — fail-closed builder.
* ``PublishFlags.allows_real_publish()`` — single-line predicate consumed
  by :mod:`publish_guard` and any future publisher.
* ``PublishFlags.block_reasons()`` — explicit, stable, audit-grade list
  of reason codes for why a real publish would be rejected. Empty when
  :meth:`allows_real_publish` is ``True``.
* ``PublishFlags.cross_validation_warnings()`` — non-blocking diagnostic
  warnings about suspicious flag combinations (e.g. ``PUBLISH_ENABLED``
  on while ``DRY_RUN`` also on, or ``MAX_POSTS_PER_DAY < MAX_POSTS``).

See ``docs/editorial-pipeline/runtime-flags-contract.md`` for the full
contract.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Mapping, Optional

__all__ = [
    "PublishFlags",
    "RUNTIME_BLOCK_REASONS",
    "CROSS_VALIDATION_CODES",
]

# Stable runtime block reasons (ordered, audit-grade).
# Consumed by ``publish_guard.assert_can_publish`` to populate the
# ``publish_guard.runtime_block`` event and the raised
# ``PublishBlockedError`` reasons list.
RUNTIME_BLOCK_REASONS: tuple[str, ...] = (
    "publish_disabled",   # PUBLISH_ENABLED=false
    "dry_run_enabled",    # DRY_RUN=true
    "max_posts_zero",     # MAX_POSTS <= 0
)

# Stable cross-validation warning codes (non-blocking).
CROSS_VALIDATION_CODES: tuple[str, ...] = (
    "publish_with_dry_run",       # PUBLISH_ENABLED=true AND DRY_RUN=true
    "publish_with_zero_cap",      # PUBLISH_ENABLED=true AND MAX_POSTS=0
    "daily_cap_below_per_run",    # MAX_POSTS_PER_DAY < MAX_POSTS
    "daily_cap_not_enforced",     # informational: enforcement deferred to #404-lite
)

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

        Never raises; unparseable values fall back to defaults. Suspicious
        but parseable combinations are logged via
        :meth:`cross_validation_warnings` once the snapshot is built.
        """
        source: Mapping[str, str] = os.environ if env is None else env
        flags = cls(
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
        for code in flags.cross_validation_warnings():
            _LOG.warning(
                "publish_flags: cross-validation warning %s "
                "(publish_enabled=%s dry_run=%s max_posts=%d max_posts_per_day=%d)",
                code,
                flags.publish_enabled,
                flags.dry_run,
                flags.max_posts,
                flags.max_posts_per_day,
            )
        return flags

    def allows_real_publish(self) -> bool:
        """Return True only if a real publish may proceed.

        Equivalent to ``publish_enabled AND not dry_run AND max_posts > 0``.

        Note: ``max_posts_per_day`` is intentionally NOT part of this
        decision; its enforcement against ``published_history`` rows is
        deferred (out of #404-lite scope; lands with Wave 2.B or a
        follow-up issue). See :meth:`cross_validation_warnings`
        ``daily_cap_not_enforced``.
        """
        return (
            self.publish_enabled
            and not self.dry_run
            and self.max_posts > 0
        )

    def block_reasons(self) -> list[str]:
        """Return ordered, stable reason codes for why real publish is blocked.

        Empty list when :meth:`allows_real_publish` is ``True``. Codes are
        drawn from :data:`RUNTIME_BLOCK_REASONS` and emitted verbatim by
        :func:`scripts.discovery.lib.publish_guard.assert_can_publish`
        in the ``publish_guard.runtime_block`` ops_log event and in the
        raised :class:`PublishBlockedError`.

        ``MAX_POSTS_PER_DAY`` is intentionally NOT a block reason in
        #405; see module docstring and :meth:`cross_validation_warnings`.
        """
        reasons: list[str] = []
        if not self.publish_enabled:
            reasons.append("publish_disabled")
        if self.dry_run:
            reasons.append("dry_run_enabled")
        if self.max_posts <= 0:
            reasons.append("max_posts_zero")
        return reasons

    def cross_validation_warnings(self) -> list[str]:
        """Return non-blocking diagnostic codes for suspicious combinations.

        These are emitted as ``logging.WARNING`` from :meth:`from_env`
        and re-emitted by ``publish_guard`` so an operator notices
        configurations that parse cleanly but are inconsistent.

        Codes (stable, drawn from :data:`CROSS_VALIDATION_CODES`):

        * ``publish_with_dry_run`` — ``PUBLISH_ENABLED=true`` while
          ``DRY_RUN=true``. Defensive: real publish still blocked, but the
          intent looks contradictory.
        * ``publish_with_zero_cap`` — ``PUBLISH_ENABLED=true`` while
          ``MAX_POSTS=0``. Hard stop, but the operator probably meant
          ``MAX_POSTS>=1``.
        * ``daily_cap_below_per_run`` — ``MAX_POSTS_PER_DAY < MAX_POSTS``.
          Operator may believe the daily cap already applies; in #405 it
          does not (see ``daily_cap_not_enforced``).
        * ``daily_cap_not_enforced`` — informational reminder that
          ``MAX_POSTS_PER_DAY`` parsing is wired but enforcement against
          ``published_history`` lands with #404-lite.
        """
        warnings: list[str] = []
        if self.publish_enabled and self.dry_run:
            warnings.append("publish_with_dry_run")
        if self.publish_enabled and self.max_posts == 0:
            warnings.append("publish_with_zero_cap")
        if self.max_posts_per_day < self.max_posts:
            warnings.append("daily_cap_below_per_run")
        # Always informational until daily-cap enforcement lands
        # (out of #404-lite scope; deferred to Wave 2.B or follow-up).
        warnings.append("daily_cap_not_enforced")
        return warnings
