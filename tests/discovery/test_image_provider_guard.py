"""Tests for scripts/discovery/lib/image_provider_guard.py (B4 containment).

Proves the fail-closed contract: the direct Google Image path runs ONLY when
both flags are set; the default (magnific, not wired) degrades to a documented
no-op via ImageProviderContained.
"""
from __future__ import annotations

import pytest

from scripts.discovery.lib import image_provider_guard as guard

GOOGLE_ON = {
    "RICK_STAGE8_IMAGE_PROVIDER": "google",
    "RICK_STAGE8_GOOGLE_IMAGE_ENABLED": "true",
}


# ---------- resolve_provider ----------

def test_default_provider_is_magnific():
    assert guard.resolve_provider({}) == guard.PROVIDER_MAGNIFIC


def test_provider_reads_flag_lowercased():
    assert guard.resolve_provider({"RICK_STAGE8_IMAGE_PROVIDER": "GOOGLE"}) == "google"


# ---------- google_direct_enabled (fail-closed) ----------

@pytest.mark.parametrize("val", ["true", "1", "yes", "on"])
def test_google_enable_truthy(val):
    assert guard.google_direct_enabled({"RICK_STAGE8_GOOGLE_IMAGE_ENABLED": val}) is True


@pytest.mark.parametrize("val", ["false", "0", "", "nope"])
def test_google_enable_non_truthy(val):
    assert guard.google_direct_enabled({"RICK_STAGE8_GOOGLE_IMAGE_ENABLED": val}) is False


def test_google_enable_missing_is_false():
    assert guard.google_direct_enabled({}) is False


# ---------- assert_generation_allowed ----------

def test_default_magnific_is_contained_noop():
    with pytest.raises(guard.ImageProviderContained) as ei:
        guard.assert_generation_allowed({})
    assert ei.value.reason == "magnific_not_wired"


def test_google_without_enable_flag_is_contained():
    with pytest.raises(guard.ImageProviderContained) as ei:
        guard.assert_generation_allowed({"RICK_STAGE8_IMAGE_PROVIDER": "google"})
    assert ei.value.reason == "google_direct_disabled"


def test_google_with_both_flags_returns_google():
    assert guard.assert_generation_allowed(GOOGLE_ON) == guard.PROVIDER_GOOGLE


def test_unknown_provider_is_contained():
    with pytest.raises(guard.ImageProviderContained) as ei:
        guard.assert_generation_allowed({"RICK_STAGE8_IMAGE_PROVIDER": "freepik"})
    assert ei.value.reason == "provider_unavailable"


def test_contained_is_runtimeerror_subclass():
    # So existing broad `except Exception` paths still catch it.
    assert issubclass(guard.ImageProviderContained, RuntimeError)
