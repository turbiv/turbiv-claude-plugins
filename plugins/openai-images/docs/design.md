# openai-images: design

Date: 2026-11-21. Status: approved by the user 2026-11-21.

## Intent

Claude can't draw. The user wants to describe an idea in Claude Code and have Claude do the rest. Claude writes a
strong image prompt, generates the image with OpenAI's best image model, saves the file, looks at it, checks it
against the request, and fixes the prompt when something is wrong. The user pays OpenAI per image from a small
prepaid balance (about $5), so every image must cost cents and show what it cost. The plugin lives in the
`turbiv-claude-plugins` marketplace and others may install it.

The user's bar: **best quality, reliable, the least amount of bullshit, and secure.**

## Goals

- One command, `/openai-images:image <idea>`, plus Claude using it on its own when asked to make or edit an image.
- Best-quality model by default, at a price that fits $5: `gpt-image-2.5-sunburst` at `medium` quality, 1024x1024,
  about $0.013 per image (#1 on Arena; 2.6 costs about 3x more at medium for a small gain).
- Generate new images and edit existing ones, using up to 16 reference images, a mask, and transparent backgrounds.
- Claude writes prompts from a built-in guide (OpenAI's official rules plus recipes), then reviews each result
  against a checklist and changes only what failed.
- After every image, Claude says what it cost and what has been spent so far.
- The API key is entered once, kept in the OS secure store, and never reaches the shell, the chat or a file.

## Non-goals

- Other image providers (Gemini, FLUX, ...). Possible later, not now.
- Video, the Responses API, multi-turn image conversations, streaming previews, batch jobs.
- A second LLM that rewrites prompts. Claude is the prompt writer.
- A gallery, an image browser or an artifact page.

## Anti-goals (what would make it a failure even if it works)

- The key leaks: printed, logged, in a settings file, or readable by Bash commands.
- Money is spent silently: hidden retries, n>1 by default, `high`/`max` quality by default, retrying quota errors.
- Images are lost or overwritten, or raw base64 is dumped into the chat.
- It breaks every time OpenAI ships a model because the model list is hard-coded.
- Setup takes more than "install, paste key".

## Constraints

- Claude Code plugin, same repo conventions as `kanban`: manifest in `.claude-plugin/plugin.json`, skills in
  `skills/`, a README, tests, entry in the marketplace and README table, `claude plugin validate .` passes.
- A `sensitive` userConfig value only reaches an MCP server (via `${user_config.KEY}` in its `env`); it does not
  reach skill text, Bash or bin scripts. That is why this is an MCP server.
- Needs `uv` on the machine (the server runs with `uv run --script`, dependencies pinned in the script header).
- OpenAI may require Organization Verification for GPT Image models; the plugin must explain that error, not crash.
- `gpt-image-1.5`, `gpt-image-1-mini`, `chatgpt-image-latest` shut down 2026-12-01; `gpt-image-2` on 2027-02-10.

## Prerequisites (done by the user, before the first real image)

These are done by hand in the OpenAI dashboard and are needed only for the final end-to-end test; the build and all
other tests use a fake OpenAI and need none of them.

1. OpenAI Platform account at platform.openai.com (separate from a ChatGPT subscription).
2. Add prepaid credit (Settings → Billing), e.g. $5. This puts the account in the Build usage tier.
3. Organization Verification (Settings → Organization → General → Verify Organization): government ID + selfie;
   can take up to 15 minutes to apply. GPT Image models may refuse to work without it.
4. A dedicated project for this plugin (e.g. "openai-images") with a monthly budget limit, and an API key created
   in that project with permissions limited to Images if offered. A leaked key can then spend at most the budget.
5. Keep the key in a password manager until the plugin exists, then enter it once with
   `/plugin configure openai-images` (or in the install dialog). It is never pasted into the chat.
6. `uv` installed (`brew install uv`). Already present on the author's machine.

## Approaches considered

| | How the key is kept | Trade-off |
|---|---|---|
| A. Shell env var + Python script | `OPENAI_API_KEY` in the user's shell profile | Least code. Key in plain text, readable by every Bash command Claude runs. |
| **B. Bundled MCP server (picked)** | Sensitive userConfig, OS secure store, passed only to the server process | Key never reaches Bash or the chat; spend rules live in the server where Claude can't skip them; Claude Code asks before each paid tool call. More code than A. |
| C. Secure key + SessionStart hook | Sensitive userConfig, copied into each session's env file by a hook | Less code than B, but the key ends up in a plain-text env file readable by Bash, so barely safer than A. |

**Picked: B,** by the user's bar (secure, reliable, least bullshit). Within B:

- **Official MCP Python SDK** (`mcp`, FastMCP) rather than a hand-written protocol: protocol handling is the part most
  likely to break, and the SDK is the common, maintained path. Cost: needs `uv`, which the user has.
- **Plain HTTP (httpx, already a dependency of `mcp`) rather than the `openai` SDK:** no hidden retries, new
  parameters and models need no SDK upgrade, and the error JSON is used as OpenAI documents it.

## Design

### Layout

```
plugins/openai-images/
  .claude-plugin/plugin.json     name, version 0.1.0, userConfig, mcpServers
  server/openai_images.py        the MCP server (PEP 723 header pins mcp, httpx)
  server/core.py                 pure logic: request building, cost, errors, paths (no network, no MCP)
  skills/image/SKILL.md          /openai-images:image: workflow, critique loop
  skills/image/prompt-guide.md   prompt rules, templates, recipes (read by the skill)
  tests/                         pytest/unittest for core.py and the server with a fake HTTP transport
  docs/design.md, docs/research/ this file and the research notes
  README.md
```

### Configuration (userConfig)

| Key | Type | Default | Notes |
|---|---|---|---|
| `openai_api_key` | string, `sensitive` | none | Not `required`, so the server still starts and reports "no key set". |
| `default_model` | string | `gpt-image-2.5-sunburst` | Any model id; not validated against a list. |
| `default_quality` | string | `medium` | |
| `max_cost_per_call` | number | `0.10` | A call whose estimated total (all `n` images, plus input-image allowance) is above this is refused unless the call sets `allow_expensive: true`. |

The server's `env` passes the key as `OPENAI_IMAGES_API_KEY` and blanks `OPENAI_BASE_URL`, `OPENAI_ORG_ID`,
`OPENAI_PROJECT_ID`, so a stray shell variable or `.env` can't redirect calls or swap the key. The server only
calls `https://api.openai.com/v1`.

### Tools

1. **`generate_image`**: `prompt` (required), `model`, `size` (default `1024x1024`), `quality`, `background`
   (`auto|opaque|transparent`), `output_format` (`png|webp|jpeg`, default `png`), `n` (default 1, max 4),
   `filename` (slug), `output_dir`, `allow_expensive`. (`n` up to 4; cost cap is per call, see Spending rules.)
2. **`edit_image`**: same, plus `images` (1–16 local paths; the first is the one edited), optional `mask` (local
   PNG). Sent as JSON with base64 data URLs to `/v1/images/edits`.
3. **`image_status`**: free. Says whether a key is set (never shows it), the defaults, the output folder, the price
   table used for estimates, and total spent (all time and this session).

The server does **not** keep a list of allowed models. It checks only what is certain: `transparent` needs png or
webp; custom sizes are multiples of 16, ratio 1:3 to 3:1, at most 3840 per edge, 655,360–8,294,400 pixels; `n` is
1–4; input images exist and are image files. Anything else goes to the API, and the API's error comes back cleanly.

### Spending rules

- Before each call the server estimates the output cost with OpenAI's published formula (from the docs' token
  calculator; checked against the published gpt-image-2 prices). Unknown models are estimated at the 2.6 rates,
  the most expensive current ones. Edits add input-image tokens, which OpenAI publishes no formula for; the estimate
  adds a conservative allowance of **$0.05 per input image and per mask** (builder's call: about 6,000 tokens at $8/M,
  above what high-fidelity inputs are expected to use) and labels it as an allowance. The real input cost from
  `usage` is logged after the call, so the allowance can be tuned from the user's own data later.
- The cap is **per call** (builder's call): estimated output for all `n` images + input allowance, compared with
  `max_cost_per_call`. Above it → refused with the estimate, unless `allow_expensive: true`. So a 16-reference edit
  (~$0.80 allowance) always needs explicit approval. The skill tells Claude to ask the user before setting it.
- After the call, if the real cost from `usage` was more than 1.5× the estimate, the result says so.
- One HTTP attempt per call for anything that may have been billed. Retries only for errors that are certainly not
  billed: 429 rate limit (not quota), 500, 503; at most 2 retries, honouring `Retry-After`, 180 s timeout per
  attempt. A timeout after sending is reported as "may have been billed", not retried.
- Real cost is computed from the response's `usage` and appended to a spend log (JSON lines) in
  `${CLAUDE_PLUGIN_DATA}`. Each tool result shows this image's cost and the running totals.
- Claude Code's own permission prompt before each `generate_image`/`edit_image` call is the per-image consent;
  the README explains how to allow it permanently if the user wants.

### Files

- Default output folder: `generated-images/` in the project the session runs in (the server's working directory).
  `output_dir` may point elsewhere inside the project; paths outside it are refused.
- Name: `YYYYMMDD-HHMMSS-<slug>.<ext>`, plus `-2`, `-3`... when the name exists. Never overwrites.
- Next to each image, a `.json` sidecar: prompt, all settings sent, settings OpenAI reports back, usage, cost,
  model, request id, and the input image paths for edits.
- Input images and masks must be inside the project (real paths resolved, so `..` and symlinks can't escape).
  No URLs are ever fetched.
- Images outside the project (user's decision): the skill has Claude copy the file into
  `generated-images/inputs/` after the user OKs the copy, then edit the copy. The server's sandbox stays strict.
  Images pasted into the chat have no file and can't be edited until saved as a file; the README says so.
- The tool result is text: file path, size, cost, totals, and a reminder to Read the file. No base64 in the result.
  (Claude Code's Read tool shows PNG/JPEG/WebP to Claude; returning image blocks from MCP is unconfirmed.)

### Errors

Each error result has a stable code, a plain message and what to do next. Never echoes the key.

| Case | Code | Retry? | Message tells the user/Claude |
|---|---|---|---|
| No key set | `no_api_key` | no | run `/plugin configure openai-images` |
| 401 | `bad_api_key` | no | key rejected; reconfigure |
| 403 "must be verified" | `org_verification_required` | no | link to platform.openai.com/settings/organization/general; up to 15 min after verifying |
| 400 `moderation_blocked` | `moderation_blocked` | no | stage (input/output) and categories; Claude rephrases, doesn't resend unchanged |
| other 400 | `invalid_request` | no | OpenAI's message, e.g. unsupported parameter for that model |
| 404 / `model_not_found` | `model_not_found` | no | model id not available to this account |
| 429 `credit_balance_exhausted` / `insufficient_quota` / spend-limit codes | `out_of_credit` | no | add credit at platform.openai.com/settings/organization/billing |
| 429 rate limit | `rate_limited` | yes (≤2) | wait time |
| 500 / 503 | `openai_unavailable` | yes (≤2) | try again later |
| timeout after send | `timeout_maybe_billed` | no | check the usage page before retrying |

### The skill (`/openai-images:image`)

Triggers when the user asks to create, draw, design, or edit an image, icon, logo, poster, mockup, etc. It tells
Claude to use only the plugin's tools (never write its own OpenAI code). The flow:

1. Understand the request; ask at most one question only when the use (where the image goes) or exact text is
   unclear. Otherwise pick sensible defaults and say them.
2. Write the prompt from `prompt-guide.md`: intended use first, then scene, subject, details, constraints; exact
   text in quotes with placement; labeled sections for complex prompts. Pick size from the use (e.g. 1536x1024 for
   a banner, 1024x1536 for a poster).
3. Make a short checklist from the request (text spelled right, counts, colors, layout, must-haves).
4. Call `generate_image` once with defaults (medium). Use `low` for quick explorations when the user wants options.
5. Read the saved file, check each checklist item, and report: path, cost, totals, what passed, what didn't.
6. If something failed and the fix is clear, make one more attempt that changes only what failed (an edit when
   the rest is good, a new generation when the composition is wrong). Stop after 2 automatic fix attempts per
   request and ask the user.
7. Never raise quality to high/xhigh/max, use n>1, or go over the cost cap without asking.

`prompt-guide.md` holds the 12 rules, the generate and edit templates, the critique checklist, and recipes for:
poster/flyer, app icon, logo, product shot, infographic/diagram, photo edit, illustration, transparent sticker.
Source: `docs/research/prompt_construction.md` (Part B), cut to what Claude needs.

### Tests

- `core.py`: cost formula (matches published gpt-image-2 prices: $0.006/$0.053/$0.211 at 1024²), size
  validation, error classification for every row of the table, file naming and no-overwrite, path sandboxing,
  sidecar contents, usage-to-cost.
- Server: tool calls against a fake HTTP transport (no network, no spend): success, moderation block, quota,
  rate-limit retry then success, timeout, missing key.
- `claude plugin validate .` from the repo root.
- One real end-to-end call (about $0.013) after the user has added credit and set the key, viewed by Claude.

## Calls left to the builder

- Exact SDK versions to pin (latest stable `mcp` and `httpx` at build time).
- Exact wording of tool descriptions and error messages, within the table above.
- Slug rules for filenames.
- How the session spend total is scoped (per server process is fine).
