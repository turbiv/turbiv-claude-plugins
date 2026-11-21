# Existing open-source tools: AI coding agent → OpenAI image API

Survey date: 2026-11-21. Input for the planned Claude Code plugin `openai-images`.
Method: `gh search repos` / `gh search code`, the official MCP registry, claudemarketplaces.com and claudepluginhub.com listings, then shallow clones. I read the source of every project below. Star counts and "last push" dates come from the GitHub API on the survey date.

Model names used in these repos (as of Nov 2026): `gpt-image-1`, `gpt-image-1-mini`, `gpt-image-1.5`, `gpt-image-2` (released 2026-04-21), `gpt-image-2.5-flare|sunburst`, `gpt-image-2.6-flare|sunburst` (the 2.6 models add animated GIF and SVG output, a `complexity` knob and `xhigh`/`max` quality). Several repos say DALL·E was shut down on 2026-05-12. These are the repos' own claims. Check API facts against `openai_api.md`.

Prompt-construction detail is deliberately left out here (see `prompt_construction.md`). I only record whether a project has a prompt template or enhancement step.

---

## 1. OpenAI `imagegen` system skill (Codex)

- **URL:** https://github.com/openai/codex/tree/main/codex-rs/skills/src/assets/samples/imagegen (the copy that ships inside Codex, last commit 2026-09-01). The older standalone copy is at https://github.com/openai/skills/tree/main/skills/.system/imagegen. That repo is now marked deprecated, and its copy is stale: it still defaults to `gpt-image-1.5` (issues #538 and #363).
- **Stars:** openai/codex has 136k; openai/skills has 28.9k.
- **Type:** Agent Skill (SKILL.md + Python CLI `scripts/image_gen.py` + `scripts/remove_chroma_key.py`).
- **Two modes:**
  - **Built-in mode (default):** uses the Codex built-in `image_gen` tool, which runs on the ChatGPT login and needs no key.
  - **CLI fallback ("explicit-only"):** uses the Images API with `OPENAI_API_KEY`. The skill tells the agent: "Never switch to CLI fallback automatically" and "Never modify `scripts/image_gen.py`… Do not create one-off SDK runners."
- **How it calls OpenAI:** the CLI uses the Images API through the `openai` SDK: `images.generate` and `images.edit`, plus `AsyncOpenAI` for batches.
  - Codex copy defaults: `gpt-image-2`, `size=auto`, `quality=medium`, `png`.
  - Deprecated copy defaults: `gpt-image-1.5`, 1024x1024, `auto`.
  - Exposed flags: `--model --prompt/--prompt-file --n(1–10) --size --quality --background --output-format --output-compression --moderation --out/--out-dir --force --dry-run --input-fidelity --mask --image (repeatable)`.
  - Size validation per model: for gpt-image-2, sides must be multiples of 16, max edge 3840, ratio at most 3:1, and 655,360 to 8,294,400 pixels.
  - Option checks per model: `background=transparent` and `input_fidelity` are rejected on gpt-image-2 with a hint to use 1.5.
  - Model must start with `gpt-image-`.
- **API key:** env `OPENAI_API_KEY` only. The skill says: "Never ask the user to paste the full key in chat." Open issue #520 asks it to use the host's secure key flow instead of inline `export` instructions.
- **Outputs:**
  - CLI: `output/imagegen/output.png` by default. Temp JSONL goes to `tmp/imagegen/`.
  - Naming: `-1`, `-2` suffixes for n>1; batches are `NNN-<slug>.png`.
  - Never overwrites without `--force`.
  - `--downscale-max-dim` writes a `-web` copy for websites.
  - Built-in mode saves under `$CODEX_HOME/generated_images/…`. The skill must copy project-bound assets into the workspace and use versioned sibling names such as `hero-v2.png` instead of overwriting.
  - The image is shown back to the agent through Codex's `view_image`. The skill tells the agent to inspect and validate the output, then iterate with "a single targeted change".
- **Edit / refs / mask / transparency / batch:**
  - Edits take up to 16 images.
  - `--mask` and `--input-fidelity` are supported.
  - `generate-batch` takes JSONL (max 500 jobs), with `--concurrency` 1–25 (default 5), `--max-attempts` and `--fail-fast`.
  - Transparency: the earlier version had a chroma-key workflow (generate on a flat key colour, then `remove_chroma_key.py`). Commit #37788 (Aug 2026) switched to asking the built-in tool for real alpha.
- **Cost / budget:** none.
- **Errors:**
  - Batch retries rate limits and transient errors with exponential backoff, capped at 60 s, and honours `retry-after` when it is present. Errors are detected by class name and message text.
  - No special handling for moderation.
- **Clever:**
  - `--augment` (on by default) builds a labelled spec from flags such as `--use-case --scene --subject --style --composition --lighting --palette --materials --text --constraints --negative`. That is a deterministic prompt template inside the CLI: `_augment_prompt_fields` in `scripts/image_gen.py`.
  - A use-case taxonomy with fixed slugs in SKILL.md.
  - `references/codex-network.md` explains sandbox network approval.
  - `--dry-run` prints the payload without calling the API.
- **Prompt guidance files:** `SKILL.md` (shared prompt schema), `references/prompting.md`, `references/sample-prompts.md`.

## 2. wuyoscar/GPT-Image2-Skill

- **URL:** https://github.com/wuyoscar/GPT-Image2-Skill
- **Stars / last push:** 6,166 · 2026-11-08 (MIT).
- **Type:** Claude Code plugin + Codex plugin manifest (`.claude-plugin/`, `.codex-plugin/`, `.agents/plugins/`) with two skills (`gpt-image`, `get-prompt-from-image`). It also ships a Python CLI on PyPI/uvx (`gpt-image`).
- **Language:** Python 3.11+, packaged as a PEP 723 `uv run` script.
- **How it calls OpenAI:** Images API through the SDK. The call goes to `images.generate`, or to `images.edit` when any `-i` is given.
  - Defaults: `gpt-image-2.6-flare`, 1024x1024, `quality=high`, `moderation=low` (explicitly set lower than the API default).
  - Size shortcuts: `1k 2k 4k portrait landscape square wide tall`.
  - GIF via `--format gif --frames --frame-duration`, sent through `extra_body` because the SDK types lag behind the API.
  - Flags drop `input_fidelity` for gpt-image-2 and block `xhigh`/`max` quality unless the model is 2.5/2.6.
