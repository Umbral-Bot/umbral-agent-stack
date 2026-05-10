"""Unit tests for ``scripts.discovery.lib.publish_flags`` (Wave 2.A / #405).

Coverage:
* Defaults when env is empty / vars missing.
* Bool truthy/falsy variants for every bool flag.
* Int parsing: valid, ``0``, negative, non-numeric, empty.
* ``allows_real_publish`` matrix.
* Garbage values never raise.
* Explicit ``env`` injection (no monkeypatching of ``os.environ``).
"""

from __future__ import annotations

import logging

import pytest

from scripts.discovery.lib.publish_flags import (
    DEFAULT_DRY_RUN,
    DEFAULT_MAX_POSTS,
    DEFAULT_MAX_POSTS_PER_DAY,
    DEFAULT_PUBLISH_ENABLED,
    PublishFlags,
)


# --------------------------------------------------------------------------- #
# Defaults / fail-closed
# --------------------------------------------------------------------------- #

def test_defaults_when_env_is_empty():
    flags = PublishFlags.from_env({})
    assert flags.publish_enabled is DEFAULT_PUBLISH_ENABLED is False
    assert flags.dry_run is DEFAULT_DRY_RUN is True
    assert flags.max_posts == DEFAULT_MAX_POSTS == 1
    assert flags.max_posts_per_day == DEFAULT_MAX_POSTS_PER_DAY == 1
    assert flags.allows_real_publish() is False


def test_defaults_are_fail_closed_for_publish():
    """With NO env vars set, real publish must be impossible."""
    assert PublishFlags.from_env({}).allows_real_publish() is False


def test_dataclass_is_frozen():
    flags = PublishFlags.from_env({})
    with pytest.raises(Exception):  # FrozenInstanceError
        flags.publish_enabled = True  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# Bool parsing — truthy variants
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("raw", ["1", "true", "TRUE", "True", "yes", "YES", "on", "ON"])
def test_publish_enabled_truthy_variants(raw):
    flags = PublishFlags.from_env({"PUBLISH_ENABLED": raw})
    assert flags.publish_enabled is True


@pytest.mark.parametrize("raw", ["1", "true", "yes", "on"])
def test_dry_run_truthy_variants(raw):
    flags = PublishFlags.from_env({"DRY_RUN": raw})
    assert flags.dry_run is True


# --------------------------------------------------------------------------- #
# Bool parsing — falsy variants
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("raw", ["0", "false", "FALSE", "no", "NO", "off", "OFF"])
def test_publish_enabled_falsy_variants(raw):
    flags = PublishFlags.from_env({"PUBLISH_ENABLED": raw})
    assert flags.publish_enabled is False


@pytest.mark.parametrize("raw", ["0", "false", "no", "off"])
def test_dry_run_falsy_variants(raw):
    flags = PublishFlags.from_env({"DRY_RUN": raw})
    assert flags.dry_run is False


def test_publish_enabled_empty_string_falls_to_default():
    flags = PublishFlags.from_env({"PUBLISH_ENABLED": ""})
    assert flags.publish_enabled is DEFAULT_PUBLISH_ENABLED


def test_dry_run_empty_string_falls_to_default():
    flags = PublishFlags.from_env({"DRY_RUN": ""})
    assert flags.dry_run is DEFAULT_DRY_RUN


@pytest.mark.parametrize("raw", ["maybe", "later", "potato", "  ", "2"])
def test_publish_enabled_garbage_falls_to_default(raw, caplog):
    with caplog.at_level(logging.WARNING):
        flags = PublishFlags.from_env({"PUBLISH_ENABLED": raw})
    assert flags.publish_enabled is DEFAULT_PUBLISH_ENABLED


@pytest.mark.parametrize("raw", ["sometimes", "kinda", "abc"])
def test_dry_run_garbage_falls_to_default(raw, caplog):
    with caplog.at_level(logging.WARNING):
        flags = PublishFlags.from_env({"DRY_RUN": raw})
    assert flags.dry_run is DEFAULT_DRY_RUN


# --------------------------------------------------------------------------- #
# Int parsing
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("raw,expected", [("0", 0), ("1", 1), ("5", 5), ("100", 100)])
def test_max_posts_valid_values(raw, expected):
    flags = PublishFlags.from_env({"MAX_POSTS": raw})
    assert flags.max_posts == expected


