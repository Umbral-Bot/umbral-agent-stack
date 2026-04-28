# Editorial Agent Flow — Source-driven AEC/BIM to LinkedIn

> Status: repo-side process contract. This document does not activate runtime agents, edit Notion, publish, or change human gates.

## Purpose

This document defines the editorial handoff sequence for source-driven public content in Umbral, especially when a general AI, automation, or operations idea must be connected to the AEC/BIM domain before becoming LinkedIn copy.

The core design rule is separation of responsibility:

- source curation decides what can be said;
- AEC/BIM contextualization decides how it applies to construction, BIM, coordination, delivery, or automation;
- LinkedIn writing turns the payload into readable social copy;
- communication direction calibrates David's voice;
- QA validates claims, traceability, gates, and safety;
- David approves.

## Canonical Flow

```text
1. sources / signals
2. source curation and candidate payload
3. AEC/BIM context framing
4. LinkedIn draft writing
5. communication direction / David voice calibration
6. editorial QA
7. Notion draft registration by operator
8. David review
9. human content approval
10. human publication authorization
```

## Agents And Responsibilities

| Step | Owner | Status | Responsibility | Not responsible for |
| --- | --- | --- | --- | --- |
| 1-2 | `rick-editorial` or source-driven flow | design-only / manual today | Curate sources, separate primary source vs referent, produce candidate payload | Final voice, publication, gates |
| 3 | `rick-editorial` now; future `rick-aec-context-curator` if needed | proposed responsibility | Connect the idea to AEC/BIM with defensible operational examples and claim boundaries | Writing polished LinkedIn copy, voice pass |
| 4 | `rick-linkedin-writer` using `linkedin-post-writer` | runtime-registered, read-only/dry-run | Write concise LinkedIn/X drafts from the payload and AEC/BIM frame | Inventing AEC/BIM context, adding sources, David voice finalization |
| 5 | `rick-communication-director` | runtime-registered, read-only/dry-run | Calibrate David's voice, naturalness, first paragraph, wording, closing cadence | Source curation, AEC/BIM thesis ownership, QA verdict |
| 6 | `rick-qa` | existing QA role | Validate claims, traceability, length, safety, gates, publication restrictions | Primary drafting, rewriting as default |
| 7 | Operator / Copilot / VPS handoff | manual / authorized | Register the current candidate in Notion as `Borrador` only | Approving gates or publishing |
| 8-10 | David | human gate | Review, approve content, authorize publication | Delegated to no agent |

## AEC/BIM Context Responsibility

The AEC/BIM connection must be decided before writing the LinkedIn post.

The responsible step is:

```text
source curation / AEC-BIM context framing
```

The initial owner is `rick-editorial` because it already owns candidate payloads, source separation, angle, and claims. If this becomes frequent or complex, create a dedicated `rick-aec-context-curator` role or skill.

### Expected Output

```yaml
aec_angle: ""
bim_relevance: ""
operational_examples:
  - ""
allowed_terms:
  - ""
terms_to_avoid:
  - ""
claim_boundaries:
  - ""
source_trace:
  - claim: ""
    source: ""
    confidence: ""
handoff_to_linkedin_writer:
  objective: ""
  audience: ""
  tone: ""
  constraints:
    - ""
```

### Example For CAND-003

```yaml
aec_angle: "AI automation in BIM teams needs explicit review and acceptance criteria before scaling."
bim_relevance: "The post applies to BIM coordination, model review, issue closure, deliverable acceptance, and decision-oriented reporting."
operational_examples:
  - "model ready for review"
  - "observation that requires rework"
  - "deliverable ready to move to the next stage"
  - "report that helps or does not help decision-making"
terms_to_avoid:
  - "AEC/BIM" as a bare opening label
  - "nivel de coordinacion" without operational grounding
  - "escalacion" in public copy
claim_boundaries:
  - "Do not imply all BIM teams have this problem."
  - "Use conditional language: many teams, when criteria are unclear, or in teams where the process is still informal."
```