- **API key:** process env, then `./.env`, then `~/.env`, loaded with `override=False`.
  - Issue #12 shows the risk: an expired project or home `.env` key silently overrode the Codex subscription path. The workaround was `unset OPENAI_API_KEY`. The SKILL.md now tells agents to respect that.
- **Outputs:**
  - Default path: `./fig/` if that folder exists, otherwise cwd.
  - Naming: `YYYY-MM-DD-HH-MM-SS-<slug30>.<ext>`; n>1 gives `_0`, `_1`.
  - It overwrites existing files (no check).
  - It prints paths to stdout. Nothing is returned inline; the skill says "Report: output file path(s)".
- **Edit / refs / mask / transparency / batch:**
  - Repeatable `-i`, `-m` alpha mask, `--background transparent` (requires png/webp), `-n` up to 10.
  - Local `gpt-image animate` slices a sprite sheet into a GIF with no API call.
- **Cost / budget:**
  - No metering.
  - Policy rules in SKILL.md: generate one image unless more were asked for; "ask before additional paid variants"; discuss cost before raising quality.
  - `OpenAI(max_retries=0)` with the comment "No hidden retries of potentially billable generation requests."
- **Errors:**
  - Every `APIError` is printed and exits 1. Exit codes: 0 ok, 1 API error or refusal, 2 bad args or missing key.
  - The skill tells the agent: on invalid-model, 403, quota or policy failures, "report the failure and stop; do not switch models or rewrite the prompt to retry automatically."
  - `docs/image-2.6-samples.md` records a real refusal: 400 `moderation_blocked` at stage `output`.
- **Complaints:**
  - #33: the hard-coded `--format` choices rejected `svg`/`gif` when 2.6 shipped. Hard-coded enums go stale.
  - #12: key precedence, and the agent sometimes writing its own `openai` Python code when the skill did not trigger.
- **Prompt templates:** a large prompt gallery under `skills/gpt-image/references/` (`gallery*.md`, `craft.md`, `templates-gpt-image-2.5.md`) with per-model "load one slice" rules.

## 3. ConardLi/garden-skills — `gpt-image-2` skill

- **URL:** https://github.com/ConardLi/garden-skills/tree/main/skills/gpt-image-2
- **Stars / last push:** 15,556 (whole skills collection) · 2026-11-19 (MIT).
- **Type:** Agent Skill with Node scripts (`generate.js`, `edit.js`, `shared.js`, `check-mode.js`). Plain `fetch`, no SDK.
- **Three modes, chosen by `check-mode.js`:**
  - **A:** local API calls. Needs `ENABLE_GARDEN_IMAGEGEN=1` and a key.
  - **B:** "host-native". The skill becomes prompt guidance and hands the prompt to the host's own image tool (it looks for tools named like `image_generation`, `mcp__*image*`).
  - **C:** "advisor". It only writes the prompt to a file.
- **How it calls OpenAI:** REST `POST /images/generations` (JSON) and `/images/edits` (multipart).
  - Default model `gpt-image-2` (env `OPENAI_IMAGE_MODEL`). Only flags you pass are sent: `size n quality background moderation output_format output_compression`; edit also takes `mask` and `input_fidelity`.
  - `OPENAI_BASE_URL` lets you use third-party gateways.
- **API key:** CLI arg, then env, then `./.env`, then `./.gateway.env`, then `~/.gateway.env`.
- **Outputs:**
  - Images go to `garden-gpt-image-2/image/<slug>-<YYYYMMDD-HHMMSS>.png`.
  - The final prompt is always saved to `garden-gpt-image-2/prompt/<slug>-<ts>.md` as well, which makes every result reproducible.
  - It prints the path. Nothing is returned inline.
- **Bugs / mistakes:**
  - `extractGeneratedBytes` reads only `data[0]`, so `n>1` silently drops images.
  - `--json` prints the whole `apiResponse`, base64 included. That can put megabytes into the agent's context.
- **Edit / refs / mask / transparency / batch:** edit with mask is supported. No batch. There is a transparency flag but no checks.
- **Cost / budget / errors:** none. Errors are thrown as `Image API error (<status>): <body>`, with no retry and no moderation-specific text.
- **Prompt templates:** 80+ structured templates in 18 categories under `references/` (for example `references/ui-mockups/*.md`). This is the main value of the repo.

## 4. shinpr/mcp-image

- **URL:** https://github.com/shinpr/mcp-image (npm `mcp-image`)
- **Stars / last push:** 195 · 2026-11-13 (MIT).
- **Type:** MCP server (TypeScript, Node 22+). Providers: Gemini (default), OpenAI, BytePlus Seedream.
- **How it calls OpenAI:** Images API through the SDK (`openai/src/api/openaiImageClient.ts`).
  - The quality preset also picks the model: `fast` gives 2.6-flare at `low`; `balanced` gives flare at `high`; `quality` gives 2.6-sunburst at `max`.
  - Size is computed from aspect ratio plus 1K/2K/4K and snapped to 16 px multiples inside the pixel cap.
  - `n` is fixed at 1.
  - Edits go through `toFile` from base64 inputs.
- **Prompt enhancement:**
  - A text model rewrites the prompt before every generation. For OpenAI that is `gpt-5.6-luna` (`src/api/openaiTextClient.ts`; logic in `src/business/structuredPromptGenerator.ts`). Text meant to appear in the image is kept verbatim.
  - `SKIP_PROMPT_ENHANCEMENT=true` turns it off. The README shows enhanced-vs-plain comparisons.
- **API key:** env `OPENAI_API_KEY`, with `IMAGE_PROVIDER=openai`.
- **Outputs:**
  - Saved to `IMAGE_OUTPUT_DIR` as `image-<epochms>-<randomhex>.<ext>`.
  - Returns a text block containing JSON `{type:'resource', resource:{uri:file://…}}` plus metadata (model, timing). No inline pixels.
  - It checks that the returned bytes match the requested MIME type.
