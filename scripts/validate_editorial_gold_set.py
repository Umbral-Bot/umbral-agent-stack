#!/usr/bin/env python3
"""
validate_editorial_gold_set.py — Validate editorial gold set and dimensions.

Loads the gold-set cases and dimensions, runs structural validation,
and prints a summary.  Exit code 0 if valid, 1 if errors found.

Usage:
  python scripts/validate_editorial_gold_set.py
  python scripts/validate_editorial_gold_set.py --gold-set evals/editorial/gold-set-minimum.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from infra.editorial_gold_set import (
    load_dimensions,
    load_gold_set,
    summarize_gold_set,
    validate_dimension_weights,
    validate_gold_set_cases,
)

_DEFAULT_GOLD_SET = Path("evals/editorial/gold-set-minimum.yaml")
_DEFAULT_DIMENSIONS = Path("evals/editorial/dimensions.yaml")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate editorial gold set and dimensions.",
    )
    parser.add_argument(
        "--gold-set",
        type=Path,
        default=_DEFAULT_GOLD_SET,
        help=f"Path to gold-set YAML (default: {_DEFAULT_GOLD_SET})",
    )
    parser.add_argument(
        "--dimensions",
        type=Path,
        default=_DEFAULT_DIMENSIONS,
        help=f"Path to dimensions YAML (default: {_DEFAULT_DIMENSIONS})",
    )
    args = parser.parse_args(argv)

    # Load
    try:
        dimensions = load_dimensions(args.dimensions)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR loading dimensions: {e}", file=sys.stderr)
        return 1

    try:
        cases = load_gold_set(args.gold_set)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR loading gold set: {e}", file=sys.stderr)
        return 1

    # Validate
    errors: list[str] = []
    errors.extend(validate_dimension_weights(dimensions))
    errors.extend(validate_gold_set_cases(cases, dimensions))

    # Summary
    summary = summarize_gold_set(cases)
    print(f"Gold set: {args.gold_set}")
    print(f"Dimensions: {args.dimensions}")
    print(f"  Cases: {summary['total_cases']}")
    print(f"  Channels: {', '.join(summary['channels_covered'])}")
    print(f"  Input types: {', '.join(summary['input_types_covered'])}")
    print(f"  Audience stages: {', '.join(summary['audience_stages_covered'])}")
    print(f"  Dimensions used: {len(summary['dimensions_used'])}")
    print(f"  All have human gate: {summary['all_have_human_gate']}")

    if errors:
        print(f"\n{len(errors)} validation error(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("\nValidation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
