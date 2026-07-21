#!/usr/bin/env python3
"""B2 guard-fix — redact secret fingerprints from captured CLI output.

Some diagnostic commands print partially-masked credential fingerprints to
stdout by default (see the ``secret-output-guard`` skill, "Tool-emitted partial
leaks"). ``openclaw models status`` is one of them: it re-emits a partial
Google Vertex credential fingerprint on every run, which then lands in agent
transcripts / logs / screenshots and can be correlated in audit logs. Even a
prefix is enough to leak.

This filter is the reproducible, testable ``CLI`` hardening called for by
``GO_B2_GUARD_FIX`` (``docs/plans/tanda-b-security-execution-plan-2026-07-19.md``
§2/§5, row B2). Pipe any command whose output an agent will capture through it:

    openclaw models status 2>&1 | python3 scripts/vps/secret_output_filter.py

It replaces credential-looking values with ``[REDACTED]`` while leaving normal
status text (profile names, model ids, timestamps) intact. It is **behavioral
defense in depth**, not a replacement for a real scanner (gitleaks/trufflehog)
and not the auth store — it only sanitises human-visible output. It never reads
the auth store, never rotates anything, and is idempotent (``[REDACTED]``
contains no secret pattern, so re-running is safe).
"""
from __future__ import annotations

import re
import sys
from typing import Pattern

REDACTED = "[REDACTED]"

# Ordered redaction passes. The masked-fingerprint pass runs first so a
# ``prefix***...`` token is swallowed whole before the prefix passes fire.
_PATTERNS: list[Pattern[str]] = [
    # Masked partial fingerprint: an alnum-ish run (>=8) followed by a run of
    # mask characters (``*`` / bullet / ellipsis), e.g. ``gho_abcd******`` or
    # ``github_pat_11BUEL...Sv_***...``. Mask indicators are deliberately
    # limited to ``*``, ``•`` and ``…`` so ordinary prose ellipses and
    # file paths are not touched.
    re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-]{7,}(?:\*{2,}|•{2,}|…)[.…•*]*"),
    # Google API key.
    re.compile(r"AIza[0-9A-Za-z_\-]{10,}"),
    # Google OAuth access token / refresh token.
    re.compile(r"ya29\.[0-9A-Za-z_\-]{10,}"),
    re.compile(r"1//[0-9A-Za-z_\-]{10,}"),
    # JWT-like (header.payload[.signature]).
    re.compile(r"eyJ[0-9A-Za-z_\-]{10,}\.[0-9A-Za-z_\-]{6,}(?:\.[0-9A-Za-z_\-]{6,})?"),
    # Common secret prefixes.
    re.compile(
        r"(?:ghp_|gho_|ghs_|ghu_|github_pat_|sk-|sk_live_|sk_test_|whsec_|ntn_|secret_)"
        r"[0-9A-Za-z_\-]{6,}"
    ),
    # Bearer / Basic auth material.
    re.compile(r"(?i)\b(?:bearer|basic)\s+[0-9A-Za-z._\-+/=]{8,}"),
]

# Redact the VALUE of any env-style ``NAME=VALUE`` where NAME looks sensitive.
# Fail-closed (default-deny): over-redacting a benign value is cheaper than a
# leak (secret-output-guard rule #1).
_ENV_ASSIGN = re.compile(
    r"(?i)\b(\w*(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)\w*)=(\S+)"
)


def redact_secret_fingerprints(text: str) -> str:
    """Return ``text`` with credential-looking substrings replaced by ``[REDACTED]``.

    Idempotent and line-structure preserving. Safe to run on output that has
    already been redacted.
    """
    if not text:
        return text
    out = _ENV_ASSIGN.sub(lambda m: f"{m.group(1)}={REDACTED}", text)
    for pat in _PATTERNS:
        out = pat.sub(REDACTED, out)
    return out


def main(argv: list[str] | None = None) -> int:
    """Stream stdin → stdout, redacting each line. Returns 0."""
    del argv
    for line in sys.stdin:
        sys.stdout.write(redact_secret_fingerprints(line))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