- **Cost / budget:** none.
- **Errors:**
  - Keyword matching on the message (`quota`/`rate limit`, `unauthorized`, `model`/`not found` (which points to org verification), `forbidden`).
  - Structured `{code, message, suggestion, details}` with an allowlist of context keys, so prompts are never echoed back. Messages are redacted by the logger.
- **Clever:** the safe-context allowlist on errors; MIME sniffing; clean `Result<>` types.

## 5. SureScaleAI/openai-gpt-image-mcp

- **URL:** https://github.com/SureScaleAI/openai-gpt-image-mcp
- **Stars / last push:** 119 · 2025-05-31 (stale, MIT). The early reference that many forks copy.
- **Type:** MCP server (TypeScript, single file `src/index.ts`). Tools: `create-image`, `edit-image`.
- **How it calls OpenAI:**
  - Images API. `model` is pinned by the schema to the literal `gpt-image-1`.
  - The Zod schema mirrors the API: `prompt(≤32000) background moderation n(1–10) output_compression output_format quality size user`.
  - Uses `AzureOpenAI` if `AZURE_OPENAI_API_KEY` is set.
- **API key:** env, or `--env-file <path>`.
- **Outputs:**
  - Default `output: "base64"` returns MCP `image` content blocks, so the agent sees the image.
  - If the total base64 exceeds 1 MB, it switches to writing a file at `$MCP_HF_WORK_DIR` or `/tmp/openai_image_<ms>.<ext>` and returns `Image saved to: file://…`.
  - `file_output` must be an absolute path. Issue #1: this broke on Windows.
- **Edit:** image and mask accept an absolute path or base64. n>1 is supported. No batch, cost tracking or retry. Errors are thrown as-is.
- **Note:** this is where the "inline unless too big, then file" pattern comes from.

## 6. guinacio/claude-image-gen ("media-pipeline")

- **URL:** https://github.com/guinacio/claude-image-gen
- **Stars / last push:** 83 · 2026-11-08 (MIT).
- **Type:** Claude Code plugin (`.claude-plugin/` + `.mcp.json` + `skills/image-generation/SKILL.md`) that bundles an MCP server (`mcp-server/build/bundle.js`). Also an **MCPB bundle** (`mcp-server/manifest.json`, `media-pipeline.mcpb`) for Claude Desktop, plus a standalone CLI. Providers: Gemini (default) and OpenAI.
- **How it calls OpenAI:** Images API through the SDK (`mcp-server/src/openai-client.ts`). One tool, `create_asset`.
  - Model routing: any name matching `gpt-image*` goes to OpenAI. Default `OPENAI_DEFAULT_MODEL=gpt-image-2`.
  - Aspect ratio maps to the 3 standard sizes and returns a **warning** when the mapping is inexact. An explicit `size` overrides this.
  - Supports `background`, `outputFormat` (including gif and svg on 2.6, with `frameCount`, `frameDurationMs`, `svgModel`, `svgReasoningEffort`), mask and reference images.
  - Lists available models at runtime with `models.list()`, filtered by `/^gpt-image/`.
- **API key:**
  - Plugin: `.mcp.json` passes `${OPENAI_API_KEY}` from the shell env.
  - MCPB: `user_config.OPENAI_API_KEY` with `sensitive: true`.
- **Outputs:**
  - `IMAGE_OUTPUT_DIR` (default `./generated-images`), files named `generated-<uuid>.<ext>`.
  - Custom paths are kept inside the output directory with a realpath check.
  - Returns a JSON text summary plus an MCP `resource_link`. No inline image.
- **Clever:**
  - A transparent background with no format picks PNG automatically; transparent + JPEG is rejected locally.
  - Invalid combinations (mask without a base image, frame options without gif, svg with refs) are rejected before any paid call.
  - `OBSERVED_MODEL_REJECTIONS`: a deliberately small list of rejections actually seen from the API ("gpt-image-2 + transparent → 400"), used instead of a full capability matrix "that goes stale the moment a model ships". Unknown combinations go through to the API, and 4xx text is passed back verbatim.
- **Errors:** 4xx messages pass through; 5xx and transport errors get a generic message. No retry and no moderation-specific text.
- **Complaints:**
  - #3: reference-image hardening only checks the file extension, so arbitrary local files could be uploaded to a third-party API.
  - #4: "requires too much permissions".
  - #7: the mask check reads magic bytes but not the alpha channel.
  - #16: the CLI ignores `IMAGE_OUTPUT_DIR`.
  - #28: docs still mention dall-e.
  - #21: dependency audit (old MCP SDK).

## 7. lansespirit/image-gen-mcp

- **URL:** https://github.com/lansespirit/image-gen-mcp
- **Stars / last push:** 69 · 2026-04-25.
- **Type:** MCP server (Python, FastMCP). OpenAI + Gemini/Imagen. Stdio or HTTP transport.
- **How it calls OpenAI:**
  - Images API. Default model `gpt-image-2`.
  - A per-model capability registry checks sizes, including custom-size limits for gpt-image-2. An unsupported size falls back to `auto` with a log message.
  - Exposes `quality size style moderation output_format compression background`.
- **API key:** env vars and pydantic settings (`config/settings.py`).
- **Outputs:**
  - `./storage/images/<task_id>.<fmt>`, where task_id is `YYYYMMDDHHMMSS` plus a uuid fragment.
  - A **JSON metadata sidecar** goes to `storage/metadata/<id>.json`.
  - Retention cleanup after 30 days.
  - Returns a `generated-images://<id>` MCP resource URI plus a file:// or HTTP URL, not base64 ("Build image URL instead of base64 data").
- **Cost:** `estimate_cost()` with per-model token prices and per-quality token counts for gpt-image-2 (low 170, medium 1370, high 5500 tokens at 1024²). The size scaling is sub-linear and the code calls it "ROUGH". Estimates are returned with each result and in the model list.
- **Clever:**
  - An **in-memory TTL cache** keyed on all parameters: an identical repeat request returns the earlier result without a paid call.
  - MCP prompt templates (`resources/prompt_templates.py`, `prompts/template_manager.py`).
