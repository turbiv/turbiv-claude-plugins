# Prompt construction for OpenAI GPT Image (gpt-image-1 to gpt-image-2.6)

Research notes for the OpenAI images plugin. Collected 2026-11-20.
Part A is the sourced findings. Part B is a draft prompt-writing guide for the skill file.

Source tags used below:

- **[OAI]**: OpenAI official docs, Cookbook or OpenAI-maintained skill (openai/skills).
- **[COMM]**: community skills, forum posts, vendor blogs. Not verified by OpenAI.
- **[RES]**: research papers (arXiv preprints, ECCV).
- **[OURS]**: our own recommendation, based on the above. Not from a source.

---

## Part A. Findings

### A0. Key takeaways

1. OpenAI's own rules are stable from gpt-image-1.5 to 2.6. The same eight "prompting fundamentals" appear in the 1.5 Cookbook, the gpt-image-2 Cookbook and the 2.5/2.6 docs page. [OAI]
2. The core structure is: **intended use, then scene, subject, details, constraints**. Use labeled sections for complex prompts. Any format works (prose, labels, JSON-like); choose the one that is easiest to read and change. [OAI]
3. Quote all text that must appear. Say where it goes, the typography, and how many times. Spell hard words letter by letter. Ask for "no extra text". Then **read the output and check it**. [OAI]
4. For edits: "change only X", then a preserve list. Repeat the preserve list on every turn. One change per turn. [OAI]
5. OpenAI uses short, targeted negative lines ("No extra text, no watermarks, no unrelated logos") in almost every official example. The "positive framing only" rule from some community skills is not what OpenAI does. [OAI] vs [COMM]
6. OpenAI recommends that you check each result against the requirements (text, labels, identity, locality of edit, alpha). Its image-evals Cookbook gives a ready rubric: hard pass/fail gates first (instruction following, exact text), then 0-5 quality scores. [OAI]
7. The OpenAI Codex `imagegen` skill is the best template for our skill. It has a use-case taxonomy, a labeled prompt schema, a "specificity policy" (how much detail the agent may add), and an inspect-then-iterate step. [OAI]
8. Image API calls do not rewrite the prompt. (The Responses API tool does; it returns `revised_prompt`.) In our plugin, Claude is the prompt rewriter. [OAI]

### A1. Sources read

