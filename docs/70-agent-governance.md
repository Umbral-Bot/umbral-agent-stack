# Agent Governance — Function Definition

> Defines the agent-governance function as a systemic layer of the Umbral Agent Stack. This is NOT a new agent, team, or automated system. It is a defined function that Rick (or David) can invoke to analyze the health and structure of the agent ecosystem.

## What agent-governance is

A periodic, on-demand analysis function that observes the agent ecosystem and produces structured recommendations. It answers: "Is the current agent/skill/routing setup working well, and what should change?"

## What agent-governance is NOT

- **Not the `improvement` team.** The `improvement` team in `config/teams.yaml` is a routing concept that handles intents like "mejora", "ooda", "self-eval". It routes work to roles (`sota_research`, `self_evaluation`, `implementation`). Agent-governance is a different layer: it observes the agent ecosystem itself, not general improvement tasks.
- **Not a new agent.** There is no `rick-governance` agent. The governance function is invoked by `rick-orchestrator` or by David directly.
- **Not an automated enforcer.** It proposes changes; David decides. It does not reorganize agents, create new skills, or modify routing on its own.
- **Not a dashboard.** It produces a structured report when invoked, not a persistent monitoring surface.

## Relationship to existing infrastructure

| Component | Role in governance |
|-----------|-------------------|
| `improvement` team (teams.yaml) | Routes "mejora/ooda/self-eval" intents. Governance may *feed* improvement issues but is not the same thing. |
| `observability` skill | Data source: OODA reports and self-eval scores from Redis. Governance *consumes* this data. |
| `system.ooda_report` handler | Provides task completion/failure metrics. Raw input for the "usage" signal. |
| `system.self_eval` handler | Provides task quality scores. Raw input for the "friction" signal. |
| `agent-handoff-governance` skill | Governs individual handoff behavior. Agent-governance observes handoff *patterns* across the system. |
| Runtime agent ROLE.md files | Define per-agent scope and boundaries. Agent-governance checks if these are respected in practice. |
| `Mejora Continua Agent Stack` (Linear) | Where governance findings become actionable issues. |

## The 4 signals

### 1. Usage

What agents and skills are actually used, how often, and with what success rate.

**Available sources today:**
- Redis task history (`umbral:task:*`) via `system.ooda_report`
- `system.self_eval` quality scores
- Linear issue history for `Mejora Continua Agent Stack`

**Not yet available:**
- Per-agent session frequency (requires OpenClaw telemetry not yet instrumented)
- Per-skill invocation counts (requires skill-level logging not yet in place)

**Minimal viable check:** Run `system.ooda_report` and `system.self_eval`, summarize task type distribution and average scores. Flag task types with high failure rates or low quality scores.

### 2. Friction

Handoffs that fail, block, loop, or create ambiguity.

**Available sources today:**
- Linear issues with `blocked` or `escalated` status
- Notion comments with unresolved follow-ups
- Observable pattern: tasks that get re-dispatched to the same handler multiple times

**Not yet available:**
- Structured handoff telemetry (the `agent-handoff-governance` skill defines the format but there is no aggregation layer)
- Escalation frequency metrics

**Minimal viable check:** Query Linear for blocked/stale issues in `Mejora Continua Agent Stack`. Review recent Notion Control Room comments for unresolved escalations. Flag recurring patterns.

### 3. Saturation and redundancy

Skills that overlap, roles that compete, agents that always delegate instead of acting.

**Available sources today:**
- Skill coverage report (`reports/skills-coverage-r12.md`)
- ROLE.md boundary definitions (can detect overlap by reading)
- AGENTS.md skill assignment table (can detect duplication)

**Not yet available:**
- Runtime delegation chain analysis (which agent spawns which, and how often)

**Minimal viable check:** Compare skill assignments across agents for duplicates. Read ROLE.md boundaries and flag any overlaps. Check if any runtime agent has zero direct task completions (always delegates).

### 4. Unmet demand

Recurring tasks that lack good capability, structural gaps, reasons for future skills or agents.

**Available sources today:**
- David's Notion comments and Telegram messages (patterns of requests that require manual intervention)
- Linear issues tagged as `enhancement` or `feature` in `Mejora Continua Agent Stack`
- Task types that consistently fail or return low-quality results

**Not yet available:**
- Intent classifier miss/fallback rate
- Explicit "capability gap" tracking

**Minimal viable check:** Review recent Linear issues for recurring themes. Check `system.self_eval` for consistently low-scoring task types. Ask: what does David repeatedly ask for that Rick handles poorly?

## Output format

When invoked, agent-governance produces a structured report:

```markdown
## Agent Governance Report — [date]

### Usage summary
- Task volume: [N] tasks in period
- Top task types: [list]
- Average quality score: [N]
- Failure rate: [N%]
- Agents active: [list]

### Friction signals
- Blocked issues: [N] ([list])
- Unresolved escalations: [N]
- Repeated dispatches: [list if any]

### Saturation / redundancy
- Duplicate skill assignments: [list if any]
- Boundary overlaps detected: [list if any]
- Agents with zero direct completions: [list if any]

### Unmet demand
- Recurring manual interventions: [list]
- Low-scoring task types: [list]
- Enhancement requests pending: [N]

### Recommendations
- [Actionable recommendation 1]
- [Actionable recommendation 2]
- ...

### Decisions for David
- [Decision requiring human judgment]
- ...
```

## Guardrails

1. **Agent-governance does not act on its own findings.** It proposes; David (or `rick-orchestrator` with David's approval) decides.
2. **It does not create agents, skills, or routing changes.** It may recommend them; implementation goes through the normal slice workflow.
3. **It does not override ROLE.md boundaries.** If it detects a boundary violation, it reports it — it does not enforce.
4. **It does not replace `improvement`.** The `improvement` team continues to route general improvement intents. Governance findings that need work become Linear issues in `Mejora Continua Agent Stack`.
5. **It runs on demand or on a periodic cadence set by David.** No autonomous cron without explicit approval.

## Invocation

For now, agent-governance is invoked manually by David or by `rick-orchestrator` when a phase closes or when David asks "how is the system doing?"

Future: if David approves, a periodic cron (e.g., weekly) can invoke this function and post the report to Notion or Linear.

## Next slices (not in scope now)

- Instrument per-agent session telemetry in OpenClaw
- Add skill-level invocation logging
- Build a governance task handler (`system.agent_governance_report`) that automates data collection
- Add structured handoff telemetry aggregation
- Create a periodic cron for governance reports
