# openai-images

Describe an image in Claude Code, and Claude makes it with OpenAI's GPT Image models. Claude writes the
prompt, generates the image, saves the file, looks at it, checks it against what you asked for, and fixes
what is wrong. After each image, Claude tells you what it cost and how much you have spent so far.

The default is `gpt-image-2.5-sunburst` at medium quality, 1024x1024: about **$0.013 per image**. With $5
of OpenAI credit, that is more than 300 images.

<img src="docs/example-hello-world.jpg" alt="A portrait poster: bold white &quot;Hello World&quot; over a sunset at sea" width="320">

Made with `/openai-images:image a poster that says "Hello World" in bold letters on a sunset background`.
Claude picked a 1024x1536 poster size, wrote the prompt, checked the spelling and layout, and reported the
cost: **$0.011** with `gpt-image-2.5-sunburst` at medium quality, first try.

## What you get

- **`/openai-images:image <idea>`**, and Claude also uses it on its own when you ask it to make or edit
  an image, icon, logo, poster, illustration or mockup.
- **New images and edits.** An edit changes one image of yours, can use up to 15 more as references,
  and can use a mask. Transparent backgrounds work with PNG and WebP.
- **A check after each image.** Claude reads the saved file and checks it against a short list made from
  your request (text spelled right, counts, colors, layout). It fixes what failed, at most twice, then
  asks you.
- **The cost of every image**, and the totals for this session and for all time.
- **No surprise spending.** One image per call, medium quality, no hidden retries. A call that would
  cost more than your cap is refused until you say yes. Claude asks before it uses high, xhigh or max
  quality, or more than one image per call.
- **Your key stays secret.** It is kept in the OS secure store (the macOS Keychain, for example) and
  goes only to this plugin's MCP server. Bash commands, the chat and files never see it.

## What it needs

