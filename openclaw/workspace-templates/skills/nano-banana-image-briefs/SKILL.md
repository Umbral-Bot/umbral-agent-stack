---

name: nano-banana-image-briefs

description: convert approved content drafts into visual briefs and editable image-generation

  prompts for three clearly differentiated alternatives aligned to brand, audience,

  and channel. use when a draft, post, campaign concept, or approved copy needs art

  direction, prompt variants, composition guidance, overlay text rules, aspect-ratio

  recommendations, or a pre-generation visual risk review.

metadata:

  openclaw:

    emoji: ??

    requires:

      env: []

---



# Nano Banana Image Briefs



Convert an approved draft into image briefs that another ChatGPT instance can use before generating visuals.



## Workflow



1. Read the approved content and extract the non-negotiables.

2. Infer the art direction from the message, audience, and channel.

3. Propose exactly 3 visual directions with meaningful differences.

4. Write a complete visual brief for each direction.

5. Produce editable prompts that David can tweak before generation.

6. Run a brand-risk and legibility review before finalizing.



If details are missing, make conservative assumptions from the approved draft and label them clearly. Do not block waiting for perfect inputs unless the request is impossible.



## Required inputs



Use whatever the user provides. Common inputs:

- approved draft or final copy

- campaign or content goal

- target audience

- channel or placement

- brand cues, visual references, or constraints

- required claims, product terms, CTA, or forbidden topics

- preferred aspect ratio or output format

- locale or language



## Step 1: extract what the image must communicate



Derive these items from the approved content before proposing visuals:

- core promise: what the audience should understand in one glance

- emotional tone: e.g. credible, urgent, optimistic, premium, technical

- proof points or supporting cues: data, UI, workflow, person, environment, object, metaphor

- audience mindset: awareness level, likely objections, visual sophistication

- channel behavior: what wins attention in this channel without breaking brand trust

- non-negotiables: exact product names, taboo imagery, mandatory text, legal or brand constraints



Do not merely restate the copy. Translate the message into visual decisions.



## Step 2: derive the art direction



Turn the content into a concise art-direction diagnosis with these fields:

- message hierarchy

- visual metaphor or scene logic

- hero subject

- supporting elements

- preferred realism level

- energy level

- trust signals

- brand expression



Use the diagnosis to explain why the chosen visual language fits the approved content.



## Step 3: create exactly 3 differentiated variants



The three variants must not feel like color swaps of the same idea. Create clear contrast across at least three of these dimensions:

- concept angle

- subject choice

- scene type

- composition

- realism vs illustration

- lighting and mood

- palette strategy

- camera distance or framing

- amount and treatment of overlay text



A good pattern is:

- Variant 1: safest and most brand-stable

- Variant 2: more conceptual or metaphor-led

- Variant 3: more performance-oriented or channel-native



If one of those patterns does not fit, still ensure the 3 options are clearly different in both idea and execution.



## Step 4: use this visual brief structure for each variant



Always structure each brief with these sections in this order:



### Variant title

A short descriptive label.



### Strategic role

State what this variant is trying to achieve and why it fits the audience and channel.



### Concept

Summarize the scene or idea in 2 to 4 sentences.



### Composition

Specify:

- focal point

- layout balance

- foreground and background

- negative space

- reading path

- safe area for any text overlay



### Style and finish

Specify:

- realism or illustration level

- texture and polish

- lighting

- depth of field

- lens feel or camera distance

- any rendering cues



### Color direction

Specify:

- dominant colors

- accent colors

- contrast approach

- saturation level

- how brand colors should appear naturally rather than as forced blocks



### Text overlay

Specify:

- whether to use overlay text

- max amount of text

- placement

- weight and contrast expectations

- when to avoid overlay entirely



### Format

Specify:

- recommended aspect ratio

- crop behavior for channel

- mobile-safe concerns

- whether the prompt should preserve whitespace for headlines or UI framing



### Avoid

List the main failure modes for this variant.



### Editable prompt

Output a prompt David can edit directly before generation.



### Prompt knobs

Give 5 to 8 editable variables such as subject, mood, palette, framing, overlay density, realism level, background complexity, and crop.



