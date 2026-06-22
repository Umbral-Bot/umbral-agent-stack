#!/usr/bin/env python3
"""Read-only token-ledger collector for a PIT tournament (PIT-P6).

Aggregates, per lane, the token usage that two independent subsystems already
record on disk and emits a single ``token_ledger.yaml``:

* **OpenClaw lane sessions** — ``<openclaw_root>/agents/<pit_id>-lane-*/``.
  The canonical store is ``sessions/sessions.json`` (a dict of sessions with
  camelCase ``inputTokens`` / ``outputTokens`` / ``totalTokens`` / ``cacheRead``,
  the same shape consumed by ``scripts/openclaw_runtime_snapshot.py``). Any
  ``sessions/*.jsonl`` transcripts are also scanned for usage as a fallback.

* **Copilot CLI broker audit** — ``<audit_root>/**/<mission_run_id>.jsonl``
  (P4 contract). Events are filtered by ``metadata.pit_id`` and bucketed by
  ``lane_id``; we count calls (dry-run vs real), an exit-code histogram and
  duration. GitHub Copilot CLI does not surface token counts, so the per-lane
  ``tokens`` block degrades to ``source: not_reported_by_github_copilot_cli``
  unless a future audit event carries a populated ``tokens`` object.

The collector is strictly read-only: it never mutates runtime state, never
prints secrets/PAT material (only numeric usage, model names and correlation
ids are read), and tolerates missing files by emitting warnings instead of
crashing.

Exit codes
----------
``0``  collector ran and wrote the YAML (warnings allowed).
``2``  ``pit_id`` is invalid, or the output could not be written.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:  # PyYAML is a project dependency; degrade with a clear message if absent.
    import yaml
except ImportError:  # pragma: no cover - exercised only without the dep
    yaml = None  # type: ignore[assignment]

PIT_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
NOT_REPORTED = "not_reported_by_github_copilot_cli"

# Audit decisions that mean the broker actually executed against Docker (a
# "real" call) rather than a gated / dry-run no-op.
REAL_DECISIONS = frozenset({"execute_started", "completed", "secret_pattern_redacted"})

DEFAULT_OPENCLAW_ROOT = "~/.openclaw"
DEFAULT_VAULT_ROOT = "~/umbral-pit-vault"
DEFAULT_AUDIT_ROOT = "reports/copilot-cli"


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_int(value: Any) -> int:
    try:
        if isinstance(value, bool):
            return 0
        return int(value)
    except (TypeError, ValueError):
        return 0


def validate_pit_id(pit_id: str) -> bool:
    return bool(pit_id) and bool(PIT_ID_RE.match(pit_id))


def lane_from_agent_dir(name: str, pit_id: str) -> Optional[str]:
    """Map an OpenClaw agent directory name to a lane id.

    The canonical on-disk convention is ``<pit_id>-lane-<slug>`` where the
    ``pit_id`` already carries its ``pit-`` prefix, e.g.
    ``pit-umbral-bim2-sharepoint-acc-lane-foundry-tools`` -> ``lane-foundry-tools``.
    A directory named exactly ``<pit_id>`` maps to the synthetic ``_pit_root``
    lane. When the ``pit_id`` does not already start with ``pit-`` we also
    tolerate the documented ``pit-<pit_id>`` form. Returns ``None`` when the
    directory does not belong to this tournament.
    """

    bases = [pit_id]
    if not pit_id.startswith("pit-"):
        bases.append(f"pit-{pit_id}")
    for base in bases:
        if name == base:
            return "_pit_root"
        prefix = f"{base}-"
        if name.startswith(prefix):
            return name[len(prefix):] or "_pit_root"
    return None


def _empty_openclaw() -> Dict[str, Any]:
    return {
        "input": 0,
        "output": 0,
        "cache_read": 0,
        "total": 0,
        "model": None,
        "sessions": 0,
        "events": 0,
    }


def _empty_copilot() -> Dict[str, Any]:
    return {
        "calls": 0,
        "dry_run": 0,
        "real": 0,
        "exit_codes": {},
        "duration_sec": {"sum": 0.0, "avg": None},
        "tokens": {"source": NOT_REPORTED},
    }


# ---------------------------------------------------------------------------
# Usage extraction (tolerant to several provider shapes)
# ---------------------------------------------------------------------------
def extract_session_usage(item: Dict[str, Any]) -> Dict[str, Any]:
    """Pull token usage from one ``sessions.json`` entry (camelCase + fallbacks)."""

    usage = item.get("usage") if isinstance(item.get("usage"), dict) else {}

    def pick(*keys: str) -> int:
        for source in (item, usage):
            for key in keys:
                if key in source and source[key] is not None:
                    return _safe_int(source[key])
        return 0

    input_tokens = pick("inputTokens", "input_tokens", "prompt_tokens", "input")
    output_tokens = pick("outputTokens", "output_tokens", "completion_tokens", "output")
    total_tokens = pick("totalTokens", "total_tokens", "total")
    cache_read = pick(
        "cacheRead", "cache_read", "cache_read_input_tokens", "cacheReadInputTokens"
    )
    if total_tokens == 0:
        total_tokens = input_tokens + output_tokens
    model = item.get("model") or usage.get("model")
    return {
        "input": input_tokens,
        "output": output_tokens,
        "total": total_tokens,
        "cache_read": cache_read,
        "model": str(model) if model else None,
    }


def extract_jsonl_usage(event: Dict[str, Any]) -> Dict[str, Any]:
    """Pull token usage from a single JSONL session event, if any."""

    usage = event.get("usage")
    if not isinstance(usage, dict):
        message = event.get("message")
        if isinstance(message, dict) and isinstance(message.get("usage"), dict):
            usage = message["usage"]
        else:
            usage = {}
    merged = {**event, **usage}

    def pick(*keys: str) -> int:
        for key in keys:
            if key in merged and merged[key] is not None:
                return _safe_int(merged[key])
        return 0

    input_tokens = pick("inputTokens", "input_tokens", "prompt_tokens")
    output_tokens = pick("outputTokens", "output_tokens", "completion_tokens")
    total_tokens = pick("totalTokens", "total_tokens")
    cache_read = pick(
        "cacheRead", "cache_read", "cache_read_input_tokens", "cacheReadInputTokens"
    )
    if total_tokens == 0:
        total_tokens = input_tokens + output_tokens
    model = merged.get("model") or (
        event.get("message", {}).get("model") if isinstance(event.get("message"), dict) else None
    )
    return {
        "input": input_tokens,
        "output": output_tokens,
        "total": total_tokens,
        "cache_read": cache_read,
        "model": str(model) if model else None,
    }


# ---------------------------------------------------------------------------
# OpenClaw collection
# ---------------------------------------------------------------------------
def collect_openclaw(
    openclaw_root: Path, pit_id: str
) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    warnings: List[str] = []
    lanes: Dict[str, Dict[str, Any]] = defaultdict(_empty_openclaw)
    model_weight: Dict[str, Counter] = defaultdict(Counter)

    agents_dir = openclaw_root / "agents"
    if not agents_dir.exists():
        # Tolerate ``--openclaw-root`` pointed straight at the agents directory.
        agents_dir = openclaw_root
    if not agents_dir.exists():
        warnings.append(f"openclaw agents dir missing: {agents_dir}")
        return {}, warnings

    matched_any = False
    for agent_dir in sorted(p for p in agents_dir.iterdir() if p.is_dir()):
        lane = lane_from_agent_dir(agent_dir.name, pit_id)
        if lane is None:
            continue
        matched_any = True
        bucket = lanes[lane]
        sessions_dir = agent_dir / "sessions"

        sessions_json = sessions_dir / "sessions.json"
        if sessions_json.exists():
            try:
                payload = json.loads(sessions_json.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                warnings.append(f"unreadable {sessions_json.name} in {agent_dir.name}: {exc.__class__.__name__}")
                payload = None
            if isinstance(payload, dict):
                for item in payload.values():
                    if not isinstance(item, dict):
                        continue
                    usage = extract_session_usage(item)
                    bucket["input"] += usage["input"]
                    bucket["output"] += usage["output"]
                    bucket["total"] += usage["total"]
                    bucket["cache_read"] += usage["cache_read"]
                    bucket["sessions"] += 1
                    if usage["model"]:
                        model_weight[lane][usage["model"]] += usage["total"] or 1

        if sessions_dir.exists():
            for jsonl_path in sorted(sessions_dir.glob("*.jsonl")):
                file_had_event = False
                try:
                    with jsonl_path.open("r", encoding="utf-8") as handle:
                        for line in handle:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                event = json.loads(line)
                            except json.JSONDecodeError:
                                continue
                            if not isinstance(event, dict):
                                continue
                            file_had_event = True
                            bucket["events"] += 1
                            usage = extract_jsonl_usage(event)
                            bucket["input"] += usage["input"]
                            bucket["output"] += usage["output"]
                            bucket["total"] += usage["total"]
                            bucket["cache_read"] += usage["cache_read"]
                            if usage["model"]:
                                model_weight[lane][usage["model"]] += usage["total"] or 1
                except OSError as exc:
                    warnings.append(f"unreadable session jsonl {jsonl_path.name}: {exc.__class__.__name__}")
                    continue
                if file_had_event:
                    bucket["sessions"] += 1

    if not matched_any:
        warnings.append(f"no openclaw lane agents matched {pit_id}-* under {agents_dir}")

    for lane, counter in model_weight.items():
        if counter:
            lanes[lane]["model"] = counter.most_common(1)[0][0]

    return dict(lanes), warnings


# ---------------------------------------------------------------------------
# Copilot CLI audit collection
# ---------------------------------------------------------------------------
def collect_copilot_cli(
    audit_root: Path, pit_id: str
) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    warnings: List[str] = []
    if not audit_root.exists():
        warnings.append(f"copilot-cli audit root missing: {audit_root}")
        return {}, warnings

    # Per-lane, per-run accumulation so a call is counted once even though its
    # JSONL file holds several phase events.
    lane_runs: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(
        lambda: defaultdict(lambda: {"executed": False, "exit_codes": [], "durations": [], "tokens": []})
    )

    matched_files = 0
    for jsonl_path in sorted(audit_root.rglob("*.jsonl")):
        try:
            with jsonl_path.open("r", encoding="utf-8") as handle:
                lines = handle.readlines()
        except OSError as exc:
            warnings.append(f"unreadable audit {jsonl_path.name}: {exc.__class__.__name__}")
            continue
        file_matched = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict) or event.get("pit_id") != pit_id:
                continue
            file_matched = True
            lane = event.get("lane_id") or "_no_lane"
            run_id = event.get("mission_run_id") or jsonl_path.stem
            run = lane_runs[lane][run_id]
            if "exit_code" in event and event["exit_code"] is not None:
                run["exit_codes"].append(_safe_int(event["exit_code"]))
            if event.get("decision") in REAL_DECISIONS or ("exit_code" in event):
                run["executed"] = True
            duration = event.get("duration_sec")
            if isinstance(duration, (int, float)) and not isinstance(duration, bool):
                run["durations"].append(float(duration))
            tokens = event.get("tokens")
            if isinstance(tokens, dict):
                run["tokens"].append(tokens)
        if file_matched:
            matched_files += 1

    if matched_files == 0:
        warnings.append(f"no copilot-cli audit events matched pit_id={pit_id} under {audit_root}")

    lanes: Dict[str, Dict[str, Any]] = {}
    for lane, runs in lane_runs.items():
        bucket = _empty_copilot()
        exit_hist: Counter = Counter()
        durations: List[float] = []
        token_input = token_output = token_total = 0
        token_seen = False
        for run in runs.values():
            bucket["calls"] += 1
            if run["executed"]:
                bucket["real"] += 1
            else:
                bucket["dry_run"] += 1
            for code in run["exit_codes"]:
                exit_hist[str(code)] += 1
            durations.extend(run["durations"])
            for tok in run["tokens"]:
                ti, to, tt = tok.get("input"), tok.get("output"), tok.get("total")
                if any(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (ti, to, tt)):
                    token_seen = True
                    token_input += _safe_int(ti)
                    token_output += _safe_int(to)
                    token_total += _safe_int(tt)
        bucket["exit_codes"] = dict(sorted(exit_hist.items()))
        if durations:
            total = round(sum(durations), 3)
            bucket["duration_sec"] = {"sum": total, "avg": round(total / len(durations), 3)}
        if token_seen:
            if token_total == 0:
                token_total = token_input + token_output
            bucket["tokens"] = {
                "input": token_input,
                "output": token_output,
                "total": token_total,
                "source": "copilot_cli_audit",
            }
        lanes[lane] = bucket

    return lanes, warnings


# ---------------------------------------------------------------------------
# Budget (best-effort, optional)
# ---------------------------------------------------------------------------
def load_lane_budgets(vault_root: Path, pit_id: str) -> Dict[str, Optional[float]]:
    """Best-effort per-lane allocated budget from the vault pit_spec.

    Returns an empty dict on any problem (missing spec, unparseable, no budget).
    Never raises.
    """

    if yaml is None:
        return {}
    spec_path = vault_root / "pit" / pit_id / "spec" / "pit_spec.yaml"
    if not spec_path.exists():
        return {}
    try:
        raw = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    if not isinstance(raw, dict):
        return {}
    lanes = raw.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        return {}

    total_budget = raw.get("budget_usd_total")
    even_share: Optional[float] = None
    if isinstance(total_budget, (int, float)) and not isinstance(total_budget, bool):
        even_share = round(float(total_budget) / len(lanes), 4)

    out: Dict[str, Optional[float]] = {}
    for lane in lanes:
        if not isinstance(lane, dict):
            continue
        lane_id = lane.get("lane_id") or lane.get("id") or lane.get("name")
        if not lane_id:
            continue
        own = lane.get("budget_usd")
        if isinstance(own, (int, float)) and not isinstance(own, bool):
            out[str(lane_id)] = round(float(own), 4)
        elif even_share is not None:
            out[str(lane_id)] = even_share
    return out


# ---------------------------------------------------------------------------
# Ledger assembly
# ---------------------------------------------------------------------------
def build_ledger(
    pit_id: str,
    openclaw_lanes: Dict[str, Dict[str, Any]],
    copilot_lanes: Dict[str, Dict[str, Any]],
    budgets: Optional[Dict[str, Optional[float]]] = None,
    warnings: Optional[List[str]] = None,
    sources: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    budgets = budgets or {}
    warnings = warnings or []
    lane_ids = sorted(set(openclaw_lanes) | set(copilot_lanes) | set(budgets))

    lanes_out: Dict[str, Any] = {}
    openclaw_total = 0
    copilot_calls_total = 0
    for lane_id in lane_ids:
        oc = {**_empty_openclaw(), **openclaw_lanes.get(lane_id, {})}
        cc = {**_empty_copilot(), **copilot_lanes.get(lane_id, {})}
        openclaw_total += _safe_int(oc.get("total"))
        copilot_calls_total += _safe_int(cc.get("calls"))
        lanes_out[lane_id] = {
            "openclaw": oc,
            "copilot_cli": cc,
            "budget_usd_allocated": budgets.get(lane_id),
            "budget_usd_estimated": None,
        }

    ledger: Dict[str, Any] = {
        "pit_id": pit_id,
        "generated_at_utc": _now_iso(),
        "schema_version": 1,
        "lanes": lanes_out,
        "tournament_total": {
            "openclaw_total": openclaw_total,
            "copilot_cli_calls": copilot_calls_total,
            "lanes": len(lanes_out),
            "notes": list(dict.fromkeys(warnings)),
        },
    }
    if sources is not None:
        ledger["sources"] = sources
    return ledger


def default_output_path(vault_root: Path, pit_id: str) -> Path:
    return vault_root / "pit" / pit_id / "metrics" / "token_ledger.yaml"


def dump_yaml(data: Dict[str, Any]) -> str:
    if yaml is None:  # pragma: no cover - dependency guaranteed in project
        return json.dumps(data, indent=2, ensure_ascii=False)
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pit_collect_tokens",
        description="Read-only token ledger collector for a PIT tournament (P6).",
    )
    parser.add_argument("--pit-id", required=True, help="Tournament id (^[A-Za-z0-9._-]{1,64}$).")
    parser.add_argument("--vault-root", default=DEFAULT_VAULT_ROOT, help="PIT vault root.")
    parser.add_argument("--openclaw-root", default=DEFAULT_OPENCLAW_ROOT, help="OpenClaw root (expects an agents/ subdir).")
    parser.add_argument("--audit-root", default=DEFAULT_AUDIT_ROOT, help="Copilot CLI audit root.")
    parser.add_argument("--output", default=None, help="Output YAML path (default: <vault>/pit/<pit_id>/metrics/token_ledger.yaml).")
    parser.add_argument("--stdout", action="store_true", help="Also print the ledger YAML to stdout.")
    return parser


def run(args: argparse.Namespace) -> int:
    pit_id = str(args.pit_id)
    if not validate_pit_id(pit_id):
        print(f"error: invalid_pit_id:{pit_id!r} must match ^[A-Za-z0-9._-]{{1,64}}$", file=sys.stderr)
        return 2

    vault_root = Path(args.vault_root).expanduser()
    openclaw_root = Path(args.openclaw_root).expanduser()
    audit_root = Path(args.audit_root).expanduser()

    warnings: List[str] = []
    openclaw_lanes, oc_warn = collect_openclaw(openclaw_root, pit_id)
    warnings.extend(oc_warn)
    copilot_lanes, cc_warn = collect_copilot_cli(audit_root, pit_id)
    warnings.extend(cc_warn)
    budgets = load_lane_budgets(vault_root, pit_id)

    sources = {
        "openclaw_root": str(openclaw_root),
        "openclaw_found": (openclaw_root / "agents").exists() or openclaw_root.exists(),
        "audit_root": str(audit_root),
        "audit_found": audit_root.exists(),
        "vault_root": str(vault_root),
        "vault_found": vault_root.exists(),
    }

    ledger = build_ledger(
        pit_id, openclaw_lanes, copilot_lanes, budgets, warnings=warnings, sources=sources
    )

    output_path = Path(args.output).expanduser() if args.output else default_output_path(vault_root, pit_id)
    text = dump_yaml(ledger)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot write output {output_path}: {exc}", file=sys.stderr)
        return 2

    print(f"# pit token ledger -> {output_path}")
    print(f"# lanes={len(ledger['lanes'])} openclaw_total={ledger['tournament_total']['openclaw_total']} "
          f"copilot_cli_calls={ledger['tournament_total']['copilot_cli_calls']} warnings={len(warnings)}")
    for note in ledger["tournament_total"]["notes"]:
        print(f"# warning: {note}")
    if args.stdout:
        print(text)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