- **Errors:** generic `ProviderError`. No retry and no moderation mapping.

## 8. Subscription bridges (no Images API): KingGyuSuh/codex-image-in-cc and GENEXIS-AI/gpt-image-skill

- **URLs:** https://github.com/KingGyuSuh/codex-image-in-cc (52 stars · 2026-09-12, Apache-2.0); https://github.com/GENEXIS-AI/gpt-image-skill (192 stars · 2026-08-28).
- **Type:**
  - codex-image-in-cc is a Claude Code plugin with user-invoked skills `/codex-image:generate|edit|status` that shell out to `node scripts/codex-image.mjs`, which runs `codex exec --sandbox workspace-write`.
  - GENEXIS is a cross-agent skill that also drives the Codex built-in `$imagegen`.
- **How it calls OpenAI:** it doesn't. A whole Codex agent turn runs the built-in `image_gen` tool, billed to the ChatGPT plan.
  - Size, quality and count are given in natural language inside the prompt.
  - codex-image-in-cc picks the orchestrator model from a preference ladder after probing `codex debug models`. It can be overridden with `CODEX_IMAGE_MODEL` + `CODEX_IMAGE_EFFORT`, and setting only one is an error.
- **Outputs:**
  - codex-image-in-cc: `./codex-images/<UTC-timestamp>-<n>.png`; Codex prints one `SAVED: <abs path>` line per image.
  - GENEXIS: `<project>/generated-images/*.png`.
- **Refs:** `--ref` (max 5) is attached through `codex exec --image`.
- **Cost:** subscription quota. GENEXIS says plainly that image turns burn included limits "3–5× faster on average".
- **Complaints:** CLI drift. #5: Codex 0.151 removed `--full-auto` and every dispatch failed. #9: Windows `codex.exe` not found. The skill asks for a 10-minute Bash timeout because a turn takes 1–3 minutes.
- **Relevance:** a competing route for users with a ChatGPT plan but no API budget. It is out of scope for an API-key plugin, but worth a mention in the README.

## 9. Borys520/gpt-image-2-mcp

- **URL:** https://github.com/Borys520/gpt-image-2-mcp
- **Stars / last push:** 14 · 2026-09-07 (MIT).
- **Type:** MCP server (TypeScript, `openai` v7). Six tools: `generate_image`, `edit_image`, `start_edit_session`, `continue_edit_session`, `end_edit_session`, `list_edit_sessions`.
- **How it calls OpenAI:**
  - The Images API is the primary path.
  - Fallback: if `/v1/images/edits` returns the launch-era 400 "Value must be 'dall-e-2'", edits are routed through the **Responses API `image_generation` tool** (host model `OPENAI_RESPONSES_EDIT_MODEL`, default `gpt-4.1-mini`). The direct endpoint is probed again after 10 minutes, and `OPENAI_FORCE_RESPONSES_EDITS=1` pins the fallback. See `src/utils/edit-via-responses.ts`.
  - Defaults: size `auto`, quality `auto`. Custom sizes are validated.
- **API key:** env `OPENAI_API_KEY`, plus `OPENAI_BASE_URL`, `OPENAI_ORG_ID` and `OPENAI_PROJECT_ID`.
- **Outputs:**
  - Default folder: `~/.config/gpt-image-2-mcp/output/<project>-<hash>/`, derived from the git root or cwd so projects don't collide. It can be overridden per call or with an env var.
  - Names: `image-YYYYMMDD-HHMMSS-<rand6>[-prefix].png`.
  - The result contains an **inline `ImageContent` block per image** (so the model sees it), a text summary, and `structuredContent` with `requested` vs `applied` settings, paths, `usage` and `cost_usd_estimated`.
  - Images above 2560×1440 get a note that they are "experimental".
- **Sessions:** multi-turn edits keep history in memory. Each output becomes the next input. Up to 20 sessions with LRU eviction and a 1-hour TTL.
- **Cost:** estimated from the API's `usage`. Fallback-route results are marked as undercounted.
- **Complaints:** #1 security report lists 11 findings: SSRF (`images` and `mask` accept URLs) and path traversal (arbitrary file read and write). Lesson: never fetch arbitrary URLs, and confine reads and writes to allowed folders.

## 10. Sunghwan0112/spritecast

- **URL:** https://github.com/Sunghwan0112/spritecast
- **Stars / last push:** 371 · 2026-11-20 (MIT).
- **Type:** Claude Code plugin (domain-specific: game sprites) with Python skill scripts and a SessionStart hook.
- **How it calls OpenAI:**
  - Raw `urllib` multipart POST to `/v1/images/edits`, because it always conditions on a rendered 3D guide image.
  - Model from `SPRITECAST_MODEL` (default `gpt-image-2.5-sunburst`); quality from `SPRITECAST_QUALITY` (default `high`).
  - Always `background=opaque`, then its own cutout step. `n=1`.
- **API key:**
  - `plugin.json` `userConfig.openai_api_key` with `sensitive: true`. The description field shows the expected cost ("about $0.07 a prop, $2.2 a walking character").
  - A SessionStart hook (`hooks/keys.sh`) writes `export OPENAI_API_KEY='…'` from `$CLAUDE_PLUGIN_OPTION_OPENAI_API_KEY` into `$CLAUDE_ENV_FILE`, so the Bash-run scripts receive it. A userConfig key wins over the env key.
- **Outputs:** per-spec project folders (`out/sheet.png`, GIF previews). The skill tells Claude to show the results.
- **Cost / budget:** the **best spend gate found**.
  - Every paid subcommand first prints the model, quality and an **estimated USD cost**, then exits without spending.
  - It spends only when re-run with `--yes`. SKILL.md: "Tell the user the cost and wait for a yes before running it with `--yes`."
  - After each call it prints the actual cost from `usage` (`PRICE` table in `skills/spritecast/scripts/isoprop.py`).
  - Redraws are capped ("Stop after a sheet's second try and show the result").