## Step 5: prompt format



Write prompts in two layers:



### A. Master prompt

Use one paragraph that includes, in natural order:

- subject and scene

- strategic intent

- composition and framing

- lighting and mood

- style and finish

- palette

- channel-safe text overlay instructions if relevant

- output format and aspect ratio

- explicit anti-generic guidance



### B. Negative guidance

Add a short line beginning with `Avoid:` followed by things to exclude.



The prompt must be editable, specific, and generator-ready. Avoid giant keyword dumps. Favor clear prose over comma spam.



## Channel rules



Apply these defaults unless the user specifies otherwise.



### linkedin organic

- optimize for credibility, clarity, and fast comprehension

- prefer 1:1 or 4:5 unless the use case says hero/banner

- keep overlay text short and highly legible

- favor concrete business context over trendy visual gimmicks

- avoid stock-like corporate poses, fake handshakes, generic office smiles, or unexplained abstract 3D objects



### x or short-form social

- prioritize a single fast hook

- simplify the scene; fewer elements read better at speed

- make the focal point obvious at thumbnail size

- keep overlay minimal or omit it entirely



### instagram

- push aesthetic distinctiveness more than in b2b channels

- use stronger mood, color, or visual metaphor when brand allows

- design for mobile crops first

- do not sacrifice legibility for style



### blog hero or landing page hero

- prefer wide formats such as 16:9, 3:2, or a specified site crop

- reserve whitespace for headline and UI chrome when needed

- favor durable visuals that can survive multiple downstream crops

- avoid noisy detail behind likely headline zones



### email header

- use wide, shallow compositions

- keep the center band clear and legible

- avoid tiny details that disappear in inbox previews



### paid social or display

- focus the image on one claim, one object, or one scene logic

- reduce clutter aggressively

- avoid ambiguous metaphors that weaken conversion intent

- keep legal or brand-sensitive text outside the generated image unless explicitly required



If the channel is unknown, recommend a default aspect ratio and explain the assumption.



## Generator compatibility and ratio mapping



Keep the brief channel-first, then translate it to the target image tool only at the end.



- If the user is generating in ChatGPT Images or Sora image mode, prefer these native ratios: 1:1, 3:2, 2:3.

- If the user is generating through the OpenAI Image API, prefer these native sizes: 1024x1024, 1536x1024, 1024x1536, or `auto` when no exact framing is required.

- If the ideal channel crop is 4:5, 16:9, or another non-native ratio, choose the nearest supported generation ratio and explicitly preserve crop-safe space for the intended downstream crop.

- When translating formats, state both: `generation ratio` and `intended delivery crop`.

- Never let a platform ratio limitation force a weaker concept; adapt framing and whitespace instead.



## Brand-safety and legibility review



Before finalizing, check every variant for:

- generic stock energy

- mismatch between image tone and approved copy

- overcrowding or weak focal hierarchy

- low contrast behind overlay text

- dependence on tiny details that will fail on mobile

- cliché metaphors that undermine credibility

- off-brand color usage

- accidental implications the product or company cannot support

- visuals that may look like another brand category



If any risk is present, revise the brief and prompt rather than merely noting the issue.



## Anti-generic rules



Never default to:

- smiling team around laptop

- person pointing at floating dashboard with no narrative reason

- random blue-purple gradients with glossy shapes

- vague futuristic cityscapes

- meaningless holograms

- overused “innovation�? iconography

- stock-photo body language that feels posed or canned



Instead, anchor the image in the actual message, use a credible scene logic, and choose distinctive details that could plausibly belong to this brand and audience.



## Output format



Use this exact top-level structure:



# Visual direction summary

- Core message:

- Audience:

- Channel:

- Key assumptions:

- Overall art direction:



# Variant 1

[full brief using the required brief structure]



# Variant 2

[full brief using the required brief structure]



# Variant 3

[full brief using the required brief structure]



# Final recommendation

- Best default choice:

- Why:

- Main risk to watch:

- What David may want to edit first:



## Optional reference



If the user needs a faster or reusable output skeleton, use the template in `references/image-brief-template.md`.



