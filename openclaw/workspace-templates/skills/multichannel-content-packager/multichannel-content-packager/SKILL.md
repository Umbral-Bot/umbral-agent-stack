---
name: multichannel-content-packager
description: convert an approved master draft into coordinated channel-specific versions for linkedin, x, blog, newsletter, and instagram while preserving the core thesis and adapting hook, length, structure, and call to action for each channel. use when chatgpt needs to package one approved idea into a reusable multichannel set, keep a canonical master version plus derivatives, generate non-mechanical variants, mark channel readiness, and prevent any implication that content is cleared for publication before final human approval.
---

# Multichannel Content Packager

Convert one approved idea into a channel-native content package without changing the underlying thesis, facts, or commitments.

Read [references/official-channel-notes.md](references/official-channel-notes.md) when the task depends on platform-specific behavior, limits, or packaging decisions. Read [references/example-prompts.md](references/example-prompts.md) when you need concrete examples of how to apply this skill.

## Core operating rules

- Treat the approved master draft as the source of truth.
- Preserve the central thesis exactly in meaning, even when wording changes by channel.
- Preserve all facts, numbers, names, dates, claims, and commitments unless the user explicitly changes them.
- Rewrite natively for each channel. Do not mechanically trim, pad, or synonym-swap the same text.
- Keep one canonical master version and one derived section per requested channel.
- Mark every requested channel as `ready`, `needs review`, or `missing`.
- Never say the package is approved for publication. Treat it as prepared for review unless the user explicitly states final approval has been granted.
- Do not publish, schedule, simulate posting, or imply that posting should happen automatically.
- When platform capabilities are uncertain, use the conservative official default rather than guessing based on rumors, experiments, or unofficial best practices.

## Workflow

Follow this sequence.

### 1. Validate the source

Confirm whether the source is an approved master draft.

If approval is unclear:
- continue packaging as a draft set
- mark all channels at least `needs review`
- state that final approval is still required before publication

Extract and preserve:
- thesis
- audience
- primary takeaway
- proof points
- CTA intent
- constraints such as tone, prohibited claims, hashtags, links, or campaign goals

### 2. Freeze the canonical master version

Create a `master version` section.

- Normalize messy input into the clearest reusable canonical version.
- Preserve meaning exactly.
- Do not add new claims.
- Do not optimize for one channel inside the master version.

### 3. Select the right adaptation mode per channel

For each requested channel:
1. preserve the thesis
2. choose a channel-native hook
3. adapt the length to the channel
4. reshape the structure to match reading behavior
5. choose a channel-appropriate CTA
6. vary rhythm and framing so the outputs are not clones

### 4. Apply channel rules

#### LinkedIn

Optimize for professional relevance, credibility, and useful takeaways.

Default organic post structure:
- hook
- context or problem
- insight
- proof point or example
- takeaway
- CTA

Default guidance:
- usually 120 to 300 words unless the user requests otherwise
- make the first two lines strong enough to stand alone
- prefer crisp paragraphs and specific language
- keep the tone informed, concrete, and non-hypey
- use a CTA that invites reflection, discussion, or a practical next step

Only when the user explicitly asks for sponsored or paid LinkedIn copy:
- tighten headline-style copy aggressively
- prefer concise value-first copy
- keep paid creative headlines short

Only when the user explicitly asks for a LinkedIn article or LinkedIn newsletter edition:
- switch from post structure to title plus long-form body structure
- plan for a cover image note if relevant
- keep the thesis consistent with the master version

#### X

Optimize for speed, clarity, and memorability.

Choose the smallest format that carries the idea cleanly:
- single post when one sharp point is enough
- thread when sequencing materially improves understanding

Default guidance:
- assume a standard post limit unless the user explicitly says Premium or long-form posting is available
- front-load the strongest angle
- strip filler, throat-clearing, and abstract marketing language
- keep CTA lightweight: reply, question, read more, or continue the thread
- if you propose media, keep the media note concise and within official platform behavior

#### Blog

Optimize for depth, scannability, and logical progression.