- **Errors:** retries 429/5xx up to 3 times with 15 s linear backoff. Other HTTP errors exit with the body.
- **Takeaway:** userConfig + SessionStart hook is the working way to give a userConfig secret to *skill scripts* (as opposed to an MCP server). The cost: the key sits in the session env file and is exported to every Bash command.

## 11. nicknisi/claude-plugins — `image-gen`

- **URL:** https://github.com/nicknisi/claude-plugins/tree/main/plugins/image-gen
- **Stars / last push:** 114 (marketplace repo) · 2026-08-11.
- **Type:** Claude Code plugin with a skill and a pre-bundled Node script (`skills/image-gen/dist/generate_image.js`, built from `scripts/generate_image.ts`), so no npm install is needed at runtime.
- **How it calls OpenAI:**
  - SDK `images.generate` / `images.edit` with `gpt-image-2`.
  - `--resolution 1K|2K|4K` maps to sizes; `--size` overrides; `--quality` default `auto`.
  - OpenAI takes only one `--input-image`. `--mask` is OpenAI-only and requires an input image.
- **API key:**
  - `OPENAI_API_KEY` env or `--api-key`. Passing the key as a flag leaks it into shell history and the transcript.
  - If only the OpenAI key is set, the provider is chosen automatically.
- **Outputs:**
  - `--filename` is required.
  - Naming convention in SKILL.md: `YYYY-MM-DD-HH-MM-SS-descriptive-name.png`.
  - SKILL.md says: "Report that path to the user; **do not read the image back**". This is a deliberate choice to save tokens, the opposite of Borys520.
- **Cost / errors / retry:** none.
- **Clever:** a short provider-choice rule: use OpenAI when text rendering or inpainting matters.

## 12. strato-space/media-gen-mcp

- **URL:** https://github.com/strato-space/media-gen-mcp
- **Stars / last push:** 9 · 2026-01-30 (MIT).
- **Type:** MCP server (strict TypeScript, Vitest/ESLint CI). Images + Sora + Veo.
- **How it calls OpenAI:** Images API with the full parameter set for `gpt-image-1.5`/`gpt-image-1`. Edits take 1–16 images. Azure is supported.
- **API key:** env / `.env` (`.env.sample`).
- **Outputs:**
  - `MEDIA_GEN_DIRS` allowlist with glob roots (default `/tmp/media-gen-mcp`). Every input and output path must be inside it.
  - `MEDIA_GEN_URLS` URL-prefix allowlist for remote inputs.
  - Names: `output_<time_t>_media-gen__<tool>_<uuid>.<ext>`.
  - The result shape can be chosen per call: `tool_result` = `resource_link` | `image`, and `response_format`; it can also place output in `content`, `structuredContent` or top-level.
  - Switches from inline to file automatically above a size limit.
  - **Recompresses with sharp** to fit MCP payload limits.
  - A `test-images` tool lets you debug how a client renders results without paying.
- **Cost:** `estimateGptImageCost()` uses the API's `usage` (text, image and cached tokens), see `src/lib/pricing.ts`.
- **Errors:** every failure returns `isError: true` with text. No retry policy found.

## 13. HarinJin/kez-gpt-image-mcp

- **URL:** https://github.com/HarinJin/kez-gpt-image-mcp
- **Stars / last push:** 4 · 2026-07-20.
- **Type:** remote MCP server on a Cloudflare Worker for claude.ai (web, desktop, phone). Uses R2 storage, Durable Objects and OAuth (PKCE) with a passcode gate.
- **How it calls OpenAI:**
  - REST to the Images API. Models allowlist: `gpt-image-2` (default), `gpt-image-1.5`, `gpt-image-1`. Quality default `medium` ("draft=low, final=high"). Default size 1024x1536.
  - Skips `input_fidelity` on gpt-image-2 because "unsupported (400), measured live 2026-06-12".
  - Can route calls through a US-east Durable Object to avoid regional 403s.
- **Outputs:** an MCP Apps **chat widget** showing image, cost ($), resolution, model snapshot, tokens and the full prompt, with lightbox and ZIP download. References are uploaded through a drag-and-drop widget, so the image bytes never pass through the LLM and cost no tokens.
- **Batch:**
  - `generate_batch` queues jobs; `check_jobs` collects them.
  - Paced at 5 images per minute ("OpenAI Tier 1 image limit"), 12 s apart.
  - Retry backoff 30 s, 1 m, 2 m, 4 m; 10-minute timeout.
- **Errors:** `mapOpenAIError` (src/index.ts around line 296) separates:
  - 400 moderation (`code` includes `moderation`, or the message mentions safety/content policy), with the advice "soften real-person/violence/sexual wording and retry";
  - 401 bad key;
  - 402 / `insufficient_quota` / billing: "budget exhausted, raise the cap or wait";
  - 429 rate limit.
  - There are tests for `moderation_blocked` and `429 insufficient_quota`.
  - **Mistake:** the batch worker retries *every* error up to MAX_ATTEMPTS, including moderation and quota errors.
- **Cost:** `estimateCost(model, usage)` uses a price table. An unknown model falls back to the `gpt-image-1` price as a conservative estimate.

## 14. kpkhxlgy0/claude-openai-gpt-image (plugin `gpt-image`)

- **URL:** https://github.com/kpkhxlgy0/claude-openai-gpt-image
- **Stars / last push:** 0 · 2026-11-12 (MIT). Not popular, but the **closest design analogue** to what we plan: a Claude Code plugin with userConfig and a bundled local MCP server.
- **Type:** Claude Code plugin with `.mcp.json`, a prebuilt `dist/server.mjs` (no npm at runtime), `/gpt-image:setup`, and tools `get_status`, `generate_image`, `edit_image`.
- **How it calls OpenAI:**
  - Images API. Default `gpt-image-2.6-flare`, quality `high` (the README warns that this costs more than `auto`), 1024x1024.
  - `n` is **fixed at 1**: "one validated image per paid call".
  - 2.6-only options (`gif`, `svg`, `complexity`, `xhigh`/`max`) are checked locally per model.
  - `markup_path`: a transparent annotation layer for "edit inside the red circle" requests.
