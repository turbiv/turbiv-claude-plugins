# openai-images Implementation Plan

> **For agentic workers:** this plan is built by three parallel sessions, one per Part. Each session reads the
> Global Constraints, the Contracts, and its own Part. Use TDD inside your Part (failing test → code → passing test →
> commit). Steps use checkbox (`- [ ]`) syntax for tracking. Touch only the files your Part lists.

**Goal:** A Claude Code plugin that lets Claude generate and edit images with OpenAI's GPT Image models through a
bundled MCP server, with the API key in the OS secure store and every image's cost shown.

**Architecture:** A Python MCP server (official MCP SDK 2.x, `MCPServer`) launched with `uv run --script`. Pure logic
(cost, validation, errors, files) lives in `server/core.py`; the MCP tools and HTTP calls live in
`server/openai_images.py`. A skill teaches Claude to write prompts, call the tools, look at the result and fix it.

**Tech Stack:** Python ≥3.11, `mcp==2.3.0`, `httpx==0.28.1`, `uv`, stdlib `unittest`.

**Spec:** `plugins/openai-images/docs/design.md` (approved 2026-11-21). Read it first; this plan does not repeat it.

## Global Constraints

- Default model `gpt-image-2.5-sunburst`, default quality `medium`, default size `1024x1024`, default `n` 1, max `n` 4.
- Cost cap `max_cost_per_call` default `0.10` USD, per call: output estimate for all `n` + `$0.05` per input image and
  per mask. Over the cap → refused unless `allow_expensive: true`.
- Prices (USD per token) for every `gpt-image-2*` id and unknown ids: text in `5e-6`, image in `8e-6`, image out
  `30e-6`. Unknown models are estimated with the 2.6 formula (most expensive).
- Only `https://api.openai.com/v1` is called. No URL is ever fetched for inputs.
- Never overwrite a file. Never put base64 or the API key in a tool result, log, sidecar or error.
- No model allow-list. Validate only: `transparent` needs `png|webp`; custom size multiple of 16, ratio 1:3–3:1,
  each edge ≤3840, pixels 655,360–8,294,400; `n` 1–4; input files exist, are png/jpeg/webp, inside the project.
- HTTP timeout 180 s per attempt. Retry only `rate_limited` and `openai_unavailable`, at most 2 retries, honour
  `Retry-After` (seconds), else 2 s then 8 s.
- MCP SDK 2.x renamed FastMCP: use `from mcp.server.mcpserver import MCPServer`; tool errors raise
  `mcp.server.mcpserver.exceptions.ToolError`. Tests use the in-memory client: `async with Client(server) as c:
  await c.call_tool(name, args)` (`from mcp.client import Client`). Migration guide:
  https://py.sdk.modelcontextprotocol.io/v2/migration/
- Test command (whole plugin, from the repo root):
  `uv run --no-project --with mcp==2.3.0 --with httpx==0.28.1 python -m unittest discover -s plugins/openai-images/tests`
