"""B4 containment — LinkedIn Company-page org-publish guard (fail-closed).

Single chokepoint that decides whether ``stage9c`` may perform a **real**
LinkedIn POST. It encodes the contract from ADR-009 (LinkedIn Company Page via
``POST /rest/posts`` with an ``urn:li:organization:*`` author) and the security
containment designed in
``docs/plans/tanda-b-security-execution-plan-2026-07-19.md`` §5.

Why this exists
---------------
``stage9c_linkedin_publish.py`` historically POSTs to the **personal** endpoint
``/v2/ugcPosts`` under an ``urn:li:person:*`` identity. ADR-009 superseded that:
publishing must target the Umbral **Company Page** through the org handler
``editorial.publish.linkedin_org`` — which does not exist yet. Until it does, a
manual/accidental invocation of stage9c must never publish under the legacy
personal identity. There is no cron/pipeline caller today, so the only risk is
manual mis-invocation; this guard closes it.

Contract (all three MUST hold for a real POST; otherwise block)
---------------------------------------------------------------
1. ``endpoint == "/rest/posts"``               (Company Posts API, not personal
                                                 ``/v2/ugcPosts``).
2. ``author`` starts with ``urn:li:organization:`` (resolved — not the
   placeholder, not ``urn:li:person:*``).
3. ``RICK_LINKEDIN_ORG_PUBLISH_ENABLED`` is truthy (default **off**).

Because this module reads the *same* endpoint constant stage9c uses for its
POST (``/v2/ugcPosts``), gate (1) can never hold in production today, so
``assert_org_publish_allowed`` always blocks the real POST and leaves
``--dry-run`` as the only path. The guard is fail-closed: unparseable / missing
flag values resolve to *disabled*.

This file performs **no** network call, reads **no** token, and never prints a
secret. See ADR-009 (``docs/adr/ADR-009-linkedin-company-api.md``).
"""

from __future__ import annotations

from typing import Mapping, Optional

__all__ = [
    "OrgPublishBlockedError",
    "LINKEDIN_ORG_PUBLISH_FLAG",
    "COMPANY_POSTS_PATH",
    "PERSONAL_UGC_PATH",
    "ORG_AUTHOR_URN_PREFIX",
    "PERSON_AUTHOR_URN_PREFIX",
    "ORG_BLOCK_REASONS",
    "org_publish_block_reasons",
    "org_publish_flag_enabled",
    "assert_org_publish_allowed",
]

# Env flag that must be explicitly enabled (default off) for a real org POST.
LINKEDIN_ORG_PUBLISH_FLAG = "RICK_LINKEDIN_ORG_PUBLISH_ENABLED"

# ADR-009 Company Posts endpoint vs the legacy personal UGC endpoint.
COMPANY_POSTS_PATH = "/rest/posts"
PERSONAL_UGC_PATH = "/v2/ugcPosts"

ORG_AUTHOR_URN_PREFIX = "urn:li:organization:"
PERSON_AUTHOR_URN_PREFIX = "urn:li:person:"

# Stable, ordered reason codes emitted on block (audit-grade).
ORG_BLOCK_REASONS: tuple[str, ...] = (
    "endpoint_not_company_posts",   # endpoint != /rest/posts
    "author_not_organization_urn",  # author is placeholder / personal / empty
    "org_publish_flag_disabled",    # RICK_LINKEDIN_ORG_PUBLISH_ENABLED not truthy
)

_TRUTHY: frozenset[str] = frozenset({"1", "true", "yes", "on"})


class OrgPublishBlockedError(Exception):
    """Raised when a real LinkedIn org POST is not permitted.

    ``reasons`` is the ordered subset of :data:`ORG_BLOCK_REASONS` explaining
    why the POST was blocked. Never carries a secret.
    """

    def __init__(self, reasons: list[str]) -> None:
        self.reasons = list(reasons)
        super().__init__(f"linkedin org publish blocked: reasons={self.reasons}")


def org_publish_flag_enabled(env: Optional[Mapping[str, str]] = None) -> bool:
    """Return True only if ``RICK_LINKEDIN_ORG_PUBLISH_ENABLED`` is truthy.

    Fail-closed: missing / empty / unparseable → ``False``.
    """
    import os

    source: Mapping[str, str] = os.environ if env is None else env
    raw = source.get(LINKEDIN_ORG_PUBLISH_FLAG)
    if raw is None:
        return False
    return raw.strip().lower() in _TRUTHY


def org_publish_block_reasons(
    *,
    endpoint: str,
    author_urn: str,
    env: Optional[Mapping[str, str]] = None,
) -> list[str]:
    """Return the ordered reason codes for why a real org POST is blocked.

    Empty list ⇒ a real POST is permitted (all three criteria hold).
    """
    reasons: list[str] = []
    if (endpoint or "").strip() != COMPANY_POSTS_PATH:
        reasons.append("endpoint_not_company_posts")
    if not (author_urn or "").strip().startswith(ORG_AUTHOR_URN_PREFIX):
        reasons.append("author_not_organization_urn")
    if not org_publish_flag_enabled(env):
        reasons.append("org_publish_flag_disabled")
    return reasons


def assert_org_publish_allowed(
    *,
    endpoint: str,
    author_urn: str,
    env: Optional[Mapping[str, str]] = None,
) -> None:
    """Raise :class:`OrgPublishBlockedError` unless all three criteria hold.

    No-op (returns ``None``) only when endpoint is the Company Posts path, the
    author is an ``urn:li:organization:*`` URN, and the enable flag is truthy.
    """
    reasons = org_publish_block_reasons(
        endpoint=endpoint, author_urn=author_urn, env=env,
    )
    if reasons:
        raise OrgPublishBlockedError(reasons)
