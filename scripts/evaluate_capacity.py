"""Offline CLI: python -m scripts.evaluate_capacity snapshot.json > receipt.json."""
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from dispatcher.capacity_evaluator import Evaluation, evaluate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()
    try:
        snapshot = Evaluation.model_validate_json(args.snapshot.read_text(encoding="utf-8-sig"))
    except (OSError, ValidationError) as error:
        # Never echo raw payloads or credentials from a malformed input file.
        print(json.dumps({"status": "INVALID_SNAPSHOT", "dispatch_allowed": False,
                          "error_type": type(error).__name__}))
        return 2
    print(json.dumps(evaluate(snapshot), ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