- **API key:**
  - `userConfig.openai_api_key` (`sensitive: true`, `required: false`, so the server can start and `get_status` works without a key) and an optional `openai_base_url`.
  - `.mcp.json` maps `${user_config.openai_api_key}` into the server env and explicitly **blanks** `OPENAI_ADMIN_KEY`, `OPENAI_ORG_ID`, `OPENAI_PROJECT_ID`, `OPENAI_CUSTOM_HEADERS` and similar, so ambient shell values don't leak in.
  - It passes `GPT_IMAGE_WORKSPACE_ROOT=${CLAUDE_PROJECT_DIR}` and `GPT_IMAGE_PLUGIN_DATA=${CLAUDE_PLUGIN_DATA}`.
  - A missing key returns `CONFIG_MISSING` before any provider call.
- **Outputs:**
  - `.claude/generated-images/gpt-image/` with unique names that contain no prompt text.
  - An explicit path must be relative to an approved workspace root.
  - **Never overwrites** (`OUTPUT_EXISTS`).
  - Actual dimensions are read back from the file; a difference from the request is flagged `SIZE_MISMATCH`.
  - **An inline preview is included only when the file is 2 MiB or smaller.**
  - Provider SVGs that contain scripts, external refs or embedded rasters are rejected.
  - Inputs are copied to private snapshots before upload.
- **Cost / concurrency / retries:** "one paid call at a time in each server process", no SDK retries and no app retries. A rate-limit error is returned as a failed paid call. No cost meter.
- **Clever:** the README's security model treats returned paths, filenames and provider content as untrusted data. Logs never contain prompts, keys or base64.

## 15. gabelul/pixeltamer-gpt-image-skill

- **URL:** https://github.com/gabelul/pixeltamer-gpt-image-skill
- **Stars / last push:** 6 · 2026-11-09 (MIT).
- **Type:** cross-agent skill with a dispatcher (`pixeltamer doctor`), Python API script, Node helpers and a trigger eval (`evals/run-trigger-eval.mjs`).
- **Three backends:** `api` (Images API key), `codex` (codex CLI agent), `codex-images`.
  - `codex-images` calls `chatgpt.com/backend-api/codex` directly with the token from `~/.codex/auth.json`. That is a private endpoint, which is a ToS and fragility risk. Avoid it.
- **How it calls OpenAI:** `generate` → `/images/generations`; `edit` / `compose` (2–16 refs) → `/images/edits`. Default `gpt-image-2.6-flare`. `-n N` sends N parallel single-image calls instead of `n=N`.
- **API key:**
  - `OPENAI_IMAGE_API_KEY` (image-specific) is preferred over `OPENAI_API_KEY`.
  - `.env` search order: cwd, `~/.config/pixeltamer/.env`, `~/.claude/.env`, script folder.
  - `PIXELTAMER_*` keys are refused from `.env` files so a project `.env` can't redirect credentials.
- **Errors:**
  - Machine-readable JSON `{ok, error:{code, message, retryable: yes|no|unknown}}`.
  - `unknown` is used for timeouts after the request was sent: "may have produced an image, and retrying blindly duplicates work you already paid for".
  - Failure output still lists files already written, because they cost money.
  - Retries 429/5xx with exponential backoff. 403 hints at org verification.
  - It does not separate `insufficient_quota` 429 from rate-limit 429.
- **Also:** checks that saved bytes match the requested format; GIF pixel-budget check.

### Also looked at (less relevant or stale)