## LinkedIn Writer Responsibility

The proposed `rick-linkedin-writer` should not invent the AEC/BIM angle. It should use the AEC/BIM frame it receives.

It may improve wording, structure, hook, rhythm, and length, but it must not:

- add technical claims;
- create new AEC/BIM examples not present in the handoff;
- add sources;
- turn inference into fact;
- decide that a claim is safe without QA.

Default output should be concise:

- LinkedIn medium by default: 180-260 words;
- compressed version required if the draft exceeds 300 words without explicit reason;
- X copy should be direct and not try to summarize everything.

## Communication Director Responsibility

`rick-communication-director` is responsible for whether the copy sounds like David.

It may:

- improve first paragraph coherence;
- remove bare sector labels such as `AEC/BIM` when they sound unnatural;
- replace abstract phrases with operational scenes;
- tighten the closing cadence;
- convert repeated human feedback into persistent calibration rules.

It must not become the owner of source selection, AEC/BIM claim framing, or primary LinkedIn drafting once `rick-linkedin-writer` exists.

## QA Responsibility

`rick-qa` validates the output after voice calibration.

It must check:

- source traceability;
- claim strength;
- unsupported AEC/BIM generalizations;
- length policy;
- artificial or generic voice;
- gates remain false;
- Notion remains `Borrador`;
- no publication happened.

It should return `pass`, `pass_with_changes`, or `blocked`.

## Repo-side Vs Runtime Live

Creating files in the repo does not make them available to an OpenClaw runtime agent.

For every runtime agent or skill, document separately:

1. repo-side files;
2. live workspace files under `~/.openclaw/workspaces/<agent-id>/`;
3. live config entry in `~/.openclaw/openclaw.json`;
4. gateway restart command;
5. smoke test proving the agent can read its `ROLE.md`, `AGENTS.md`, `SKILL.md`, and auxiliary files.

## Current Implementation Stance

As of 2026-04-24:

- `rick-communication-director` exists as runtime-registered, read-only/dry-run.
- `rick-linkedin-writer` exists as runtime-registered, read-only/dry-run. Permissions hardened (minimal alsoAllow, 29 deny entries). See `cand-003-linkedin-writer-runtime-smoke.md`.
- `rick-aec-context-curator` is a proposed responsibility, not necessarily a runtime agent.
- The AEC/BIM framing responsibility should first be documented under `rick-editorial` or as a new skill before creating another runtime agent.
- Notion updates remain operator/human controlled and must keep candidates in `Borrador`.

## Implementation Decision Rules

Do not create new runtime agents or skills until the existing repo-side skills have been checked for overlap.

Before implementing `rick-linkedin-writer`, audit at least:

- `openclaw/workspace-templates/skills/linkedin-content/SKILL.md`
- `openclaw/workspace-templates/skills/linkedin-david/SKILL.md`
- `openclaw/workspace-templates/skills/editorial-source-curation/SKILL.md`
- `openclaw/workspace-templates/skills/bim-coordination/SKILL.md`

Recommended implementation order:

1. Add or extend an AEC/BIM context framing capability under the source-driven/editorial stage.
2. Decide whether `linkedin-content` or `linkedin-david` can be extended, or whether a separate `linkedin-post-writer` skill is justified.
3. If a separate runtime is still justified, create `rick-linkedin-writer` as read-only/dry-run and force it to read its writing rules through workspace `AGENTS.md`.
4. Keep `rick-communication-director` as voice calibration only.
5. Harden `rick-qa` so long, artificial, or unsupported copy cannot pass.

`rick-linkedin-writer` is justified only if it has a distinct accountability boundary:

- first-pass LinkedIn/X drafting;
- length control;
- rule-based anti-slop;
- structured handoff to `rick-communication-director`;
- no source invention;
- no voice-final approval;
- no publication or gates.

If the same result can be achieved by extending `linkedin-david` plus adding an AEC/BIM context framing skill, prefer that lighter repo-side change before activating a new runtime agent.