@pytest.mark.parametrize("raw", ["-1", "-3", "-100"])
def test_max_posts_negative_falls_to_default(raw, caplog):
    with caplog.at_level(logging.WARNING):
        flags = PublishFlags.from_env({"MAX_POSTS": raw})
    assert flags.max_posts == DEFAULT_MAX_POSTS


@pytest.mark.parametrize("raw", ["abc", "1.5", "one", "  ", "true"])
def test_max_posts_non_numeric_falls_to_default(raw, caplog):
    with caplog.at_level(logging.WARNING):
        flags = PublishFlags.from_env({"MAX_POSTS": raw})
    assert flags.max_posts == DEFAULT_MAX_POSTS


def test_max_posts_empty_falls_to_default():
    flags = PublishFlags.from_env({"MAX_POSTS": ""})
    assert flags.max_posts == DEFAULT_MAX_POSTS


def test_max_posts_per_day_valid_zero():
    flags = PublishFlags.from_env({"MAX_POSTS_PER_DAY": "0"})
    assert flags.max_posts_per_day == 0


def test_max_posts_per_day_negative_falls_to_default(caplog):
    with caplog.at_level(logging.WARNING):
        flags = PublishFlags.from_env({"MAX_POSTS_PER_DAY": "-7"})
    assert flags.max_posts_per_day == DEFAULT_MAX_POSTS_PER_DAY


def test_max_posts_per_day_garbage_falls_to_default(caplog):
    with caplog.at_level(logging.WARNING):
        flags = PublishFlags.from_env({"MAX_POSTS_PER_DAY": "soon"})
    assert flags.max_posts_per_day == DEFAULT_MAX_POSTS_PER_DAY


# --------------------------------------------------------------------------- #
# allows_real_publish matrix
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "publish_enabled,dry_run,max_posts,expected",
    [
        # The single combination that allows real publish.
        (True, False, 1, True),
        (True, False, 5, True),
        # Kill switch off.
        (False, False, 1, False),
        # DRY_RUN on (defensive).
        (True, True, 1, False),
        # Cap = 0.
        (True, False, 0, False),
        # Both defenses off but cap = 0.
        (True, False, 0, False),
        # Defaults.
        (False, True, 1, False),
    ],
)
def test_allows_real_publish_matrix(publish_enabled, dry_run, max_posts, expected):
    flags = PublishFlags(
        publish_enabled=publish_enabled,
        dry_run=dry_run,
        max_posts=max_posts,
        max_posts_per_day=1,
    )
    assert flags.allows_real_publish() is expected


def test_allows_real_publish_ignores_max_posts_per_day():
    """Per contract, daily-cap enforcement lands with #404-lite."""
    flags = PublishFlags(
        publish_enabled=True,
        dry_run=False,
        max_posts=1,
        max_posts_per_day=0,
    )
    assert flags.allows_real_publish() is True


# --------------------------------------------------------------------------- #
# Smoke: real env-shaped scenarios
# --------------------------------------------------------------------------- #

def test_all_on_env_allows_publish():
    flags = PublishFlags.from_env(
        {
            "PUBLISH_ENABLED": "true",
            "DRY_RUN": "false",
            "MAX_POSTS": "1",
            "MAX_POSTS_PER_DAY": "1",
        }
    )
    assert flags.allows_real_publish() is True


def test_garbage_env_never_raises_and_falls_to_defaults(caplog):
    with caplog.at_level(logging.WARNING):
        flags = PublishFlags.from_env(
            {
                "PUBLISH_ENABLED": "maybe",
                "DRY_RUN": "sometimes",
                "MAX_POSTS": "-3",
                "MAX_POSTS_PER_DAY": "abc",
            }
        )
    assert flags.publish_enabled is DEFAULT_PUBLISH_ENABLED
    assert flags.dry_run is DEFAULT_DRY_RUN
    assert flags.max_posts == DEFAULT_MAX_POSTS
    assert flags.max_posts_per_day == DEFAULT_MAX_POSTS_PER_DAY
    assert flags.allows_real_publish() is False


def test_from_env_uses_os_environ_when_no_arg(monkeypatch):
    monkeypatch.delenv("PUBLISH_ENABLED", raising=False)
    monkeypatch.delenv("DRY_RUN", raising=False)
    monkeypatch.delenv("MAX_POSTS", raising=False)
    monkeypatch.delenv("MAX_POSTS_PER_DAY", raising=False)
    flags = PublishFlags.from_env()
    assert flags.allows_real_publish() is False