- **spartanz51/imagegen-mcp:** 37 stars, last push 2025-05. npx MCP server; dall-e-2/3 + gpt-image-1. Defaults `moderation=low`; saves to temp files and returns path + base64.
- **CLOUDWERX-DEV/gpt-image-1-mcp:** 18 stars, 2025-05. Saves to the OS Pictures folder or `./generated-images/image-<ts>.png`; prints token usage. Users asked for a custom base URL (#4) and gpt-image-1.5 (#5).
- **TamerinTECH/claude-code-generate-images-mcp:** 13 stars. "Generate assets while vibe coding"; writes into `<workingDirectory>/generated-images`; has a UI-mockup prompt builder; supports Azure OpenAI gpt-image-1 only.
- **FradSer/dotclaude `generate-image`:** 596 stars for the whole repo. Plugin skill run through `uv run`. `--backend` has no default (the user must choose gemini or openai). `lib/progressive_env.py` resolves settings in this order: flag, env, `$PWD/.env`, `${CLAUDE_PLUGIN_ROOT}/.env`. A key file in the plugin root is lost on plugin update, so don't copy that.
- **leoleoasd/gpt-image-2-skill** (0 stars): env first, then a saved key file.
- **michaeldmueller/etch-image** (5 stars): userConfig for three provider keys.
- MCP registry entries `com.nuverlabs/image-gen` and `app.payperwork/images` (pay-per-image over x402) only came up in search. Not reviewed.

---

## Comparison table

| # | Project | ★ | Last push | Type | Lang | API path | Default model / quality / size | Key source | Output location & naming | Image back to agent | Edit / refs / mask / alpha / n>1 / batch | Cost / budget | Moderation & 429 handling |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | openai `imagegen` (Codex) | 136k (codex) | 2026-09 | Skill + Py CLI | Python | Built-in tool (default); Images API fallback | gpt-image-2 / medium / auto | env only | `output/imagegen/…`, `NNN-slug`, no overwrite w/o `--force` | via Codex `view_image` | ✓ / ✓16 / ✓ / chroma→native / ✓ / JSONL concurrency | none | backoff on 429/timeouts; none for moderation |
| 2 | wuyoscar/GPT-Image2-Skill | 6.2k | 2026-11 | CC+Codex plugin, skill, CLI | Python | Images API | 2.6-flare / high / 1024² (moderation=low) | env → ./.env → ~/.env | `./fig/` or cwd, `ts-slug.ext`, overwrites | path only | ✓/✓/✓/✓/✓/– (+local sprite→GIF) | policy text + `max_retries=0` | prints error, "stop, don't retry" |
| 3 | garden-skills gpt-image-2 | 15.6k (coll.) | 2026-11 | Skill + Node | JS | Images REST | gpt-image-2 / API default | args → env → .env/.gateway.env | `garden-gpt-image-2/image/slug-ts.png` + saved prompt .md | path only | ✓/✓/✓/flag/**n>1 bug**/– | none | none |
| 4 | shinpr/mcp-image | 195 | 2026-11 | MCP | TS | Images API | 2.6-flare low ("fast") | env | `image-<ms>-<hex>` | file:// resource JSON | ✓/✓/–/–/n=1/– | none | keyword hints; safe error allowlist |
| 5 | SureScaleAI/openai-gpt-image-mcp | 119 | 2025-05 | MCP | TS | Images API (+Azure) | gpt-image-1 / API defaults | env / `--env-file` | base64 inline; >1 MB → `/tmp/openai_image_<ms>` | **inline image** | ✓/✓/✓/✓/✓/– | none | none |
| 6 | guinacio/claude-image-gen | 83 | 2026-11 | CC plugin + MCP + MCPB | TS | Images API | gpt-image-2 / – / aspect→3 sizes | shell env (plugin); MCPB user_config | `./generated-images/generated-<uuid>` | resource_link | ✓/✓/✓/✓(auto-PNG)/–/– | none | 4xx pass-through; observed-rejection list |
| 7 | lansespirit/image-gen-mcp | 69 | 2026-04 | MCP | Python | Images API | gpt-image-2 | env/settings | `./storage/images/<ts+uuid>` + JSON sidecar, 30-day retention | resource URI / URL | ✓/–/–/✓/–/– | per-call estimate; **param cache** | none |
| 8 | codex-image-in-cc / GENEXIS | 52 / 192 | 2026-09 / 08 | CC plugin / skill | JS | none (Codex subscription) | Codex decides | Codex login | `./codex-images/<ts>-n.png` | `SAVED:` lines | ✓/✓5/–/✓/via prompt/✓(GENEXIS) | plan quota | n/a |
| 9 | Borys520/gpt-image-2-mcp | 14 | 2026-09 | MCP | TS | Images API, Responses fallback for edits | gpt-image-2 / auto / auto | env | `~/.config/…/output/<project>-<hash>/image-ts-rand.png` | **inline + structuredContent** | ✓/✓8/✓/✓/✓/sessions | usage-based estimate | none special; had SSRF/path bugs |
| 10 | spritecast | 371 | 2026-11 | CC plugin (skill+hook) | Python | Images edits (raw HTTP) | 2.5-sunburst / high | **userConfig → SessionStart → CLAUDE_ENV_FILE** | project `out/` | skill shows results | edit-only/✓/–/own cutout/n=1/– | **estimate → `--yes` gate**, actual $ printed | 429/5xx ×3 |
| 11 | nicknisi image-gen | 114 (mkt) | 2026-08 | CC plugin skill | TS (bundled) | Images API | gpt-image-2 / auto / 1K | env / `--api-key` | caller-given, `YYYY-MM-DD-HH-MM-SS-name.png` | **explicitly no** | ✓/1/✓/–/–/– | none | none |
| 12 | strato-space/media-gen-mcp | 9 | 2026-01 | MCP | TS | Images API (+Azure) | gpt-image-1.5 | env/.env | allowlisted dirs, `output_<t>_media-gen__tool_uuid` | configurable (link / inline, sharp-compressed) | ✓/✓16/✓/✓/✓/– | usage-based | isError text |
| 13 | HarinJin/kez-gpt-image-mcp | 4 | 2026-07 | Remote MCP (CF Worker) | TS | Images REST | gpt-image-2 / medium / 1024×1536 | Worker secret | R2 + widget | **widget card with $** | ✓/✓/–/–/–/**queued batch, 5/min** | usage-based | **maps moderation / 401 / quota / 429** (but batch retries all) |
| 14 | kpkhxlgy0 gpt-image plugin | 0 | 2026-11 | CC plugin + bundled MCP | TS | Images API | 2.6-flare / high / 1024² | **userConfig sensitive; other OPENAI_* blanked** | `.claude/generated-images/gpt-image/`, no-overwrite | inline preview only if ≤2 MiB | ✓/✓8/✓/✓/**n fixed 1**/– | 1 paid call at a time; no retries | rate limit = failed call |
| 15 | pixeltamer | 6 | 2026-11 | Skill + dispatcher | Py/JS | Images API (+risky ChatGPT backend) | 2.6-flare | `OPENAI_IMAGE_API_KEY` → `OPENAI_API_KEY`, .env chain | – | path in JSON | ✓/✓16/✓/✓/parallel singles/✓ | – | `retryable: yes/no/unknown`; 429/5xx backoff |

Legend for the edit column: edit / reference images (max count) / mask / transparent background / n>1 / batch.

---

## Patterns worth copying

1. **Keep the key in `userConfig` with `sensitive: true`, and keep it out of chat, flags and `.env` files.**
   - kpkhxlgy0 and spritecast do this. Set `required: false` so the server or skill still loads and can report "no key configured" without calling the API.
   - For an MCP server, pass `${user_config.openai_api_key}` in `.mcp.json` and **blank other `OPENAI_*` vars** (org, project, base URL, admin key) so the user's shell env can't silently redirect the server (kpkhxlgy0).
   - For skill scripts run from Bash, a SessionStart hook can write it to `$CLAUDE_ENV_FILE` (spritecast). The tradeoff is that the key reaches every Bash command in the session.
   - An image-specific override name such as `OPENAI_IMAGE_API_KEY` is useful (pixeltamer).
2. **Make the agent agree to spending.**
   - Print the estimated cost before calling the API; spend only after confirmation (`--yes`) or user approval (spritecast).
   - Default to one image per call. Ask before more variants or a higher quality (wuyoscar, kpkhxlgy0).
   - Turn off hidden SDK retries on billable calls (`max_retries=0`) (wuyoscar, kpkhxlgy0, guinacio).
3. **Report real cost from `response.usage`, not only a guess.** Put it in the text summary and in `structuredContent` (Borys520, strato-space, HarinJin, spritecast). Fall back to a conservative price when the model is unknown (HarinJin). Mark estimates that may be low (Borys520's fallback-route note).
4. **Return requested vs applied settings plus usage in `structuredContent`** (Borys520): model snapshot, size actually delivered, `revised_prompt` when present (shinpr). Check the saved file's real dimensions and format and flag `SIZE_MISMATCH` (kpkhxlgy0, shinpr's MIME check).
5. **Let the agent see the image, within a size limit.**
   - Return an inline image block only for small files (≤1–2 MB) (SureScaleAI, kpkhxlgy0). Otherwise return a file path or `resource_link`, or recompress a preview (strato-space).
   - For a skill-based plugin, the equivalent is to print the path and tell Claude to `Read` it when it needs to check the result. Make that conditional, because nicknisi deliberately skips it to save tokens.
6. **Predictable output locations that never overwrite.**
   - Write to a project-relative default folder.
   - Names: timestamp + short slug or random suffix (`YYYYMMDD-HHMMSS-<slug>-<rand>.png`).
   - Never overwrite; write a versioned sibling instead (OpenAI imagegen, kpkhxlgy0).
   - Keep the final prompt next to the image (garden's `prompt/*.md`, lansespirit's JSON sidecar). This makes results reproducible and lets someone audit spend.
7. **Reject impossible combinations locally, but don't hard-code a full capability matrix.**
   - Check what is certain: transparent needs png/webp; a mask needs a base image; GIF/SVG-only options need those formats; n is 1–10; custom-size rules.
   - Keep a short list of rejections *actually observed* from the API (guinacio's `OBSERVED_MODEL_REJECTIONS`) and pass unknown combinations to the API.
   - Hard-coded format and model enums broke wuyoscar when 2.6 shipped (#33).
8. **Classify errors so the agent knows whether to retry.**
   - 400 `moderation_blocked` (at input *or* output stage): don't retry unchanged; tell the user and suggest a rewrite (HarinJin).
   - 401: bad key. 403: org verification needed (pixeltamer, shinpr).
   - 429 with `insufficient_quota`: budget used up, **don't retry**. A plain 429 rate limit: back off and honour `retry-after` (OpenAI imagegen).
   - Mark timeouts after the request was sent as `retryable: unknown`, because an image may already be billed (pixeltamer).
   - Return a stable error `code`, a human message and a suggestion, without echoing the prompt (shinpr's safe-context allowlist).
9. **Batch with a pacing limit.** Use JSONL jobs with bounded concurrency (OpenAI imagegen: default 5, max 25) or a per-minute pace for tier-1 accounts (HarinJin: 5 per minute). Report the files that were already written when a batch fails (pixeltamer).
10. **Sandbox file inputs.** Only read reference images and masks from inside the project or an allowlist. Resolve realpaths. Don't fetch URLs unless they are allowlisted (strato-space `MEDIA_GEN_DIRS` / `MEDIA_GEN_URLS`; Borys520's SSRF report is the counterexample). Snapshot inputs before upload (kpkhxlgy0).
11. **A setup/status command that costs nothing**, such as `/…:setup` → `get_status` or `pixeltamer doctor`. It reports whether a key is set (never the key itself), the default model, the output folder, and whether the plugin is reachable.
12. **Ship pre-built code.** Avoid `npm install` at runtime: commit `dist/` bundles (nicknisi, kpkhxlgy0, guinacio). Or use a self-contained `uv run` PEP 723 script (wuyoscar, FradSer).
13. **Stop the agent from writing its own SDK code.** Tell it to "use the bundled script/tool only, never write an SDK runner" (OpenAI imagegen, wuyoscar). Issue #12 shows agents otherwise write `openai.Client(...)` themselves when the skill fails to trigger. Back this up with good trigger wording; pixeltamer even has a trigger eval.
14. **Optional prompt layer, clearly separated from the API call.** Either a deterministic labelled template (OpenAI `--augment` fields), a template library (garden, wuyoscar), or an LLM rewrite step with an off switch and verbatim text kept (shinpr). Leave the details to the prompt-construction notes.

## Mistakes to avoid

- **Silent loss or clobbering:**
  - Reading only `data[0]` when `n>1` (garden).
  - Overwriting existing files (wuyoscar).
  - Writing to `/tmp` by default, where files disappear and the project can't see them (SureScaleAI, strato-space default).
- **Dumping base64 into the agent's context:** printing the raw API response (garden `--json`) or always inlining 4K PNGs.
- **Key handling:**
  - `--api-key` CLI flags (nicknisi, FradSer) leak into history and transcripts.
  - Reading `$PWD/.env` or `~/.env` can pick up a project's or an expired key without the user noticing (wuyoscar #12).
  - A `.env` in `CLAUDE_PLUGIN_ROOT` is wiped on plugin update.
  - Inline "export OPENAI_API_KEY=…" instructions are criticised in openai/skills #520.
- **Retrying the wrong errors:** retrying moderation and quota errors (HarinJin's batch worker); treating every 429 as a rate limit when `insufficient_quota` also comes back as a 429 (pixeltamer, spritecast); hidden SDK retries on billable calls.
- **Hard-coded model, format and size enums with no escape hatch**: these broke on 2.6 (wuyoscar #33), and stale defaults kept `gpt-image-1.5` (openai/skills #538) or pinned `gpt-image-1` as a literal (SureScaleAI). Allow a free-form `model` and `extra` passthrough, and keep defaults in one place.
- **Unbounded file and URL access** in reference-image parameters: SSRF and arbitrary file read/write (Borys520 #1); extension-only checks that let any file be sent to a third party (guinacio #3).
- **Default `moderation=low`** without telling the user (wuyoscar, spartanz51). Keep the API default (`auto`) unless the user opts in.
- **Defaults that cost more than they need to**, without saying so: `quality=high` by default (wuyoscar, kpkhxlgy0, spritecast) roughly quadruples cost compared with medium. If you choose such a default, say it in the tool description.
- **Fragile dependencies on other CLIs:** Codex CLI flag changes broke codex-image-in-cc (#5), and private ChatGPT endpoints are used in pixeltamer's `codex-images` backend.
- **Aspect-ratio mapping that quietly changes what the user asked for** (16:9 becoming 3:2) without a warning. guinacio gets this right by returning a warning.
