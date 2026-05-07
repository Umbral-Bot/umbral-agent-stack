# ADR-011 — Codegen backend stage gate (Plan B: Hostinger)

- **Date:** 2026-05-06
- **Status:** Proposed (placeholder — source handoff inaccessible from VPS at promotion time; see "Source & Block" below)
- **Owner:** umbral-bim
- **Related:** O5, ADR-009 (Mission Control scope), `umbral-bot-2`

## Context (from caller summary, NOT from full handoff)

Codegen backend Plan A (Azure-native) was deferred. Plan B uses Hostinger to host the codegen backend stage gate so it is not coupled to Azure Sponsorship cost lifecycle (`2026-07-30` expire — see [docs/runbooks/azure-off-sponsorship-2026-07-30.md](../runbooks/azure-off-sponsorship-2026-07-30.md)).

The full reasoning, alternatives evaluated, and acceptance criteria live in:

```
notion-governance/docs/handoffs/2026-05-06-O5-codegen-backend-decision-plan-B-hostinger.md
```

## Decision

**Pending population.** This ADR is a placeholder so that:

1. Cross-references from `umbral-agent-stack` to "the O5 decision" resolve to a real file in the repo.
2. The numbering slot is reserved (next sequential after ADR-010).
3. PR-level discussion can attach here while the source handoff is being made accessible.

## Source & Block

The promotion of this ADR from the source handoff was attempted on `2026-05-06` from the VPS by `copilot-vps`. **It is blocked because the GitHub token available on the VPS (account `UmbralBIM`) does not have read access to `Umbral-Bot/notion-governance`.**

Verification:

```bash
gh api repos/Umbral-Bot/notion-governance --jq '.full_name'
# => 404 Not Found
gh api orgs/Umbral-Bot/repos --jq '.[].full_name'
# => Umbral-Bot/umbral-agent-stack   (only repo visible)
```

Local clones at `~/notion-governance-git` and `~/notion-governance-local` are stale (HEAD = `1ddd29c`, last fetch `2026-04-12`) and do not contain the 2026-05-06 handoff or commit `1317d05`.

To unblock: David grants the VPS token read scope on `Umbral-Bot/notion-governance`, or pushes the two 2026-05-06 handoffs into `umbral-agent-stack/.cache/handoffs/` for one-time promotion. Either path triggers a follow-up commit that flips this ADR's status from `Proposed` to `Accepted` and replaces the placeholder Decision section with the actual content.

## Consequences (placeholder)

To be populated after source handoff is read.

## References

- Source handoff (inaccessible from VPS at promotion time): `notion-governance/docs/handoffs/2026-05-06-O5-codegen-backend-decision-plan-B-hostinger.md`
- Governance commit referenced by caller: `notion-governance@1317d05`
- Off-Sponsorship runbook (related cost lifecycle context): [docs/runbooks/azure-off-sponsorship-2026-07-30.md](../runbooks/azure-off-sponsorship-2026-07-30.md)