- Imports: `openai_images.py` does `import core` (the script's folder is on `sys.path` under `uv run --script`).
  Tests put `plugins/openai-images/server` on `sys.path` (a `tests/fixtures.py` like kanban's) and `import core`,
  `import openai_images`. No `__init__.py` packages.
- Repo conventions: see `plugins/kanban` (README style, unittest tests, `claude plugin validate .` from the repo root).

## Review Focus

1. Quota exhausted (429 `insufficient_quota`/`credit_balance_exhausted`) must never be retried — the user's last
   cents go to repeated failures otherwise. Part A test `test_quota_429_not_retried`.
2. Two calls in the same second with the same slug must produce two files, not one overwritten. Part A
   `test_output_path_unique_same_second`.
3. A symlink inside the project pointing outside must be refused as input. Part A `test_symlink_escape_refused`.
4. `size: "auto"` / `quality: "auto"` must still be estimated (worst case) so the cap can't be dodged. Part A
   `test_estimate_auto_is_worst_case`.
5. A key with surrounding whitespace or an empty string from an unset userConfig placeholder must read as "no key",
   not be sent. Part A `test_blank_key_is_no_key`.

## Contracts (shared by all Parts — do not change without telling the coordinator)

### Files

```
plugins/openai-images/
  .claude-plugin/plugin.json     Part C
  server/openai_images.py        Part A  (PEP 723 header: requires-python >=3.11; dependencies mcp==2.3.0, httpx==0.28.1)
  server/core.py                 Part A
  tests/test_core.py             Part A
  tests/test_server.py           Part A
  skills/image/SKILL.md          Part B
  skills/image/prompt-guide.md   Part B
  README.md                      Part C
  docs/                          read-only for all Parts
repo root: .claude-plugin/marketplace.json, README.md   Part C
```

### Server launch and environment (Part A reads these, Part C writes them in plugin.json)

Command: `uv run --script ${CLAUDE_PLUGIN_ROOT}/server/openai_images.py`. MCP server name: `openai-images`.

| Env var | Set from | Meaning |
|---|---|---|
| `OPENAI_IMAGES_API_KEY` | `${user_config.openai_api_key}` | key; blank/whitespace/unsubstituted `${...}` → no key |
| `OPENAI_IMAGES_DEFAULT_MODEL` | `${user_config.default_model}` | blank → `gpt-image-2.5-sunburst` |
| `OPENAI_IMAGES_DEFAULT_QUALITY` | `${user_config.default_quality}` | blank → `medium` |
| `OPENAI_IMAGES_MAX_COST_PER_CALL` | `${user_config.max_cost_per_call}` | blank/unparsable → `0.10` |
| `OPENAI_IMAGES_DATA_DIR` | `${CLAUDE_PLUGIN_DATA}` | spend log folder; blank → `~/.claude/plugins/data/openai-images` |
| `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_ORG_ID`, `OPENAI_PROJECT_ID` | `""` | blanked; the server ignores them anyway |

Project folder: env `CLAUDE_PROJECT_DIR` if set and non-blank, else the server's working directory.

### MCP tools (Part A implements; Parts B and C describe them)

`generate_image(prompt: str, model: str | None = None, size: str = "1024x1024", quality: str | None = None,
background: str = "auto", output_format: str = "png", n: int = 1, filename: str | None = None,
output_dir: str | None = None, allow_expensive: bool = False) -> dict`

`edit_image(prompt: str, images: list[str], mask: str | None = None, ...same optional params...) -> dict` —
`images[0]` is edited, the rest are references (1–16). Paths may be relative to the project folder.

`image_status() -> dict` — free, no network: `{"key_set": bool, "defaults": {...}, "max_cost_per_call": float,
"output_dir": str, "spent_session_usd": float, "spent_total_usd": float, "prices": {...}}`.

Success result of generate/edit (a dict; the SDK sends it as structured content plus JSON text):

```
{"files": [{"path": "<abs path>", "sidecar": "<abs path .json>", "width": 1024, "height": 1024, "bytes": 1234567}],
 "model": "gpt-image-2.5-sunburst",
 "settings_sent": {...}, "settings_applied": {"size": ..., "quality": ..., "background": ..., "output_format": ...},
 "estimate_usd": 0.013, "cost_usd": 0.0137, "spent_session_usd": 0.05, "spent_total_usd": 1.20,
 "warnings": ["..."], "next_step": "Read <path> to check the image against the request."}
```

Failure: raise `ToolError` with text `"<code>: <message> Next: <next_step>"`. Codes, exactly:
`no_api_key, bad_api_key, org_verification_required, moderation_blocked, invalid_request, model_not_found,
out_of_credit, rate_limited, openai_unavailable, timeout_maybe_billed, over_cost_cap, path_outside_project,
input_not_found`.

`over_cost_cap` message includes the estimate and says to ask the user, then retry with `allow_expensive: true`.

Files: default output folder `<project>/generated-images/`; edit inputs from outside the project are copied by Claude
to `<project>/generated-images/inputs/` (Part B's skill does this, after the user OKs it).

---

## Part A: the Python server (session `server`)

**Goal for `/goal`:** "The test command in `plugins/openai-images/docs/plan.md` Global Constraints exits 0 with all
Part A tests passing (shown in the transcript), including `test_cost_matches_published_gpt_image_2`,
`test_quota_429_not_retried`, `test_moderation_not_retried`, `test_rate_limit_retried_then_ok`,
`test_timeout_maybe_billed`, `test_no_key`, `test_symlink_escape_refused`, `test_output_path_unique_same_second`;
and no file outside `plugins/openai-images/server/` and `plugins/openai-images/tests/` was changed. Or stop after 40
turns."

**Read first:** `docs/design.md` (whole); `docs/research/openai_api.md` §1–6 and §9 (endpoints, params, the cost
formula in §4 "Official per-image output token estimates", error table §5); `docs/research/existing_repos.md`
"Patterns worth copying" and "Mistakes to avoid"; MCP SDK v2 migration guide (URL above). Research more yourself
where these leave a gap (e.g. MCP SDK 2.3.0 behaviour) and note what you found in your final report.

### Task A1: `core.py` — config, estimates, cost

**Files:** Create `server/core.py`, `tests/test_core.py`.

**Produces:**
- `@dataclass(frozen=True) class Config: api_key: str | None; default_model: str; default_quality: str;
  max_cost_per_call: float; project_dir: Path; data_dir: Path`
- `load_config(env: Mapping[str, str], cwd: Path) -> Config`
- `estimate_output_tokens(model: str, quality: str, width: int, height: int) -> int` — the calculator formula from
  `openai_api.md` §4, including the 2.6 multipliers (low 4.2, medium 3.3); ids starting `gpt-image-2.5` use 2.5
  bases; exactly `gpt-image-2` / `gpt-image-2-<date>` use gpt-image-2 bases; everything else uses 2.6.
- `@dataclass class Estimate: output_usd: float; input_allowance_usd: float; total_usd: float; notes: list[str]`
- `estimate_cost(model: str, quality: str, size: str, n: int, input_images: int) -> Estimate` — `auto` quality →
  `high`; `auto` size → `1024x1024`; each adds a note.
- `cost_from_usage(model: str, usage: dict) -> float`

- [ ] Tests: `test_cost_matches_published_gpt_image_2` (gpt-image-2 1024x1024 low/medium/high → 0.006/0.053/0.211
  rounded to 3 dp; 1536x1024 → 0.005/0.041/0.165); `test_estimate_2_6_medium` (1449 tokens at 1024²);
  `test_estimate_2_5_medium` (439 tokens); `test_estimate_auto_is_worst_case`; `test_input_allowance` (3 inputs →
  0.15); `test_cost_from_usage` (example usage from §4 → text 10×5e-6 + image-in 40×8e-6 + out 50×30e-6);
  `test_blank_key_is_no_key` (`""`, `"  "`, `"${user_config.openai_api_key}"` → `None`); `test_config_defaults`.
- [ ] Implement until green. Commit.

### Task A2: `core.py` — validation and errors

**Produces:**
- `class ImagesError(Exception): code: str; message: str; next_step: str; retryable: bool` with
  `__str__` → `"<code>: <message> Next: <next_step>"`.
- `parse_size(size: str) -> tuple[int, int] | None` (`None` for `auto`)
- `validate_request(*, size: str, background: str, output_format: str, n: int) -> None` raises
  `ImagesError("invalid_request", ...)`
- `classify_error(status: int, body: dict | None, headers: Mapping[str, str]) -> ImagesError` — the design's error
  table; `retry_after` parsed from the header into an attribute `retry_after: float | None`.

- [ ] Tests: one per error-table row (401, 403 "must be verified", 400 `moderation_blocked` with stage+categories in
  the message, other 400, 404 `model_not_found`, 429 each quota/spend code → `out_of_credit` not retryable, plain 429
  → `rate_limited` retryable with `retry_after`, 500, 503); size rules (1536x864 ok, 1000x1000 not multiple of 16,
  4000x1000 too wide, 512x512 too few pixels, 3840x1280 ratio 3:1 ok); transparent+jpeg refused; n=5 refused.
- [ ] Implement until green. Commit.

### Task A3: `core.py` — files, sidecar, spend log

**Produces:**
- `resolve_inside(project_dir: Path, path: str) -> Path` — realpath; raises `path_outside_project`.
- `check_input_image(project_dir: Path, path: str) -> Path` — inside project, exists (`input_not_found`), png/jpeg/webp
  by magic bytes.
- `output_path(out_dir: Path, slug: str | None, prompt: str, ext: str, now: datetime) -> Path` —
  `YYYYMMDD-HHMMSS-<slug>.<ext>`, slug from `filename` or first words of the prompt, `[a-z0-9-]`, ≤40 chars;
  `-2`, `-3`… if taken.
- `write_new(path: Path, data: bytes) -> None` — exclusive create (`"xb"`), makes parent dirs.
- `image_info(data: bytes) -> tuple[str, int, int]` — format, width, height from PNG/JPEG/WebP headers.
- `write_sidecar(image_path: Path, record: dict) -> Path` — `<image>.json`, never contains base64 or the key.
- `append_spend(data_dir: Path, record: dict) -> None` and `spend_totals(data_dir: Path, session_id: str) ->
  tuple[float, float]` — JSON lines file `spend.jsonl`.

- [ ] Tests: `test_output_path_unique_same_second`, `test_symlink_escape_refused`, `..` refused, absolute path outside
  refused, `test_write_new_never_overwrites`, image_info on tiny PNG/JPEG/WebP fixtures built in the test,
  sidecar has prompt/settings/usage/cost and no `b64`, spend totals across two sessions.
- [ ] Implement until green. Commit.

### Task A4: `openai_images.py` — MCP server

**Consumes:** everything above. **Produces:** `create_server(config: Config, http: httpx.Client, sleep:
Callable[[float], None] = time.sleep, now: Callable[[], datetime] = ...) -> MCPServer` and a `__main__` that builds
the real `Config` from `os.environ` and runs stdio. Tools exactly as in Contracts.

Request building: generations → JSON `POST /v1/images/generations`; edits → JSON `POST /v1/images/edits` with
`images: [{"image_url": "data:<mime>;base64,..."}]` and `mask` likewise. Omit `input_fidelity`. Send only parameters
the caller set or the defaults above. Decode `data[].b64_json`, write each file, sidecar, spend log.

- [ ] Tests in `tests/test_server.py` (`IsolatedAsyncioTestCase`, `httpx.MockTransport`, temp project dir, fake
  `sleep` that records calls): `test_generate_ok` (file written, result fields per Contracts, request body has
  model/quality/size defaults, Authorization header present, result has no base64); `test_edit_ok` (two inputs sent
  as data URLs); `test_no_key` (no HTTP call made); `test_over_cost_cap` then same with `allow_expensive`;
  `test_moderation_not_retried` (one HTTP call); `test_quota_429_not_retried`; `test_rate_limit_retried_then_ok`
  (sleep called with Retry-After); `test_timeout_maybe_billed` (`httpx.ReadTimeout` → code, no retry);
  `test_image_status_no_network`; `test_list_tools_names` (exactly the three tools).
- [ ] Implement until green. Commit.
- [ ] Smoke: `printf '' | timeout 5 uv run --script plugins/openai-images/server/openai_images.py` starts without an
  import error (exit by timeout is fine). Commit.

---

## Part B: the skill and prompt guide (session `skill`)

**Goal for `/goal`:** "`plugins/openai-images/skills/image/SKILL.md` and `prompt-guide.md` exist; `claude plugin
validate plugins/openai-images` reports no errors for the skill (shown in the transcript); SKILL.md covers, and the
transcript quotes the lines for, each of: when to trigger, use only the plugin's tools, one question at most, the
checklist, Read the saved file, at most 2 automatic fix attempts, ask before high/xhigh/max or n>1 or
`allow_expensive`, copying outside-project inputs into `generated-images/inputs/` after the user OKs it, reporting
cost and totals; prompt-guide.md has the generate and edit templates and the 8 recipes from the design; and no file
outside `plugins/openai-images/skills/` was changed. Or stop after 30 turns."

**Read first:** `docs/design.md` ("The skill" section and Goals); `docs/research/prompt_construction.md` (all of it;
Part B there is the draft guide); `docs/research/openai_api.md` §3 (sizes, quality, background, so recipes pick valid
values) and §7; `docs/research/existing_repos.md` pattern 13 (stop the agent writing its own SDK code) and the OpenAI
Codex `imagegen` skill it links; Claude Code skills docs https://code.claude.com/docs/en/skills.md. Research more
yourself where these leave a gap and note what you found in your final report.

### Task B1: `skills/image/SKILL.md`

Frontmatter: `name: image`; `description` that leads with the trigger (create, draw, design, edit an image, icon,
logo, poster, illustration, mockup, photo edit) and says it uses OpenAI via this plugin; `argument-hint: "<what to
make or change>"`; no `disable-model-invocation` (the MCP permission prompt is the spend consent);
`allowed-tools` only if it is needed for Read of `generated-images/**`.

Body: the 7-step flow from the design, written as instructions to Claude, with tool names and params exactly as in
Contracts. Point to `prompt-guide.md` with `${CLAUDE_SKILL_DIR}/prompt-guide.md`. Keep it under ~150 lines.

- [ ] Write it. Run `claude plugin validate plugins/openai-images`. Commit.

### Task B2: `skills/image/prompt-guide.md`

Cut Part B of `prompt_construction.md` to what Claude needs: the rules (mark official vs community briefly), the
generate and edit templates, the critique checklist, size/quality picks per use, failure modes with fixes, and
recipes for: poster/flyer, app icon, logo, product shot, infographic/diagram, photo edit, illustration, transparent
sticker. Each recipe: size, background, quality, template filled for one example.

- [ ] Write it. Check every size/quality value against `openai_api.md` §3 rules. Commit.

---

## Part C: packaging (session `packaging`)

**Goal for `/goal`:** "`claude plugin validate .` from the repo root exits 0 (shown in the transcript) with the
`openai-images` plugin listed in `.claude-plugin/marketplace.json`; `plugins/openai-images/.claude-plugin/plugin.json`
declares the four userConfig keys and the `openai-images` MCP server exactly per the Contracts env table;
`plugins/openai-images/README.md` covers what it does, prerequisites, install, entering the key, usage, cost, how to
allow the tools permanently, troubleshooting by error code, and that pasted images can't be edited until saved; the
repo README table has a row for it; and no file under `plugins/openai-images/server|skills|tests` was changed. Or stop
after 30 turns."

**Read first:** `docs/design.md` (Configuration, Prerequisites, Errors, Files); Claude Code plugin docs:
https://code.claude.com/docs/en/plugins/manifest-reference.md (userConfig, env vars, where each variable resolves),
https://code.claude.com/docs/en/plugins/components.md (MCP servers, `${user_config.*}`),
https://code.claude.com/docs/en/plugins/create.md, https://code.claude.com/docs/en/plugins/cli-reference.md;
`docs/research/openai_api.md` §5–6 (errors, verification) for troubleshooting; the repo `README.md` and
`plugins/kanban/README.md` for style. Research more yourself where these leave a gap (e.g. whether
`${CLAUDE_PLUGIN_DATA}` and `${CLAUDE_PROJECT_DIR}` expand in an MCP `env`) and note what you found in your final
report.

### Task C1: `plugin.json`

`name: openai-images`, `version: 0.1.0`, description, author `Ivan Turbin`. `userConfig`: `openai_api_key` (string,
sensitive, not required), `default_model` (string, default `gpt-image-2.5-sunburst`), `default_quality` (string,
default `medium`; use `options` low/medium/high/xhigh/max/auto if the validator accepts it), `max_cost_per_call`
(number, default 0.10, min 0.01). `mcpServers.openai-images`: command `uv`, args `["run", "--script",
"${CLAUDE_PLUGIN_ROOT}/server/openai_images.py"]`, env per the Contracts table.

- [ ] Write it. `claude plugin validate plugins/openai-images` (a missing server file is expected to be fine; if the
  validator requires it, note it in the report instead of creating it). Commit.

### Task C2: README and marketplace

- [ ] `plugins/openai-images/README.md` per the goal list. Prerequisites copied from the design. Cost table: 2.5
  Sunburst low/medium/high at 1024² $0.006/$0.013/$0.053; 2.6 $0.025/$0.043/$0.053.
- [ ] Marketplace entry and repo README table row (same style as kanban). `claude plugin validate .`. Commit.

---

## After the three Parts (coordinator, this session)

1. Ask the user before merging `server`, `skill`, `packaging` branches into `claude/openai-images-plugin`.
2. Run the full test command and `claude plugin validate .`.
3. Load the plugin from the checkout, `/plugin configure openai-images`, run `image_status`, then one real
   `generate_image` at medium (~$0.013) and Read the file.
4. Open the PR.