Use this structure:
- title
- subheading
- introduction
- 3 to 5 sections with descriptive subheads
- conclusion
- CTA

Guidance:
- expand the reasoning, not just the wording
- add transitions and section labels that help scanning
- keep all claims faithful to the master version
- when input is too thin for a full post, deliver a concise draft plus outline and mark `needs review`

#### Newsletter

Default to an email-style newsletter unless the user names a specific newsletter platform.

Use this structure:
- subject line
- preview text
- opening
- body
- CTA

Guidance:
- sound direct and human
- make the "why now" clear early
- avoid turning the newsletter into a pasted blog intro
- if the user actually wants a LinkedIn newsletter edition, adapt it as long-form LinkedIn content instead and state that assumption
- if the destination platform is ambiguous and the format matters, mark `needs review` and note the ambiguity

#### Instagram

Treat this channel as future-facing unless the user explicitly asks for an instagram-ready output.

Use this structure:
- concept angle
- caption
- optional visual or slide sequence note
- CTA

Guidance:
- adapt for visual storytelling and caption rhythm
- do not assume assets, reel format, or carousel format unless the user asks for them
- if you propose a carousel and the user has not stated account-specific newer limits, stay conservative on official documented limits
- remember that carousel posts use one caption and one location for the whole post
- if visual direction is missing, mark `needs review` or `missing` and name the missing input

### 5. Assess readiness

Assign one status per requested channel:
- `ready`: usable draft with no obvious missing inputs
- `needs review`: materially drafted but still needs human review for tone, legal, brand, links, creative, or platform ambiguity
- `missing`: cannot be responsibly drafted because critical information is absent

Always explain every non-ready status.

### 6. Run the quality gate

Check all of the following before finalizing:

#### Integrity
- preserve the same thesis everywhere
- keep all facts aligned with the master version
- preserve the intended audience
- keep CTA intent aligned with campaign goals

#### Adaptation
- open each channel differently
- make each channel feel native to its format
- adapt structure rather than compress mechanically
- vary hooks, rhythm, and framing purposefully

#### Platform discipline
- do not assume premium or advanced platform features unless the user says they are available
- use conservative official defaults when platform-specific constraints matter
- separate email newsletter logic from LinkedIn newsletter logic
- avoid inventing asset specs, media counts, or posting affordances

#### Readiness
- include every requested channel
- label every requested channel
- explain every non-ready status concretely
- include the approval protection note at the end

## Anti-patterns

Avoid these failures:

- pasting the master draft into every channel with light trimming
- using the same hook across channels
- repeating the same CTA everywhere without channel intent
- writing X like a broken LinkedIn paragraph
- writing newsletter like a pasted blog intro
- writing Instagram as if visuals already exist when they do not
- assuming premium features, extra character allowance, or expanded carousel limits without user confirmation
- inventing facts, outcomes, or metrics
- defaulting to heavy hashtag or emoji use
- marking a channel `ready` when key inputs are still missing
- implying the package can now be posted or scheduled

## Output format

Use this structure unless the user asks for another packaging format.

```markdown
# Multichannel content package

## Source summary
- Thesis:
- Audience:
- Primary takeaway:
- CTA intent:
- Constraints:

## Master version
[canonical approved master version]

## Channel status matrix
| Channel | Status | Why |
|---|---|---|
| LinkedIn | ready / needs review / missing | ... |
| X | ready / needs review / missing | ... |
| Blog | ready / needs review / missing | ... |
| Newsletter | ready / needs review / missing | ... |
| Instagram | ready / needs review / missing | ... |

## LinkedIn
**Status:** ...
[final LinkedIn adaptation]

## X
**Status:** ...
[final X adaptation or thread]

## Blog
**Status:** ...
[final blog draft or concise draft plus outline]

## Newsletter
**Status:** ...
[final newsletter draft]

## Instagram
**Status:** ...
[concept, caption, optional visual notes]

## Approval note
Prepared for review only. Do not publish or schedule until final approval is explicitly given.
```
