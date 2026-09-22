"""T3-C1: deterministic planning only. No I/O, reservations or dispatch effects."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

Number = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Identifier = Annotated[str, Field(min_length=1, max_length=240)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Evidence(Contract):
    observed_at: AwareDatetime
    received_at: AwareDatetime
    expires_at: AwareDatetime
    evidence_ref: Identifier

    @model_validator(mode="after")
    def chronology(self):
        if not self.observed_at <= self.received_at < self.expires_at:
            raise ValueError("evidence chronology must be observed <= received < expires")
        return self

    def fresh(self, now: datetime) -> bool:
        return self.received_at <= now < self.expires_at


class Observation(Evidence):
    product: Identifier
    account_ref: Identifier  # opaque non-secret reference, not a credential
    pool_id: Identifier
    window_id: Identifier
    source: Literal["tool", "ui", "fixture"]
    confidence: Literal["verified", "reported", "simulated"] = "reported"
    availability: Literal["pass", "blocked", "unknown"] = "unknown"
    total: Number = 100
    remaining: Number | None = None
    unit: Literal["percent", "requests", "tokens"] = "percent"
    resets_at: AwareDatetime | None = None
    unknown_reason: str | None = None

    @model_validator(mode="after")
    def amounts(self):
        if self.total <= 0 or (self.unit == "percent" and self.total != 100):
            raise ValueError("invalid quota total")
        if self.remaining is not None and self.remaining > self.total:
            raise ValueError("remaining exceeds total")
        if self.remaining is None and not self.unknown_reason:
            raise ValueError("unknown quota needs a reason")
        return self

    def valid_until(self) -> datetime:
        ttl = timedelta(minutes=15 if self.source == "ui" else 5)
        return min(self.expires_at, self.observed_at + ttl,
                   self.resets_at or self.expires_at)


class Signal(Evidence):
    value: Literal["pass", "fail", "unknown"] = "unknown"


class Route(Contract):
    route_id: Identifier
    product: Identifier
    account_ref: Identifier
    pool_id: Identifier | None = None
    pool_relationships_verified: bool = False
    windows_complete: bool = False
    window_ids: list[Identifier] = Field(default_factory=list)
    included_usage_verified: bool = False
    checks: dict[str, Signal] = Field(default_factory=dict)
    # Failure/refusal/429 wins over historical success, including a fallback route.
    stop_reason: str | None = None


class Commitments(Evidence):
    pool_id: Identifier
    amounts: dict[str, Number]  # every limiting window, same units as observation


class Candidate(Contract):
    task_id: Identifier
    revision: Identifier
    owner: Identifier
    source_ref: Identifier
    status: Literal["pending", "blocked", "done"]
    kind: Literal["deliverable", "incident", "backlog", "learning"]
    authorized: bool = False
    useful: bool = False
    ready: bool = False
    needs_gui: bool = False
    route_id: Identifier
    max_cost: dict[str, Number] | None = None
    cost_evidence_ref: str | None = None
    deadline: AwareDatetime | None = None
    next_step: str


class Evaluation(Contract):
    schema_version: Literal["t3c1.v1"] = "t3c1.v1"
    now: AwareDatetime
    mode: Literal["observed", "simulation"] = "observed"
    stop: bool = False
    reserve_fraction: Annotated[float, Field(ge=.20, le=1, allow_inf_nan=False)] = .20
    margin_fraction: Annotated[float, Field(ge=.05, le=1, allow_inf_nan=False)] = .05
    max_candidates: Annotated[int, Field(ge=1, le=3)] = 3
    routes: list[Route]
    observations: list[Observation]
    commitments: list[Commitments]
    candidates: list[Candidate]

    @model_validator(mode="after")
    def unique_keys(self):
        for keys in ([r.route_id for r in self.routes],
                     [(o.pool_id, o.window_id) for o in self.observations],
                     [c.pool_id for c in self.commitments],
                     [c.task_id for c in self.candidates]):
            if len(keys) != len(set(keys)):
                raise ValueError("duplicate identity in evaluation snapshot")
        if self.reserve_fraction + self.margin_fraction > 1:
            raise ValueError("reserve and margin exceed capacity")
        return self


def evaluate(snapshot: Evaluation) -> dict:
    """Plan up to three useful tasks against one snapshot, never admit them.

    Shared pools are debited in this calculation only. The receipt is reproducible
    for the same input, not a durable claim, lock or authority to run a task.
    """
    canonical = json.dumps(snapshot.model_dump(mode="json"), sort_keys=True,
                           separators=(",", ":"), allow_nan=False)
    decision_id = hashlib.sha256(canonical.encode()).hexdigest()
    routes = {r.route_id: r for r in snapshot.routes}
    observations = {(o.pool_id, o.window_id): o for o in snapshot.observations}
    commitments = {c.pool_id: c for c in snapshot.commitments}
    allocated: dict[tuple[str, str], float] = {}
    results = []
    selected = 0
    priority = {k: i for i, k in enumerate(("deliverable", "incident", "backlog", "learning"))}
    order = sorted(snapshot.candidates, key=lambda c: (
        priority[c.kind], c.deadline.timestamp() if c.deadline else float("inf"), c.task_id))
    for task in order:
        reasons: list[str] = []
        available: dict[str, float] = {}
        expiries: list[datetime] = []
        references = [task.source_ref]
        route = routes.get(task.route_id)
        if snapshot.stop:
            reasons.append("GLOBAL_STOP")
        if task.status == "done":
            reasons.append("ALREADY_COMPLETED")
        elif task.status != "pending" or not task.ready:
            reasons.append("TASK_NOT_READY")
        if not task.authorized:
            reasons.append("NOT_AUTHORIZED")
        if not task.useful:
            reasons.append("NO_USEFUL_OUTCOME")
        if not reasons:
            if route is None:
                reasons.append("ROUTE_UNKNOWN")
            else:
                if route.stop_reason:
                    reasons.append("ROUTE_STOP")
                if not route.included_usage_verified:
                    reasons.append("INCLUDED_USAGE_UNKNOWN")
                if not route.pool_id or not route.pool_relationships_verified:
                    reasons.append("POOL_RELATIONSHIP_UNKNOWN")
                if not route.windows_complete or not route.window_ids:
                    reasons.append("LIMITING_WINDOWS_UNKNOWN")
                known_windows = {o.window_id for o in snapshot.observations if o.pool_id == route.pool_id}
                if known_windows != set(route.window_ids):
                    reasons.append("WINDOW_SET_MISMATCH")
                checks = ["credential", "permission", "health", "capability", "host", "lease"]
                if task.needs_gui:
                    checks.append("gui")
                for name in checks:
                    signal = route.checks.get(name)
                    if signal is None or signal.value != "pass" or not signal.fresh(snapshot.now):
                        reasons.append("READINESS_" + name.upper())
                    else:
                        expiries.append(signal.expires_at)
                        references.append(signal.evidence_ref)
                commitment = commitments.get(route.pool_id)
                if commitment is None or not commitment.fresh(snapshot.now):
                    reasons.append("COMMITMENTS_UNKNOWN_OR_STALE")
                else:
                    expiries.append(commitment.expires_at)
                    references.append(commitment.evidence_ref)
                    if set(commitment.amounts) != set(route.window_ids):
                        reasons.append("COMMITMENT_WINDOW_SET_MISMATCH")
                if task.max_cost is None or not task.cost_evidence_ref:
                    reasons.append("COST_NOT_BOUNDED")
                else:
                    references.append(task.cost_evidence_ref)
                    if set(task.max_cost) != set(route.window_ids):
                        reasons.append("COST_WINDOW_SET_MISMATCH")
                for window in sorted(set(route.window_ids)):
                    key = (route.pool_id, window)
                    obs = observations.get(key)
                    if obs is None or obs.remaining is None:
                        reasons.append("QUOTA_UNKNOWN:" + window)
                        continue
                    references.append(obs.evidence_ref)
                    if obs.product != route.product or obs.account_ref != route.account_ref:
                        reasons.append("QUOTA_IDENTITY_MISMATCH:" + window)
                    if obs.availability != "pass":
                        reasons.append("PROVIDER_AVAILABILITY:" + window)
                    if snapshot.mode != "simulation" and (
                            obs.source == "fixture" or obs.confidence == "simulated"):
                        reasons.append("SIMULATED_QUOTA:" + window)
                    if not obs.fresh(snapshot.now) or snapshot.now >= obs.valid_until():
                        reasons.append("QUOTA_STALE_OR_RESET:" + window)
                    expiries.append(obs.valid_until())
                    if (commitment is None or window not in commitment.amounts
                            or task.max_cost is None or window not in task.max_cost):
                        reasons.append("WINDOW_BUDGET_UNKNOWN:" + window)
                        continue
                    free = max(0.0, obs.remaining - obs.total * (
                        snapshot.reserve_fraction + snapshot.margin_fraction)
                        - commitment.amounts[window] - allocated.get(key, 0))
                    available[window] = round(free, 8)
                    if task.max_cost[window] > free:
                        reasons.append("RESERVE_PROTECTED:" + window)
        if not reasons and selected >= snapshot.max_candidates:
            reasons.append("CANDIDATE_LIMIT")
        if not reasons:
            selected += 1
            for window in set(route.window_ids):
                key = (route.pool_id, window)
                allocated[key] = allocated.get(key, 0) + task.max_cost[window]
        results.append({"task_id": task.task_id, "revision": task.revision,
                        "owner": task.owner, "route_id": task.route_id,
                        "status": "HOLD" if reasons else "PROPOSED_ONLY",
                        "reasons": reasons or ["WITHIN_OBSERVED_BUDGET"],
                        "available_before": available,
                        "valid_until": min(expiries).isoformat() if expiries else None,
                        "evidence_refs": sorted(set(references)), "next_step": task.next_step})
    return {"schema_version": "t3c1.v1", "decision_id": decision_id,
            "evaluated_at": snapshot.now.isoformat(), "mode": snapshot.mode,
            "dispatch_allowed": False, "incremental_spend_authorized_usd": 0,
            "status": "PROPOSALS_ONLY" if selected else "IDLE",
            "capacity_observations": [
                {"product": o.product, "account_ref": o.account_ref, "pool_id": o.pool_id,
                 "window_id": o.window_id, "unit": o.unit, "observed_remaining": o.remaining,
                 "availability": o.availability, "confidence": o.confidence, "source": o.source,
                 "observed_at": o.observed_at.isoformat(), "valid_until": o.valid_until().isoformat(),
                 "fresh": o.fresh(snapshot.now) and snapshot.now < o.valid_until(),
                 "evidence_ref": o.evidence_ref} for o in snapshot.observations],
            "decisions": results}


def codex_observations(payload: dict, *, account_ref: str, observed_at: datetime,
                       received_at: datetime, evidence_ref: str) -> list[Observation]:
    """Normalize only the codex bucket from a captured get_usage_limits response.

    Missing windows stay unknown to the caller. No assertion of windows_complete,
    shared identity with PCRick, extra credits or compatibility with other pools.
    """
    buckets = payload.get("rateLimitsByLimitId")
    bucket = buckets.get("codex", {}) if buckets is not None else payload.get("rateLimits", {})
    if bucket is None or bucket.get("limitId") != "codex":
        return []
    rows = []
    for window_id in ("primary", "secondary"):
        window = bucket.get(window_id)
        if not isinstance(window, dict):
            continue
        used = window.get("usedPercent")
        # No clamping corrupt telemetry into usable budget.
        if isinstance(used, bool) or not isinstance(used, (int, float)) or not 0 <= used <= 100:
            remaining = None
        else:
            remaining = 100 - used
        reset = window.get("resetsAt")
        from datetime import timezone
        resets_at = datetime.fromtimestamp(reset, timezone.utc) if reset is not None else None
        rows.append(Observation(product="codex", account_ref=account_ref,
                                pool_id="codex:" + account_ref, window_id=window_id,
                                source="tool", observed_at=observed_at, received_at=received_at,
                                confidence="verified",
                                availability=("blocked" if payload.get("ordinaryUsageAllowed") is False
                                              or bucket.get("spendControlReached") is True
                                              or bucket.get("rateLimitReachedType") is not None
                                              else "pass" if payload.get("ordinaryUsageAllowed") is True
                                              else "unknown"),
                                expires_at=observed_at + timedelta(minutes=5),
                                evidence_ref=evidence_ref, remaining=remaining,
                                resets_at=resets_at,
                                unknown_reason="usedPercent unavailable/invalid" if remaining is None else None))
    return rows