| Source | Tag | Notes |
|---|---|---|
| [Image prompting guide (GPT-Image-2.6 / 2.5 tabs)](https://developers.openai.com/api/docs/guides/image-prompting) (markdown: `image-prompting.md`) | OAI | The current primary guide. The tabs for 2.6 and 2.5 have the same 8 fundamentals. The tabs for gpt-image-2, 1.5 and 1 are short parameter references. The old Cookbook URL now redirects here. |
| [Image generation guide](https://developers.openai.com/api/docs/guides/image-generation) | OAI | API mechanics: complexity, masks, markup, SVG, GIF, sizes, limitations, moderation, errors, `revised_prompt`. |
| [Images API reference: generate](https://developers.openai.com/api/reference/resources/images/methods/generate) | OAI | Prompt max **32,000 characters**. No `seed` or `negative_prompt` parameter. |
| [Cookbook notebook: image-gen-models-prompting-guide.ipynb (gpt-image-2)](https://github.com/openai/openai-cookbook/blob/main/examples/multimodal/image-gen-models-prompting-guide.ipynb) | OAI | Dated 2026-04-21, updated 2026-08-20. Has the longest "Prompting Fundamentals" text. |
| [Cookbook: gpt-image-1.5 prompting guide](https://github.com/openai/openai-cookbook/blob/main/examples/multimodal/image-gen-1.5-prompting_guide.ipynb) | OAI | Earlier version of the same rules. |
| [Cookbook: Image evals for image generation and editing](https://github.com/openai/openai-cookbook/blob/main/examples/multimodal/image_evals.ipynb) | OAI | LLM-as-judge rubrics for generated images. |
| [Cookbook: Transparent image assets](https://github.com/openai/openai-cookbook/blob/main/examples/multimodal/transparent-image-assets-for-campaigns-and-presentations.ipynb) | OAI | Transparency rules. |
| [openai/skills: `.system/imagegen`](https://github.com/openai/skills/tree/main/skills/.system/imagegen) (SKILL.md, references/prompting.md, references/sample-prompts.md) | OAI | The Codex built-in image skill. |
| [wuyoscar/GPT-Image2-Skill](https://github.com/wuyoscar/GPT-Image2-Skill) (about 6.2k stars), `skills/gpt-image/SKILL.md`, `references/craft.md` | COMM | Large prompt gallery and a "craft" guide. |
| [smixs/visual-skills](https://github.com/smixs/visual-skills) (about 720 stars), `image/SKILL.md`, `references/gpt-image.md`, `golden-rules.md`, `patterns/poster-illustration.md` | COMM | A 5-slot template, banned "slop" words, a Style DNA and Reject Checklist. |
| [glebis/claude-skills `gpt-image-2`](https://github.com/glebis/claude-skills/tree/main/gpt-image-2) (about 410 stars) | COMM | A Claude Code skill: presets, draft then final, a preflight contradiction check. |
| [vargHQ/skills `gpt-image-2-6`](https://github.com/vargHQ/skills/tree/main/gpt-image-2-6) | COMM | 2.6 measurements and a failure-to-fix table. |
| [steipete/agent-scripts `openai-image-gen`](https://github.com/steipete/agent-scripts/tree/main/skills/openai-image-gen) | COMM | A random structured prompt sampler with a gallery. Little prompt guidance. |
| MCP servers, e.g. [SureScaleAI/openai-gpt-image-mcp](https://github.com/SureScaleAI/openai-gpt-image-mcp) | COMM | Thin API wrappers. The tool descriptions give no prompt-writing guidance. In this ecosystem the prompt craft lives in skills. |
| [OpenAI forum: GPT-image 2.0 issues/workarounds thread](https://community.openai.com/t/collection-of-gpt-image-generator-2-0-issues-bugs-and-work-around-tips-check-first-post/1379535) | COMM | |
| [OpenAI forum: moderation over-refusals on gpt-image-2](https://community.openai.com/t/api-issue-moderation-over-refusals-on-gpt-image-2-with-moderation-low-where-chatgpt-always-succeeds/1388964) | COMM | Includes a reply from OpenAI staff. |
| [Kittl review of GPT Image 2](https://www.kittl.com/blogs/kittl-review-gpt-image-2-0/) | COMM | Vendor review with a list of weaknesses. |
| [Idea2Img (ECCV 2024, arXiv 2310.08541)](https://arxiv.org/abs/2310.08541), [CRAFT (arXiv 2512.20362)](https://arxiv.org/abs/2512.20362), [Iterative Refinement Improves Compositional Image Generation (arXiv 2601.15286)](https://arxiv.org/abs/2601.15286), M3 (arXiv 2602.06166, seen in search only) | RES | Loops where a vision model critiques the image and the prompt is then revised. |

### A2. Model and parameter facts that affect prompting [OAI]

- **Models (Nov 2026):** `gpt-image-2.6-flare` (small, fast) and `gpt-image-2.6-sunburst` (base model, "more detail or precise edits"), released 2026-11-04. Also `gpt-image-2.5-flare/-sunburst` (2026-09-08) and `gpt-image-2`. `gpt-image-1` was shut down on **2026-10-23**. `gpt-image-1.5` shuts down on **2026-12-01**.
- OpenAI's advice on which model to start with: "start with GPT-Image-2.6 Flare if response time matters most. Start with GPT-Image-2.6 Sunburst if the image must meet demanding requirements for detail, layout, or edit accuracy."
- **`quality`:** `auto | low | medium | high | xhigh | max` on 2.5 and 2.6. "Controls how much visual detail the model can render, such as texture or small lettering." Use `low` for drafts. For small text, dense information or several fonts, compare `medium` and `high`.
- **`complexity`** (2.6 only): `low | medium | high`; the default is `high`. "Controls how much the model plans before rendering." High can help dense text, complex layouts and relationships between objects. It "can increase latency and introduce unwanted changes". **Start with `low` for targeted edits.** If the prompt already fixes the layout, text and style, a higher setting "may make little visible difference". Complexity has no separate fee.
- **`size`:** `auto` or `WxH`. Both sides must be multiples of 16, the aspect ratio must be between 1:3 and 3:1, no edge may exceed 3840 px, and the total must be 655,360 to 8,294,400 px. Common sizes: 1024x1024, 1536x1024, 1024x1536, 1536x864 (16:9 slide), 2048x1152, 3840x2160. Above 2560x1440 is "experimental" on 2.5.
- **Aspect ratio goes in `size`, not only in the prompt.** OpenAI fundamental #1 also says to state the aspect ratio and placement in the prompt.
- **`background: transparent`** requires PNG or WebP. Check the decoded alpha channel.
- **`output_format`:** `png | jpeg | webp`, plus `svg` (generations only, `n=1`) and `gif` (2-16 frames) on 2.6.
- **`markup`** (2.6 edits): a transparent PNG overlay with circles or arrows drawn on it, the same size as the first input image. The prompt then refers to it: "inside the red circle". Do not combine it with `mask`.
- **Masks** are "entirely prompt-based. The model uses the mask as guidance, but may not follow its exact shape with complete precision."
- **No input_fidelity** on gpt-image-2 and later. Inputs are always processed at high fidelity.
- **Prompt length:** up to 32,000 characters.
- **No seed and no negative-prompt parameter** in the Images API. (glebis' skill uses a `--seed` flag; it is not in the API reference, so treat it as unverified.)
- **Moderation:** `moderation: auto | low`. Both prompts and outputs are checked. A blocked request returns `error.code = "moderation_blocked"` and `moderation_details.moderation_stage` (`input` or `output`) with categories. "Don't automatically retry these errors without modifying the prompt or input images."
- **Limitations listed by OpenAI:** latency up to 2 minutes; text "can still struggle with precise text placement and clarity"; consistency of recurring characters or brand elements; "difficulty placing elements precisely in structured or layout-sensitive compositions."

### A3. OpenAI's prompting fundamentals, rule by rule [OAI]

From the 2.6 guide, "Prompting fundamentals", with additions from the gpt-image-2 Cookbook:

1. **Define the result.** "Name the subject and intended use, such as a product photograph, advertisement, or diagram. Specify the composition, aspect ratio, and important placement constraints. For complex requests, organize the prompt as scene, subject, details, and constraints, using labeled sections." The Cookbook says the intended use "set[s] the 'mode' and level of polish" and gives the order as "background/scene → subject → key details → constraints".
2. **Format.** "Short prompts, descriptive paragraphs, JSON-like structures, instructions, and tags can all express the same intent." The Cookbook adds: "For production systems, prioritize a skimmable template over clever prompt syntax."
3. **Visible details.** Name the materials, lighting, colors and visual medium. Ask for "photorealistic" or "real photograph" explicitly. The Cookbook says the word "photorealistic" "strongly engage[s] the model's photorealistic mode". "Treat camera specifications as cues for appearance, not a guarantee of exact physical simulation." For wide, cinematic, low-light, rainy or neon scenes, "specify scale, atmosphere, and color instead of relying on mood words alone".
4. **People and actions.** "Describe body framing, relative scale, gaze, and interaction with objects", e.g. "full body visible, feet included", "looking down at the open book", "hands naturally gripping the handlebars".
5. **Exact text.** "Put required wording in quotes and describe its position and typography. Spell unusual words or brand names letter by letter when needed. Ask for no extra text, then check spelling and legibility." The Cookbook also allows ALL CAPS for literal text. The 2.6 "Render exact text" example says to "tell the model how many times it should appear" ("Render the tagline exactly once").
6. **Separate changes from constraints.** "say 'change only X' and list the details to preserve, such as identity, geometry, layout, lighting, or labels. State exclusions such as unwanted text, logos, or watermarks. For precise local edits, also identify saturation, contrast, arrows, camera angle, and surrounding objects that must remain unchanged."
7. **Roles for references.** "Identify each input by number and purpose: subject, style, clothing, or background. Explain how the inputs should combine and which elements should move where."
8. **Iterate deliberately.** "Pass the previous output as the next edit input, request one change, and repeat the details to preserve ... restate critical constraints if the result drifts. Compare results before adding more instructions." The Cookbook says: "Long prompts can work well, but debugging is easier when you start with a clean base prompt and refine with small, single-change follow-ups."

**Prompt length:** OpenAI sets no ideal length. Its examples run from one sentence ("Remove the flower from man's hand. Do not change anything else.") to about 150 words for slides. Most are 40-120 words. The Cookbook says "Long prompts can work well". The 1.5 guide adds: "camera/composition terms ... often steer realism more reliably than generic '8K/ultra-detailed.'"

### A4. Use-case guidance from the official examples [OAI]

- **Photorealism** (sailor example): subject, then texture ("visible wrinkles, pores, and sun texture"), then action, then capture ("Shot like a 35mm film photograph, medium close-up at eye level, using a 50mm lens"), then light ("Soft coastal daylight, shallow depth of field, subtle film grain, natural color balance"), then feel ("honest and unposed"), then exclusions ("No glamorization, no heavy retouching"). The Cookbook says: "prompt the model as if a real photo is being captured in the moment ... Avoid words that imply studio polish or staging."
- **Ads and text** (Thread example): brand, audience and vibe; the tagline in quotes; "Render the tagline exactly once, clearly and legibly, integrated into the ad layout. No extra text, no watermarks, no unrelated logos."
- **Billboard with exact text:** `Billboard text (EXACT, verbatim, no extra characters): "Fresh and clean"`, then `Typography: bold sans-serif, high contrast, centered, clean kerning. Ensure text appears once and is perfectly legible.` The Cookbook adds: "If text fidelity is imperfect, keep the prompt strict and iterate—small wording/layout tweaks usually improve legibility."
- **Logo:** "original, non-infringing logo for a company called X". Describe the brand personality, then "clean, vector-like shapes, a strong silhouette, and balanced negative space. Favor simplicity over detail so it reads clearly at small and large sizes. Flat design, minimal strokes, no gradients unless essential." Use `n` for variations. Use `svg` for editable paths.
- **UI mockup:** "describe the product as if it already exists. Focus on layout, hierarchy, spacing, and real interface elements, and avoid concept art language."
- **Infographic / diagram / slide:** "Productivity visuals work best when the prompt is written like an artifact spec rather than an illustration request. Name the exact deliverable ..., define the canvas and hierarchy, provide the real text or data, and describe the visual language." For accuracy, "list the required components explicitly and say what should not be included." Use `quality="high"` for dense labels. The output may contain invented numbers: "Check each number and any extra percentage the model adds". The transparent-assets Cookbook goes further: "For production reporting where numerical precision is critical, render charts deterministically."
- **Educational:** "Prompt them like an instructional design brief: define the audience, lesson objective, visual format, required labels, and scientific constraints."
- **Comics:** "define the narrative as a sequence of clear visual beats, one per panel." Write "Panel 1: ..." lines.
- **Character consistency:** first make a character reference image with labeled `Character / Theme / Style / Constraints` sections. In later prompts, use that image as input and repeat the defining details under `Character Consistency:` plus "Do not redesign the character".
- **Holiday card and merchandise:** labeled `Scene / Mood / Style / Constraints`, then `Include ONLY this card text (verbatim): "..."`.
- **Historical scenes:** name the place and date ("Bethel, New York on August 16, 1969"). The model infers the context, but check the period details.
- **Looping GIF:** give the subject a start pose to return to; say whether the camera moves.

### A5. Edits, references, transparency [OAI]

- **Edit wording:** start with the change, then the preserve list, then the exclusions. Examples:
  - "In this room photo, replace ONLY the white chairs with chairs made of wood. Preserve camera angle, room lighting, floor shadows, and surrounding objects. Keep all other aspects of the image unchanged."
  - "Translate the text in the infographic to Spanish. Do not change any other aspect of the image." (Then check for words left in the original language.)
  - Identity: "Do not change her face, facial features, skin tone, body shape, pose, or identity in any way ... Replace only the clothing ... Match lighting, shadows, and color temperature ... Do not change the background, camera angle, framing, or image quality, and do not add accessories, text, logos, or watermarks."
  - Sketch to render: "Preserve the exact layout, proportions, and perspective ... Do not add new elements or text."
- **Short follow-ups work** once the base image exists: "Make it look like a winter evening with snowfall."
- **Multi-image:** "Place the dog from the second image into the setting of image 1, right next to the woman, use the same style of lighting, composition and background. Do not change anything else." The Cookbook form is "Image 1: product photo… Image 2: style reference…" and "apply Image 2's style to Image 1". A mask or markup applies only to the **first** image; the other images are references.
- **Pixel-exact regions:** "If part of an image must remain pixel-identical, composite the approved edit into the original." Prompting alone cannot guarantee it.
- **Transparency:** "Request both an isolated subject in the prompt and `background="transparent"` in the API ... A drawn checkerboard is not transparency. For subsequent edits, repeat the requirement to preserve the transparent background." The transparent-assets Cookbook says: "**Prompt instructions take priority over `background="transparent"`.** If the prompt describes a backdrop, scene, color, or other background, the model may generate that background instead." For a transparent chart, ask for transparency "across the entire chart" with "no card, frame, panel, or filled plot area". Standard wording: "Fully transparent background ... single centered [subject] with generous padding, clean alpha edges, and no solid backdrop, scenery, checkerboard, shadow, or watermark."

### A6. Checking and iteration, from OpenAI [OAI]

The 2.6 guide, "Check the result":

- "Can you read every word, and does it match the requested text? Are diagram labels and relationships correct?"
- "Do identities, product shapes, labels, and reference details remain intact?"
- "Did the edit change only what you requested?"
- "If you need transparency, does the decoded file contain transparent pixels?"

The **image-evals Cookbook** turns this into an LLM-as-judge harness:

- "A good vision eval does **not** score 'a pretty picture.'" Hard constraints are "exact text, counts, attributes, locality".
- Structure: **gates** (pass/fail): instruction following, text rendering, locality and preservation. Then **graded** scores (0-5): layout and hierarchy, style fit, realism, artifact severity. Verdict rule: every gate must pass and every graded score must be at least 3. "Do not average scores to override text correctness."
- Judge prompt scope rules (UI and flyer judges): "Judge only against the provided instructions." "Be strict about required copy: spelling, punctuation, casing, and symbols must match exactly." "Extra or missing text is a serious error." "Do NOT reward creativity that violates constraints." "If unsure, score conservatively."
- Failure tags: `wrong_screen_type`, `missing_required_section`, `extra_ui_elements`, `text_unreadable_or_garbled`, `layout_confusing`.
- Visual-quality checks: "No distorted objects, broken hands/cups, melted foam textures, weird artifacts around text."
- Edit metrics: transformation correctness, **non-target invariance** ("No detectable changes outside the requested edits"), and identity and style integrity.
- Next step it suggests: "splitting the single-shot grader prompt into multiple calls to focus on a specific metric."

The Codex `imagegen` skill (workflow steps 12-13): "Inspect outputs and validate: subject, style, composition, text accuracy, and invariants/avoid items. Iterate with a single targeted change, then re-check." Step 17: report the final prompt.

### A7. How existing agent skills structure prompts

| Skill | Template / spec | Enhancement step | Presets / taxonomy | Vision check |
|---|---|---|---|---|
| **OpenAI Codex `imagegen`** [OAI] | Labeled schema: `Use case / Asset type / Primary request / Input images / Scene/backdrop / Subject / Style/medium / Composition/framing / Lighting/mood / Color palette / Materials/textures / Text (verbatim) / Constraints / Avoid` | Yes, with a **specificity policy** (below) | 8 generate slugs + 8 edit slugs, a recipe for each; asset templates (website, game, wireframe, logo) | "Inspect outputs and validate", then single-change iteration |
| **wuyoscar GPT-Image2-Skill** [COMM] | Prose or JSON-like "config" prompts; layout before subject | "Refine only as needed: preserve the brief" | 30+ gallery categories with real prompts | Inspect GIF frames; report one refinement suggestion |
| **smixs visual-skills** [COMM] | 5 slots: `Scene / Subject / Important Details / Use Case / Constraints`; edit form `Change / Preserve / Constraints` | Mandatory reading of the model file before writing | Industry pattern files (ecommerce, fashion, food, poster, character, UI/social) | **Style DNA + Reject Checklist** |
| **glebis gpt-image-2** (Claude Code) [COMM] | "Scene → Subject → Detail → Lighting → Constraint" | Presets merged with the subject; an LLM **preflight check for contradictions** before spending | Style presets (editorial, blueprint, infographic, poster, app-mockup, isometric, ...) and platform sizes | Draft at `low`, then "Show the image to the user using the Read tool", then final at `high` |
| **vargHQ gpt-image-2-6** [COMM] | Rules for text-heavy layouts | n/a | Recipes credited to authors on X | "Read every word in the output before you use it" |
| steipete openai-image-gen [COMM] | Random structured prompt sampler | n/a | n/a | HTML gallery for a human |
| MCP servers [COMM] | None. Thin wrappers; the tool description only gives the 32k max | None | None | None |

**Codex imagegen: prompt augmentation, quoted** ([SKILL.md](https://github.com/openai/skills/blob/main/skills/.system/imagegen/SKILL.md)):

> "Reformat user prompts into a structured, production-oriented spec. Make the user's goal clearer and more actionable, but do not blindly add detail."
>
> "If the prompt is already specific and detailed, preserve that specificity and only normalize/structure it. If the prompt is generic, you may add tasteful augmentation when it will materially improve the result."
>
> Allowed: "composition or framing hints; polish level or intended-use hints; practical layout guidance; reasonable scene concreteness that supports the stated request". Not allowed: "extra characters or objects that are not implied by the request; brand names, slogans, palettes, or narrative beats that are not implied; arbitrary side-specific placement unless the surrounding layout supports it".
>
> "If any critical detail is missing and blocks success, ask a question; otherwise proceed."
>
> Input images: "Do not assume that every provided image is an edit target." Label each one as "reference image", "edit target" or "supporting insert/style/compositing input".

Its sample recipe for `logo-brand` ([sample-prompts.md](https://github.com/openai/skills/blob/main/skills/.system/imagegen/references/sample-prompts.md)):

```text
Use case: logo-brand
Primary request: original logo for "Field & Flour", a local bakery
Style/medium: vector logo mark; flat colors; minimal
Composition/framing: single centered logo on a plain background with generous padding
Constraints: strong silhouette, balanced negative space; original design only; no gradients unless essential; no trademarks; no watermark
```

**wuyoscar craft.md** ([link](https://github.com/wuyoscar/GPT-Image2-Skill/blob/main/skills/gpt-image/references/craft.md)), the useful community rules:

- "Put canvas, aspect ratio, and layout before subject ... Otherwise the model spends detail budget on the object and improvises the layout."
- "Scene density beats adjectives": "include 5–12 concrete nouns for the scene and 2–4 material/lighting constraints. Do not stack empty adjectives".
- "Material, lighting, and palette are separate controls. Do not compress them into 'premium'."
- Posters: state the hierarchy (name largest, then tagline, details, CTA, fine print) and use "Exact readable text:". Add a targeted avoid-line: "avoid unreadable microtext, avoid fake sponsor logos, avoid garbled characters".
- "Pick one dominant capture frame. Too many camera specs can conflict."
- "**Negation is for strong priors** ... Avoid lists should be short and targeted. Too many negatives can dominate the prompt."
- "Real-person likeness edits often fail at the API moderation layer; surface the API error verbatim."

**smixs gpt-image.md** ([link](https://github.com/smixs/visual-skills/blob/main/image/references/gpt-image.md)): 5 slots, and "The fifth slot is where most mediocre prompts fail silently." Banned "slop" words: "stunning, incredible, epic, gorgeous, masterpiece"; replace them with concrete facts ("overcast daylight, brushed aluminum"). Do not write "like an Apple ad"; describe the visual properties instead. For text: "no extra text, no duplicate text, no watermarks". Its golden-rules file also says "Start with a Verb" (Create / Edit / Transform). Its "positive framing" rule ("empty street" rather than "street with no cars") conflicts with OpenAI's own examples, which use "No ..." lines. Our reading: positive descriptions are best for scene content; short "No X" lines are fine for artifacts such as text, watermarks and logos.

**glebis gpt-image-2** ([link](https://github.com/glebis/claude-skills/blob/main/gpt-image-2/SKILL.md)): a Claude Code skill. Useful ideas:

- A **preflight contradiction check**: "a preset that hard-codes something the subject overrides (e.g. the `editorial` preset forces 'on pure black background' while your subject asks for a warm off-white ground)". If a conflict is found, the generation is aborted before money is spent.
- **Draft then final**: generate at `low`, show the image, then make the final at `high`.
- A warning: do not resize a square image to 16:9 afterwards. "pass the API-native size directly".
- For a carousel, put pagination into the prompt and keep one style across the slides.

### A8. Iteration with vision feedback

**Patterns in existing tools:**

- OpenAI's "Check the result" list and the image-evals judge rubrics (A6). [OAI]
- The Codex imagegen loop: inspect, check (subject, style, composition, text, invariants and avoid items), make one targeted change, check again. [OAI]
- smixs **Reject Checklist** ([poster-illustration.md](https://github.com/smixs/visual-skills/blob/main/image/references/patterns/poster-illustration.md)) [COMM]: "Reject and re-prompt naming the specific failure — do not accept and patch." Generic reject items:
  - the style reduced to a decorative border;
  - a generic template look;
  - hero text in unreadable microtext;
  - "The model invented facts — logos, sponsor marks, dates, statistics, quotes, provenance";
  - "A supplied person became a different person";
  - "The mood drifted from the brief (usually darker and more severe than requested, because contrast reads as quality to the model)";
  - texture as a flat overlay.

  Before generating, write a 4-line "Style DNA": core look, material language, structural rule, color direction.
- varg: "Read every word in the output before you use it. Fix one wrong word with a markup edit, not a full regeneration." [COMM]
- glebis: show the draft with the Read tool and ask the user before the final. [COMM]

**Research loops** [RES]:

- **Idea2Img** (Yang et al., Microsoft, ECCV 2024). GPT-4V plays three roles: writing prompts, picking the best draft, and reflecting on feedback against the idea. A memory keeps the prompt, draft and feedback history. A user preference study showed gains across several generators.
- **CRAFT** (arXiv 2512.20362). Turns the prompt into "dependency-structured visual constraints", checks each one with a VLM, edits the prompt "only where constraints fail", and stops on an explicit criterion. Reported gains in composition and text rendering; the largest gains are for lighter generators.
- **Iterative Refinement** (Jaiswal et al., arXiv 2601.15286). Refining step by step with a VLM critic beats compute-matched parallel sampling (best-of-N): +16.9% all-correct on ConceptMix (k=7), +13.8% on T2I-CompBench 3D-spatial. Breaking a complex prompt into sequential corrections gives more faithful images.
- **M3** (arXiv 2602.06166, search snippet only): a checklist builder, a checker and a refiner, with gains reported on counting, spatial relations and text.

**What this means for our loop** [OURS]:

1. Before you generate, turn the request into a short **acceptance checklist**: each quoted string, counts, required elements, placement, style, exclusions and the alpha requirement. This follows CRAFT and the OpenAI gates.
2. After you generate, check each item. Exact text and required elements are pass/fail gates.
3. Choose the fix:
   - **Edit** (pass the output plus one change plus the preserve list) when the composition is right and the error is local, such as one wrong word or one extra object.
   - **Regenerate** with a revised prompt when the layout or concept is wrong.
4. Use at most 2-3 rounds, then show the user the best result with the issues that remain.
5. To check small text, crop or zoom the image before you read it. A downscaled preview hides spelling errors.

### A9. Known failure modes and prompt-level mitigations

| Failure | Evidence | Mitigation |
|---|---|---|
| **Misspelled, duplicated or extra text**; drift in long text | OAI limitation note; Kittl: dense blocks of 100+ words "can introduce occasional letter swaps", heavy-ligature scripts merge [COMM] | Quote every string; keep each string short; state the count ("exactly once"); spell rare words letter by letter; add "no extra text, no duplicate text"; `quality` medium or high; 2.6 `complexity: high` for dense layouts [OAI]. Put long copy outside the image (HTML or a layout tool) [OURS]. Fix one word with a markup or edit call [COMM]. |
| **Invented numbers, labels, logos, sponsors** | OAI slide example: "Check each number and any extra percentage the model adds"; smixs Reject Checklist [COMM] | Give all the data and labels in the prompt; "no other text"; "no logos/trademarks"; render charts in code when precision matters [OAI]. |
| **Imprecise layout or placement** | OAI limitations ("difficulty placing elements precisely") | Name the canvas and layout first ("3:4 vertical poster; top third: title; ..."); use `complexity: high`; use a markup edit for local moves [OAI/COMM]. |
| **Object counts** | Kittl: "Counts above 12 become unreliable" [COMM]; M3 and CRAFT target counting [RES] | State numbers as digits and as items ("exactly three balloons: one red, one blue, one yellow"); keep counts small; check them in the critique step. If wrong, edit: "remove one balloon; keep everything else" [OURS]. |
| **Hands and interlocking fingers** | Kittl: clasped hands "remain a significant challenge" [COMM]; the OAI evals list "broken hands" as an artifact | Describe the hand action exactly ("hands naturally gripping the handlebars") [OAI]; avoid poses with interlocked fingers; crop or frame to hide them; fix with a local edit [OURS]. |
| **"No X" ignored**, or a background described in the prompt beats `transparent` | OAI: "Prompt instructions take priority over background='transparent'" | Do not describe what you want left out. Describe the wanted state positively ("empty plain studio backdrop"). Keep "No ..." lines short and limited to artifacts (text, watermark, logo, checkerboard) [OAI + COMM]. |
| **Drift over chained edits** (face, saturation) | varg measured face similarity: 0.74 to 0.48 (Flare) and 0.73 to 0.29 (Sunburst) over 5 chained edits [COMM] | Repeat the preserve list each turn [OAI]; batch changes into one edit, or edit from the original [COMM]; composite for pixel-exact regions [OAI]; use `complexity: low` for targeted edits [OAI]. |
| **Character inconsistency across images** | OAI limitation | Make a character reference image first, pass it as input, and repeat the defining traits plus "Do not redesign the character" [OAI]. |
| **Too much "AI polish"** on photos | OAI: "Avoid words that imply studio polish"; varg: "pretty doll faces" [COMM] | Use the word "photorealistic" plus capture context ("candid", "35mm film", "iPhone photo"); real texture (pores, wear); "no glamorization, no heavy retouching" [OAI]. |
| **Over-refusal of benign requests** (often at `moderation_stage: output` for photoreal people) | OpenAI forum thread with an OpenAI staff reply [COMM] | Don't retry the same request [OAI]. Read `moderation_stage`. For **input** blocks: remove real names, brands or IP, and violent or sexual-adjacent words; describe what is visible, not intent. For **output** blocks on people: state modest, specific clothing and an innocent context; in one forum case, adding "wearing modern summer clothes, looking happy" let the request pass. If the user agrees, a non-photoreal medium (illustration, 3D) also helps. Use `moderation: "low"` where it is appropriate. After 2 failed rewrites, tell the user instead of looping [COMM/OURS]. |
| **IP and real-person likeness** | wuyoscar: likeness edits "often fail at the API moderation layer" [COMM] | Ask for an "original, non-infringing" design (OAI wording); describe the style properties, not the franchise name. |
| **Visible noise or pattern artifacts** on detailed surfaces | Forum thread; Kittl [COMM] | Lower the detail density; regenerate [COMM]. |
| **Wrong aspect ratio** | glebis: resizing afterwards distorts the image [COMM] | Always set `size` to the target ratio; mention the format in the prompt as well [OAI]. |

### A10. Open questions and conflicts

- **Negatives:** OpenAI uses short "No X" lines; smixs says to use positive framing. Use both, each in its place (Part B).
- **JSON prompts:** OpenAI says the format doesn't matter. wuyoscar likes JSON for complex product renders. Use labeled lines by default; they are easy for Claude to write and to diff between iterations.
- **The gpt-image-1 and 1.5 rules still hold** (same fundamentals). 1.x-only details: `input_fidelity: high` for edits, and only 3 sizes. gpt-image-1 is retired, so this only matters for 1.5 until 2026-12-01.
- **2.6-specific notes** are only about parameters (complexity, markup, SVG, GIF). There are no new wording rules for 2.6.
- Not verified: any `seed` support; whether `complexity` behaves the same on edits as on generations at every level.

---

## Part B. Draft prompt-writing guide (for the skill file)

> Paste-ready text. The tags in brackets show where each rule comes from: **[OAI]** OpenAI docs, **[COMM]** community practice, **[OURS]** our own convention. You can remove the tags in the final skill.

### How to write a GPT Image prompt

**1. Brief before prompt.** From the user's short idea, find: (a) the deliverable and where it will be used, (b) any exact text, (c) the size or ratio, (d) any input images and the role of each one. Ask **one** question only if a missing fact blocks success (for example, the child's name and age on a birthday poster). Otherwise make sensible defaults and tell the user what you assumed. [OAI Codex skill]

**2. How much to add.** If the user gave details, keep them and only restructure them. If the idea is generic, you may add composition, polish level, layout and concrete scene detail. Do **not** add characters, brands, slogans, palettes or story beats that the user did not imply. [OAI Codex skill]

**3. Structure.** Begin with a verb and the deliverable. Then use labeled lines in this order: scene, subject, details, text, constraints. [OAI] Put the canvas or layout first when the structure matters (posters, infographics, grids). [COMM]

**4. Be concrete.** Name the materials, light source, palette, medium and framing. Replace praise words ("stunning, epic, masterpiece, 8K") with visible facts. [OAI + COMM] Keep material, lighting and palette as separate lines. Use one camera or capture frame, not several. [COMM]

**5. Text.** Put every string that must appear in "double quotes". Give its position, its typography (weight, style, color, rough size) and the count ("exactly once"). Spell rare words letter by letter. Keep strings short. Finish with "No other text." For dense text, use quality `high` and, on 2.6, `complexity: high`. [OAI] Put long copy in HTML or a layout tool, not in the image. [OURS]

**6. People and counts.** Give framing ("full body, feet visible"), gaze, and what the hands are doing. [OAI] Write counts as numbers and list the items one by one. Keep them small (about 12 or fewer). [COMM]

**7. Negatives.** Describe the wanted state positively ("plain empty background", "solo portrait"). Keep "No ..." for artifacts only: "No extra text, no watermark, no logos, no checkerboard." Use one short line, not a list of 15 items. [OAI + COMM]

**8. Photorealism.** Use the word "photorealistic" plus how the photo was taken (candid, 35mm, or phone photo; eye level; 50mm), the light, and real texture (pores, wear, grain). Add "No glamorization, no heavy retouching." Treat lens specs as hints for the look, not as physics. [OAI]

**9. Edits.** Write in this order: `Change:` (one thing), `Preserve:` (identity, pose, geometry, layout, lighting, camera angle, text, background), then `Constraints:` (no new elements or text). Repeat the preserve list on every turn. If several fixes are needed, batch them into one edit, or edit from the original rather than chaining many edits. [OAI + COMM] Use `complexity: low` for small edits. For pixel-exact areas, composite the result in code. [OAI]

**10. References.** Give each input a number and a role: "Image 1: edit target (the room). Image 2: style reference (palette and brushwork only)." Then say what moves where. Masks and markup apply only to Image 1. [OAI]

**11. Transparent assets.** Set `background: "transparent"` with PNG or WebP. In the prompt, describe only the isolated subject: "isolated on a fully transparent background, centered, generous padding, clean alpha edges; no backdrop, scenery, shadow, or checkerboard." Do not describe any background, because the prompt overrides the parameter. Check the alpha channel in the file. [OAI]

**12. Parameters, not prose.** Put the ratio in `size` (both sides multiples of 16, ratio from 1:3 to 3:1). Use `quality: low` for drafts and `medium` or `high` for finals. Use Flare for speed and Sunburst for dense layouts and precise edits. [OAI]

### Reusable template

```text
Create a <deliverable> for <use/audience>. <Canvas/format, e.g. "Vertical 2:3 poster">.
Scene: <environment, background, time of day>
Subject: <main subject; exact count; pose/action; gaze/hands>
Style: <medium + 2-3 concrete style facts>
Composition: <framing, viewpoint, placement, negative space>
Lighting & palette: <light source/quality>; <3-4 colors>
Details: <materials, textures, 5-10 concrete nouns>
Text (verbatim, each exactly once): "<STRING 1>" — <position, typography>; "<STRING 2>" — <...>
Constraints: <must keep / must include>. No other text, no watermark, no logos.
```

Edit form:

```text
Edit Image 1. Change only: <one concrete change>.
Preserve exactly: <identity/face, pose, geometry, layout, lighting, camera angle, existing text, background>.
<Image 2: role — what to take from it.>
Do not add new objects, text, logos, or watermarks.
```

### Critique loop (after every generation) [OAI evals + RES, adapted]

1. Before you call the API, write a checklist from the brief: each quoted string, counts, required elements, placement, style, exclusions, alpha.
2. Look at the image. Crop or zoom to read small text. Mark each item PASS or FAIL. Exact text and required elements are hard gates. Do not let a pretty image hide a wrong word.
3. Also look for: invented text, logos or numbers; extra or missing objects; broken hands or faces; changes outside the edit area; style or mood drift.
4. Fix only what failed:
   - If the composition is right, **edit** (one change plus the preserve list).
   - If the layout or concept is wrong, **regenerate** with a revised prompt (change the failing line, keep the others).
5. Stop after 2-3 rounds. Show the best image and state any issues that remain. Report the final prompt and settings.
6. If you get `moderation_blocked`: don't resend the same request. Check `moderation_stage`.
   - `input`: remove names, brands or IP and loaded words; describe the visible content.
   - `output` (often photoreal people): add specific, modest clothing and a benign context, or, with the user's consent, use an illustrated medium.
   - After 2 attempts, explain the block to the user.

### Recipes

**Poster or invitation (e.g. a kid's birthday)** — size `1024x1536`, quality `high`

```text
Create a printable vertical 2:3 birthday party poster for a 6-year-old.
Layout: top third headline; center hero illustration; bottom band with party details.
Subject: a friendly cartoon dinosaur wearing a party hat, holding exactly 6 balloons (red, yellow, blue, green, orange, purple).
Style: flat vector children's illustration, rounded shapes, thick soft outlines, cheerful.
Palette: sunny yellow background, teal, coral, white accents.
Text (verbatim, each exactly once): "MIA IS 6!" — top, large bold rounded sans-serif, white with coral outline;
"Saturday, May 9 · 3 PM" and "12 Oak Street" — bottom band, medium clean sans-serif, dark teal.
Constraints: high contrast, legible from a distance. No other text, no watermark, no logos.
```

**App icon** — size `1024x1024`, quality `high` [COMM/OURS: OpenAI has no icon recipe; the rules come from the logo recipe]

```text
Create an app icon for a habit-tracking app called "Streak".
Subject: a single bold check-mark merged with a rising flame, centered, filling about 70% of the square.
Style: modern flat icon, simple geometric shapes, subtle two-tone gradient, strong silhouette that reads at 32 px.
Background: solid deep indigo filling the whole square edge to edge (the OS applies the rounded mask).
Constraints: one symbol only, no text or letters, no border, no drop shadow outside the shape, no watermark.
```

**Logo (transparent)** — `background: transparent`, PNG (or `output_format: svg`), `n: 3-4` [OAI]

```text
Create an original, non-infringing logo for "Field & Flour", a local bakery.
Feel: warm, simple, timeless. Mark: a wheat stalk forming the letter F beside the wordmark.
Style: clean vector-like shapes, strong silhouette, balanced negative space, flat colors (wheat gold, charcoal), minimal strokes, no gradients.
Text (verbatim, once): "Field & Flour" in a friendly serif.
Fully transparent background: single centered logo, generous padding, clean alpha edges; no backdrop, scenery, checkerboard, shadow, or watermark.
```

**Product shot** — size `1536x1024`, quality `high`

```text
Create a photorealistic e-commerce hero photo of a matte sage-green ceramic coffee mug.
Scene: light oak table, plain warm off-white wall, empty right third for page copy.
Subject: one mug at a slight three-quarter angle, steam rising, a folded linen napkin beside it.
Lighting: soft window light from the left, gentle contact shadow, natural color balance.
Details: visible glaze speckles, fine ceramic texture, crisp rim highlight; shot at eye level, 85mm look, shallow depth of field.
Constraints: no text, no logos, no watermark, no other props.
```

**Infographic or diagram** — size `1536x1024` (landscape) or `1024x1536`, quality `high`, 2.6 `complexity: high` [OAI]

```text
Create a clean educational infographic titled "How Rain Forms" for 10-year-olds.
Layout: left-to-right flow of 4 numbered stages connected by arrows; title across the top; white background.
Stages and labels (verbatim): "1 Evaporation", "2 Condensation", "3 Clouds", "4 Precipitation".
Style: flat vector icons, consistent stroke width, blue/teal palette with one warm accent, generous white space.
Constraints: labels large and readable; only the title and these labels; no extra text, no decorative clutter, no logos.
```

**Photo edit** — the edit endpoint with Image 1; 2.6 `complexity: low`; add markup for local edits [OAI]

```text
Edit Image 1 (the family photo). Change only: replace the overcast sky with a clear late-afternoon sky with a few soft clouds.
Preserve exactly: every person's face, identity, expression, pose and clothing; the house, trees and lawn; camera angle and framing.
Match the new light gently on the scene (warm, low sun from the left) without changing skin tones.
Do not add new objects, people, text, or watermarks.
```

UI mockups, if needed later [OAI]: "Create a realistic <platform> UI mockup for <product>... describe it as if it already exists"; list the exact labels in quotes; "no placeholder or lorem ipsum text"; quality `high`.
