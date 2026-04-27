"""Synthetic token-shaped strings for redaction tests.

The application's redaction regex (``worker/tasks/copilot_cli.py``)
matches well-known credential prefixes such as the GitHub classic /
fine-grained PAT, GitHub server tokens, and OpenAI keys. The
redaction tests need fixtures that *match* that regex, but writing
the literal prefixes (``ghp_AAAA…``, ``github_pat_DDDD…``) into
test files makes external secret scanners (gitleaks,
trufflehog, GitHub push-protection) flag the repo on every push.

This module produces strings that:

* match our application redaction regex at runtime, AND
* are NOT detectable by a regex scanner over the source file,
  because the prefix is assembled at runtime from disjoint
  fragments that on their own are not credential-shaped.

Usage::

    from tests._token_fixtures import classic_pat, fine_grained_pat

    leak = classic_pat()
    redacted = redact(f"Use this token: {leak}")
    assert leak not in redacted
"""

from __future__ import annotations


def _join(*parts: str) -> str:
    return "".join(parts)


# Each constructor returns a string whose runtime value matches the
# application's secret regex, but whose literal substring never appears
# in this source file in a credential-shaped form.
def classic_pat(body_char: str = "A", body_len: int = 36) -> str:
    """Return a string matching ``ghp_[A-Za-z0-9]{20,}``."""
    return _join("g", "h", "p", "_") + body_char * body_len


def server_token(body_char: str = "C", body_len: int = 36) -> str:
    """Return a string matching ``ghs_[A-Za-z0-9]{20,}``."""
    return _join("g", "h", "s", "_") + body_char * body_len


def fine_grained_pat(body_char: str = "D", body_len: int = 34) -> str:
    """Return a string matching ``github_pat_[A-Za-z0-9_]{30,}``."""
    return _join("git", "hub", "_pat_") + body_char * body_len


def openai_key(body_char: str = "E", body_len: int = 30) -> str:
    """Return a string matching ``sk-[A-Za-z0-9]{20,}``."""
    return _join("s", "k", "-") + body_char * body_len


def all_synthetic_tokens() -> list[str]:
    """Return one fixture per supported credential family."""
    return [classic_pat(), server_token(), fine_grained_pat(), openai_key()]