1. **An OpenAI Platform account** at [platform.openai.com](https://platform.openai.com). This is not the
   same as a ChatGPT subscription.
2. **Prepaid credit**, for example $5 (Settings → Billing).
3. **Organization Verification** (Settings → Organization → General → Verify Organization). You need a
   government ID and a selfie. OpenAI may refuse GPT Image models without it. Access can take up to 15
   minutes after you verify.
4. **A project just for this plugin**, for example "openai-images", with a monthly budget limit, and an
   API key made in that project. If OpenAI offers it, limit the key's permissions to Images. Then a
   leaked key can spend at most that budget.
5. **`uv`** on your computer (`brew install uv` on macOS, or see
   [docs.astral.sh/uv](https://docs.astral.sh/uv/)). Claude Code starts the server with
   `uv run --script`, and `uv` gets the Python packages it needs on the first start.

Keep the key in your password manager until you enter it in the next step.

## Setup

1. Install the plugin:

   ```text
   /plugin install openai-images@turbiv-claude-plugins
   ```

2. **Enter the key once.** The install dialog asks for it. If you skipped it, or to change it later,
   run:

   ```text
   /plugin configure openai-images
   ```

   Never paste the key into the chat. Text you type in the chat goes to the model and stays in the
   session's transcript.

3. Start a new Claude Code session. Ask "image status" to check: Claude says whether a key is set (it
   never shows the key), the defaults, and what you have spent.

## Usage

```text
/openai-images:image a flat app icon of a paper plane, blue on white
```

Or just ask: "make a poster for the bake sale on Saturday at 10", "remove the background from
`photos/mug.jpg`", "make three quick low-quality options for a logo".

Claude Code asks for your OK before each paid call. That prompt is your per-image consent. To skip it,
see [Allow the tools without asking](#allow-the-tools-without-asking).

**Edits need a file.** An image you paste into the chat has no file, so Claude cannot edit it. Save it
as a file in your project first, then name the file. An image from outside the project is copied into
`generated-images/inputs/` first, and Claude asks you before it copies it.

### The tools

| Tool | Does | Costs |
|---|---|---|
| `generate_image` | Makes 1 to 4 new images from a prompt | Yes |
| `edit_image` | Edits `images[0]`, with the other images (up to 16 in all) as references, and an optional PNG `mask` | Yes |
| `image_status` | Says whether a key is set, the defaults, the cost cap, the output folder, the prices used, and the totals spent | Free, no network |

Both paid tools take `prompt`, and optionally `model`, `size` (default `1024x1024`, or `auto`), `quality`,
`background` (`auto`, `opaque` or `transparent`), `output_format` (`png`, `webp` or `jpeg`; default
`png`), `n` (1 to 4, default 1), `filename`, `output_dir` and `allow_expensive`.

### Where the images go

- `generated-images/` in the project folder, named `YYYYMMDD-HHMMSS-<short-name>.png`. If the name is
  taken, `-2`, `-3` and so on are added. A file is never overwritten.
- Next to each image, a `.json` file with the prompt, the settings, what it cost and the request id.
- Input images and masks must be inside the project. Paths that lead outside it, also through `..` or a
  symlink, are refused. The plugin never downloads from a URL.

## Cost

Estimated price of one 1024x1024 image. At the same quality, 1536x1024 costs a bit less, and 2048x2048
or 3840x2160 about twice as much.

| Model | low | medium | high | xhigh | max |
|---|---|---|---|---|---|
| `gpt-image-2.5-sunburst` (default) | $0.006 | **$0.013** | $0.053 | $0.094 | $0.211 |
| `gpt-image-2.6-sunburst` | $0.025 | $0.043 | $0.053 | $0.094 | $0.211 |

- These are OpenAI's published estimates for the image output. The prompt text adds a fraction of a cent.
- An edit also pays for its input images. OpenAI publishes no formula for that, so the estimate adds
  **$0.05 per input image and per mask**. This is a safe allowance, and the real cost is logged after
  the call.
- **The cost cap** (`max_cost_per_call`, default $0.10) is per call: all images in the call plus the
  input allowance. A call above it is refused with the estimate. Claude then asks you, and sends it
  again with `allow_expensive` only if you say yes. At medium quality, an edit with 2 or more input
  images (the image plus one reference, or the image plus a mask) is above the default cap.
- The real cost comes from OpenAI's `usage` in the reply. The result says so when it is more than 1.5
  times the estimate.
- A model the plugin does not know is estimated at the 2.6 prices, the highest.

## Settings

Change them in the install dialog or with `/plugin configure openai-images`.

| Setting | Default | Meaning |
|---|---|---|
| `openai_api_key` | none | Your key. Kept in the OS secure store |
| `default_model` | `gpt-image-2.5-sunburst` | Any OpenAI image model id. Not checked against a list, so new models work at once |
| `default_quality` | `medium` | `low`, `medium`, `high`, `xhigh`, `max` or `auto` |
| `max_cost_per_call` | `0.10` | The cost cap per call, in USD |

Start a new session after a change.

## Allow the tools without asking

Claude Code asks before each `generate_image` and `edit_image` call. To stop the prompts, add the tools to
`permissions.allow` in `~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "mcp__plugin_openai-images_openai-images__image_status",
      "mcp__plugin_openai-images_openai-images__generate_image",
      "mcp__plugin_openai-images_openai-images__edit_image"
    ]
  }
}
```

`mcp__plugin_openai-images_openai-images` alone allows all three. You can also choose "don't ask again"
in the prompt itself. With the tools allowed, Claude can spend without asking you each time, up to the
cost cap per call. The project's budget limit at OpenAI is the hard stop.

## Troubleshooting

Each error starts with a code and says what to do next.

| Code | What happened | What to do |
|---|---|---|
| `no_api_key` | No key is set | Run `/plugin configure openai-images`, then start a new session |
| `bad_api_key` | OpenAI rejected the key (401) | Check the key in the OpenAI project, or make a new one, and enter it again |
| `org_verification_required` | The organization is not verified (403) | Verify at [Settings → Organization → General](https://platform.openai.com/settings/organization/general). Wait up to 15 minutes, then try again |
| `out_of_credit` | Credit is used up, or a budget or spend limit was hit (429) | Add credit at [Billing](https://platform.openai.com/settings/organization/billing), or raise the project's limit. Never retried |
| `rate_limited` | Too many requests (429) | Retried up to 2 times on its own. If it still fails, wait a minute |
| `openai_unavailable` | OpenAI had a server error (500 or 503) | Retried up to 2 times on its own. If it still fails, try later |
| `timeout_maybe_billed` | No answer within 180 seconds | It may have been billed. Check the [usage page](https://platform.openai.com/usage) before you try again |
| `moderation_blocked` | OpenAI's safety filter blocked the prompt or the image | The message says which stage and category. Claude changes the prompt; sending it unchanged fails again |
| `invalid_request` | OpenAI refused a setting (400), or a size, format or count is not valid | The message says which. For example, `transparent` needs `png` or `webp` |
| `model_not_found` | The model id does not exist or this account cannot use it (404) | Check `default_model`, or use the default |
| `over_cost_cap` | The estimate is above `max_cost_per_call` | Claude asks you. Say yes to send it with `allow_expensive`, or raise the cap |
| `path_outside_project` | An input or output path is outside the project | Copy the file into the project, for example into `generated-images/inputs/` |
| `input_not_found` | An input image does not exist, or is not PNG, JPEG or WebP | Check the path. A pasted image must be saved as a file first |

**The tools are missing.** Check that `uv` is installed (`uv --version`), then run `/mcp` and look at
the `openai-images` server. The first start downloads the Python packages and needs the internet.

## Privacy and security

- The key is in the OS secure store and in the MCP server's environment only. The server blanks
  `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_ORG_ID` and `OPENAI_PROJECT_ID`, so a stray variable in
  your shell can't swap the key or send calls somewhere else.
- The server calls only `https://api.openai.com/v1`. Your prompts and input images go to OpenAI.
- No key and no image data are written to results, logs or the `.json` files.

## Where the data is

| Place | Holds |
|---|---|
| `generated-images/` in the project | The images, their `.json` files, and copied inputs in `inputs/` |
| `~/.claude/plugins/data/openai-images-turbiv-claude-plugins/spend.jsonl` | The spend log: one line per call, with its cost. The totals come from it |
| The OS secure store | The key |

Uninstalling the plugin deletes the spend log (keep it with `--keep-data`). The images stay.

## How it is built

- `server/openai_images.py`: the MCP server (Python, official MCP SDK), started with `uv run --script`.
  The packages it needs are pinned in the file's header.
- `server/core.py`: the logic without network: cost, checks, errors, file names, the spend log.
- `skills/image/`: the skill. `SKILL.md` is the flow; `prompt-guide.md` holds the prompt rules,
  templates and recipes.
- `docs/`: the design, the build plan and the research notes.

## For developers

Run the tests from the repo root. They use a fake OpenAI and spend nothing.

```bash
uv run --no-project --with mcp==2.3.0 --with httpx==0.28.1 python -m unittest discover -s plugins/openai-images/tests
```
