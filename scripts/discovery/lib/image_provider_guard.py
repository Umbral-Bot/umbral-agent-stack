"""B4 containment — Stage 8 image-provider guard (fail-closed).

ADR-006 (update 2026-06-06) superseded the Vertex AI / ``gemini-3-pro-image``
provider with **Magnific** (via MCP, David's own subscription) as the primary
visual provider. ``stage8_image_generator.py`` still calls Google/Gemini
directly (``worker.tasks.google_image.handle_google_image_generate``). This
guard implements the security containment from
``docs/plans/tanda-b-security-execution-plan-2026-07-19.md`` §5.2:

* impede the **direct Google Image** call by default, and
* require the current provider (Magnific per ADR-006) — which is not wired
  in-repo yet (MCP / OAuth pending) — so stage8 degrades to a **documented
  no-op** until re-cabled.

Provider selection (fail-closed)
--------------------------------
* ``RICK_STAGE8_IMAGE_PROVIDER`` — default ``magnific`` (the ADR-006 provider).
* The legacy direct-Google path is a **double lock**: it runs only when
  ``RICK_STAGE8_IMAGE_PROVIDER=google`` **and**
  ``RICK_STAGE8_GOOGLE_IMAGE_ENABLED`` is truthy (default off). This mirrors
  the ``RICK_COPILOT_CLI_ENABLED`` / ``RICK_COPILOT_CLI_EXECUTE`` idiom.

When generation is contained, :func:`assert_generation_allowed` raises
:class:`ImageProviderContained`. Callers treat that as a documented no-op
(skip, do **not** mark the proposal failed), so a manual/accidental run never
hits Google. This file performs no network call and never prints a secret.
See ADR-006 (``docs/adr/ADR-006-capa-visual-editorial.md``).
"""

from __future__ import annotations

from typing import Mapping, Optional

__all__ = [
    "ImageProviderContained",
    "IMAGE_PROVIDER_FLAG",
    "GOOGLE_ENABLE_FLAG",
    "PROVIDER_MAGNIFIC",
    "PROVIDER_GOOGLE",
    "DEFAULT_PROVIDER",
    "resolve_provider",
    "google_direct_enabled",
    "assert_generation_allowed",
]

IMAGE_PROVIDER_FLAG = "RICK_STAGE8_IMAGE_PROVIDER"
GOOGLE_ENABLE_FLAG = "RICK_STAGE8_GOOGLE_IMAGE_ENABLED"

PROVIDER_MAGNIFIC = "magnific"
PROVIDER_GOOGLE = "google"
DEFAULT_PROVIDER = PROVIDER_MAGNIFIC

_TRUTHY: frozenset[str] = frozenset({"1", "true", "yes", "on"})


class ImageProviderContained(RuntimeError):
    """Raised when Stage 8 image generation is contained (no provider runs).

    Subclasses :class:`RuntimeError` so existing broad ``except Exception``
    paths still catch it, but callers that want the documented **no-op**
    semantics catch it explicitly and skip without marking the proposal failed.
    ``reason`` is a stable code; the message carries operator guidance.
    """

    def __init__(self, reason: str, message: str) -> None:
        self.reason = reason
        super().__init__(message)


def resolve_provider(env: Optional[Mapping[str, str]] = None) -> str:
    """Return the configured provider (lowercased). Default ``magnific``."""
    import os

    source: Mapping[str, str] = os.environ if env is None else env
    raw = (source.get(IMAGE_PROVIDER_FLAG) or "").strip().lower()
    return raw or DEFAULT_PROVIDER


def google_direct_enabled(env: Optional[Mapping[str, str]] = None) -> bool:
    """Return True only if the legacy direct-Google path is explicitly enabled.

    Fail-closed: missing / empty / unparseable → ``False``.
    """
    import os

    source: Mapping[str, str] = os.environ if env is None else env
    raw = source.get(GOOGLE_ENABLE_FLAG)
    if raw is None:
        return False
    return raw.strip().lower() in _TRUTHY


def assert_generation_allowed(
    env: Optional[Mapping[str, str]] = None,
) -> str:
    """Return the provider to use, or raise :class:`ImageProviderContained`.

    * ``google`` + ``RICK_STAGE8_GOOGLE_IMAGE_ENABLED`` truthy → returns
      ``"google"`` (legacy direct path explicitly re-enabled).
    * ``google`` without the enable flag → contained (direct Google blocked).
    * ``magnific`` (default) → contained no-op (provider not wired in-repo).
    * anything else → contained no-op.
    """
    provider = resolve_provider(env)
    if provider == PROVIDER_GOOGLE:
        if google_direct_enabled(env):
            return PROVIDER_GOOGLE
        raise ImageProviderContained(
            "google_direct_disabled",
            "stage8: direct Google Image call is contained — ADR-006 superseded "
            "Google/Gemini with Magnific. Set "
            f"{GOOGLE_ENABLE_FLAG}=true to force the legacy path (accepts the "
            "ADR-006 risk).",
        )
    if provider == PROVIDER_MAGNIFIC:
        raise ImageProviderContained(
            "magnific_not_wired",
            "stage8: Magnific is the ADR-006 provider but is not wired in-repo "
            "(MCP / OAuth pending). Documented no-op until re-cabled — use "
            "--dry-run or wire the Magnific adapter.",
        )
    raise ImageProviderContained(
        "provider_unavailable",
        f"stage8: image provider {provider!r} is not available; contained "
        "no-op (ADR-006).",
    )
