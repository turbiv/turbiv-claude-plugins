---
name: image
description: Creates or edits images with OpenAI GPT Image through this plugin's openai-images MCP tools - draw, design or generate a picture, icon, app icon, logo, poster, flyer, illustration, sticker, product shot, infographic, diagram or mockup, or edit, retouch or change an existing photo or image file. Use for /openai-images:image, "make an image of...", "draw...", "design a logo", "edit this photo", "remove the background".
argument-hint: "<what to make or change>"
---

# Image

You turn the user's idea into a strong image prompt, make the image with this plugin's MCP tools, look at
the saved file, and fix only what is wrong. The user pays OpenAI per image from a small prepaid balance,
so every call costs real money. Spend as little as the request needs.

Request: $ARGUMENTS

## Rules

- Use only the tools of the `openai-images` MCP server: `generate_image`, `edit_image`, `image_status`
  (in the tool list they may appear as `mcp__plugin_openai-images_openai-images__<tool>`). Never write your
  own OpenAI code, never call the API with curl, Python or an SDK, never ask for or read an API key. If the
  tools are missing or fail to start, say so and stop.
- Ask at most one clarifying question per request, and only when the use (where the image goes) or the
  exact text cannot be guessed. Otherwise pick sensible defaults and say them in one line. Consent
  questions below (cost, copying a file) are asked only when they apply, one at a time, in one short line.
- Never raise `quality` to `high`, `xhigh` or `max`, set `n` above 1, or set `allow_expensive: true`
  without asking the user first. Say the estimate when you ask.
- One call at a time. Never call a tool again with the same arguments after it failed.

## 1. Understand the request

Find: the deliverable and where it will be used, any exact text, the size or ratio, and any input images
with the role of each (edit target or reference). Read `${CLAUDE_SKILL_DIR}/prompt-guide.md` before
writing the first prompt in a session; it has the rules, templates and recipes.

Input images:

- Paths may be relative to the project folder. The server refuses files outside the project.
- If an input file is outside the project, ask: "Copy `<path>` into `generated-images/inputs/` so I can
  edit it?" Only after a yes, copy it with Bash (`mkdir -p generated-images/inputs` then `cp -n`, never
  overwrite; add `-2` to the name if it exists) and pass the copy's path.
- An image pasted into the chat has no file. Ask the user to save it in the project and give the path.

If you are not sure the plugin is set up, call `image_status` (free, no network) and check `key_set`.

## 2. Write the prompt

Follow `prompt-guide.md`: intended use first, then scene, subject, details, constraints; labeled lines for
anything complex; every string that must appear in "double quotes" with position, typography and
"exactly once"; then "No other text" where text matters. Keep the user's own details. Do not add
characters, brands, slogans or story beats they did not imply. For edits, use the edit template: change
only X, then the preserve list.

Pick `size` from the use, not the prompt alone: `1024x1024` square (icons, logos, stickers),
`1024x1536` portrait (posters, flyers), `1536x1024` landscape (banners, product shots, diagrams),
`1536x864` 16:9 (slides, video thumbnails). Custom sizes must follow the rules in the guide.

## 3. Make a checklist

Before the call, write a short checklist from the request (3-8 items): each quoted string spelled right
and shown once, counts, required elements, colors, layout or placement, style, exclusions (no extra text,
no watermark), transparency if asked. Each item must be something you can see in the image.

## 4. Call the tool

- New image: `generate_image(prompt, size, background, output_format, filename)`. Leave `model` and
  `quality` unset so the user's defaults apply (normally `gpt-image-2.5-sunburst`, `medium`, about
  0.013 USD at 1024x1024). Use `quality: "low"` for quick options when the user wants to explore.
- Change an existing image: `edit_image(prompt, images, mask, ...)`. `images[0]` is the image edited;
  the others (up to 16 in all) are references, each named by number and role in the prompt. `mask` is an
  optional PNG with alpha, the same size as `images[0]`.
- Transparent: `background: "transparent"` with `output_format` `png` or `webp`, and describe only the
  isolated subject in the prompt.
- `filename` is a short slug (`streak-app-icon`). Files go to `generated-images/` and are never
  overwritten. Leave `output_dir` unset unless the user names a folder inside the project.
- Each input image and mask adds a 0.05 USD allowance to the estimate. With the default cap of 0.10 USD,
  an edit with two or more inputs is refused with `over_cost_cap`.

## 5. Look at the result and report

The result has `files[].path`, `cost_usd`, `estimate_usd`, `spent_session_usd`, `spent_total_usd`,
`settings_applied` and `warnings`. Then:

1. Read each saved file with the Read tool (`files[].path`). Never judge an image you have not opened.
2. Check every checklist item: PASS or FAIL. Exact text and required elements are hard gates: a pretty
   image with a wrong word fails. Read small text closely. Also look for invented text, logos or numbers,
   extra or missing objects, broken hands or faces, changes outside the edit area, mood drift. For
   transparency, the background must be empty, not a drawn checkerboard.
3. Report in a few lines: the path, what this image cost (`cost_usd`), the session and all-time totals
   (`spent_session_usd`, `spent_total_usd`), what passed and what failed. Pass on any `warnings`.

## 6. Fix what failed

- If an item failed and the fix is clear, make one more attempt that changes only what failed:
  - `edit_image` with the saved file as `images[0]` when the composition is right and the error is local
    (one wrong word, one extra object). Use the edit template and repeat the preserve list.
  - `generate_image` with the prompt changed only on the failing line when the layout or concept is wrong.
- At most 2 automatic fix attempts per request. After that, or when the fix is unclear, show the best
  image, list what is still wrong, and ask the user how to go on.
- Don't fix things the user did not ask for. When all items pass, stop.

## 7. Spend only with consent

Ask before any of these, in one line with the estimate, and wait for a yes:

- `quality` `high`, `xhigh` or `max` (high is about 4x medium; offer it for dense or small text).
- `n` greater than 1 (offer it when the user wants several options, e.g. logo ideas).
- `allow_expensive: true`. When a call fails with `over_cost_cap`, tell the user the estimate from the
  error and ask; retry with `allow_expensive: true` only after a yes.

## Errors

A failed call raises an error `"<code>: <message> Next: <next_step>"`. Follow its `Next` and:

- `no_api_key`, `bad_api_key`: the user runs `/plugin configure openai-images`. Never ask for the key.
- `org_verification_required`: the user verifies the OpenAI organization; it can take 15 minutes.
- `out_of_credit`: the user adds credit. Do not retry.
- `moderation_blocked`: never resend unchanged. Rewrite once by the guide's moderation advice (input
  stage: drop names, brands, loaded words; output stage: add a modest, benign context). If it is blocked
  again, explain and ask.
- `invalid_request`, `model_not_found`: fix the parameter named in the message, or tell the user.
- `rate_limited`, `openai_unavailable`: the server already retried. Tell the user to try later.
- `timeout_maybe_billed`: do not retry. The image may have been billed; the user can check the OpenAI
  usage page.
- `path_outside_project`, `input_not_found`: check the path; for a file outside the project, see step 1.

At the end, give the final file path(s) and, if you changed it during fixes, the final prompt.
