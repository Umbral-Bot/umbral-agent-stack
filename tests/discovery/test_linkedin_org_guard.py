"""Tests for scripts/discovery/lib/linkedin_org_guard.py (B4 containment).

Proves the fail-closed contract: a real LinkedIn POST is permitted ONLY when
all three criteria hold (endpoint /rest/posts, org author URN, enable flag),
and blocked otherwise with stable reason codes.
"""
from __future__ import annotations

import pytest

from scripts.discovery.lib import linkedin_org_guard as guard

ORG_URN = "urn:li:organization:123456"
PERSON_URN = "urn:li:person:rick"
PLACEHOLDER = "urn:li:person:__TODO_RESOLVE_AT_PUBLISH__"

ENABLED = {"RICK_LINKEDIN_ORG_PUBLISH_ENABLED": "true"}


# ---------- flag parsing (fail-closed) ----------

@pytest.mark.parametrize("val", ["true", "1", "yes", "on", "TRUE", "  On "])
def test_flag_truthy_values_enable(val):
    assert guard.org_publish_flag_enabled({"RICK_LINKEDIN_ORG_PUBLISH_ENABLED": val}) is True


@pytest.mark.parametrize("val", ["false", "0", "no", "off", "", "garbage", "maybe"])
def test_flag_non_truthy_values_disable(val):
    assert guard.org_publish_flag_enabled({"RICK_LINKEDIN_ORG_PUBLISH_ENABLED": val}) is False


def test_flag_missing_is_disabled():
    assert guard.org_publish_flag_enabled({}) is False


# ---------- allow-path: all three criteria hold ----------

def test_allowed_when_all_criteria_met():
    reasons = guard.org_publish_block_reasons(
        endpoint=guard.COMPANY_POSTS_PATH, author_urn=ORG_URN, env=ENABLED,
    )
    assert reasons == []
    # assert_* must not raise
    guard.assert_org_publish_allowed(
        endpoint=guard.COMPANY_POSTS_PATH, author_urn=ORG_URN, env=ENABLED,
    )


# ---------- block-path: each missing criterion ----------

def test_blocks_personal_endpoint_even_with_org_and_flag():
    reasons = guard.org_publish_block_reasons(
        endpoint=guard.PERSONAL_UGC_PATH, author_urn=ORG_URN, env=ENABLED,
    )
    assert reasons == ["endpoint_not_company_posts"]


def test_blocks_person_author():
    reasons = guard.org_publish_block_reasons(
        endpoint=guard.COMPANY_POSTS_PATH, author_urn=PERSON_URN, env=ENABLED,
    )
    assert reasons == ["author_not_organization_urn"]


def test_blocks_placeholder_author():
    reasons = guard.org_publish_block_reasons(
        endpoint=guard.COMPANY_POSTS_PATH, author_urn=PLACEHOLDER, env=ENABLED,
    )
    assert reasons == ["author_not_organization_urn"]


def test_blocks_empty_author():
    reasons = guard.org_publish_block_reasons(
        endpoint=guard.COMPANY_POSTS_PATH, author_urn="", env=ENABLED,
    )
    assert reasons == ["author_not_organization_urn"]


def test_blocks_flag_disabled_by_default():
    reasons = guard.org_publish_block_reasons(
        endpoint=guard.COMPANY_POSTS_PATH, author_urn=ORG_URN, env={},
    )
    assert reasons == ["org_publish_flag_disabled"]


def test_blocks_all_three_when_legacy_defaults():
    # The exact production posture today: personal endpoint, person URN, no flag.
    reasons = guard.org_publish_block_reasons(
        endpoint=guard.PERSONAL_UGC_PATH, author_urn=PERSON_URN, env={},
    )
    assert reasons == list(guard.ORG_BLOCK_REASONS)


def test_assert_raises_with_reasons():
    with pytest.raises(guard.OrgPublishBlockedError) as ei:
        guard.assert_org_publish_allowed(
            endpoint=guard.PERSONAL_UGC_PATH, author_urn=PERSON_URN, env={},
        )
    assert ei.value.reasons == list(guard.ORG_BLOCK_REASONS)


def test_reason_codes_are_stable_and_ordered():
    assert guard.ORG_BLOCK_REASONS == (
        "endpoint_not_company_posts",
        "author_not_organization_urn",
        "org_publish_flag_disabled",
    )
