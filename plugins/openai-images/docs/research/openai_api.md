# OpenAI Image API: implementation notes for the openai-images plugin

Researched 2026-11-20 from the official docs at developers.openai.com. Each page also serves as Markdown when you add `.md` to its URL, and the quotes below come from those files.

Sources read:
- Guide: https://developers.openai.com/api/docs/guides/image-generation
- Responses tool guide: https://developers.openai.com/api/docs/guides/tools-image-generation
- Prompting guide: https://developers.openai.com/api/docs/guides/image-prompting
- Reference: `api/reference/resources/images/methods/{generate,edit,create_variation}`, `api/reference/resources/responses/methods/create`
- Pricing: https://developers.openai.com/api/docs/pricing
- Model pages: `api/docs/models/gpt-image-2.6-sunburst`, `-2.6-flare`, `-2.5-sunburst`, `gpt-image-2`, `gpt-image-1.5`, `gpt-image-1-mini`, `chatgpt-image-latest`
- Deprecations, changelog, error-codes and rate-limits pages
- The cost calculator's JavaScript: `/_astro/GptImageTokenCalculator.react.*.js`, linked from the guide

Markers:
- **[UNVERIFIED]** means no official page confirms the point.
- **[CONFLICT]** means two official pages disagree.

---

## 1. Endpoints and when to use which

| | Images API | Responses API + `image_generation` tool |
|---|---|---|
| Routes | `POST /v1/images/generations` (JSON), `POST /v1/images/edits` (multipart **or** JSON) | `POST /v1/responses` with `tools:[{"type":"image_generation", "model": "<image model>", ...}]` |
| Top-level `model` | The image model, for example `gpt-image-2.6-flare` | A mainline model, for example `gpt-6.2-astra` or `gpt-5.5`. The image model goes in the tool's `model`. |
| Multi-turn editing | No. Each call stands alone, so you send the previous output back as `image`. | Yes: `previous_response_id`, or send an `{"type":"image_generation_call","id":"ig_..."}` input item |
| Streaming / partial images | Yes: `stream: true`, `partial_images` 0–3 | Yes: `stream: true`, tool `partial_images` 0–3 |
| Markup-guided edits (`markup`) | **Yes, Images API edits only** | No. The guide says: "For regional edits with the Responses API, use a mask" (`input_image_mask`). |
| Mask inpainting | `mask` on edits | `input_image_mask` on the tool |
| SVG / GIF output | Yes. SVG works on generations only; GIF works on generations and edits. | The tool schema lists `gif`/`svg` in `output_format`, but the guide documents both through the Image API only. |
| `revised_prompt` | "Not returned by GPT image models" | Returned on the `image_generation_call` item |
| Cost visibility | **Good.** `usage` splits text and image tokens for the image model alone. | Poor. `usage` has the mainline model's tokens, with no image-tool breakdown in the `ResponseUsage` schema, and adds the mainline model's own cost. |

The official guidance: "If you only need to generate or edit a single image from one prompt, the Image API is your best choice. If you want to build conversational, editable image experiences with GPT Image, go with the Responses API."

**Recommendation for the plugin:** use the Images API only. Claude already writes and iterates on the prompt, so the plugin does not need a second LLM rewriting prompts and charging for its tokens. The Images API also gives exact per-call `usage` and supports `markup`. To iterate, pass the previous output file back to `/v1/images/edits`.

## 2. Model ids

Model ids accepted by `/v1/images/generations` as of 2026-11-20, from the reference `model` enum:

| Model id | Status | Notes |
|---|---|---|
| `gpt-image-2.6-sunburst` | Current, released 2026-11-04 | "detailed visual work", precise edits. Alias only, no dated snapshot. **Default `model` for `/v1/images/edits` and for the Responses tool.** Batch is not supported. |
| `gpt-image-2.6-flare` | Current, released 2026-11-04 | "fast iteration", the smaller and faster model. No dated snapshot. Batch is not supported. |
| `gpt-image-2.5-sunburst`, `gpt-image-2.5-sunburst-2026-09-08` | Current, released 2026-09-08, not deprecated | Supports Batch |
| `gpt-image-2.5-flare`, `gpt-image-2.5-flare-2026-09-08` | Current | Supports Batch |
| `gpt-image-2`, `gpt-image-2-2026-04-21` | **Deprecated, shuts down Feb 10, 2027** (notice dated Nov 10, 2026) | |
| `gpt-image-1.5`, `gpt-image-1.5-2025-12-16` | **Deprecated, shuts down Dec 1, 2026** | Confirmed |
| `gpt-image-1-mini` | **Deprecated, shuts down Dec 1, 2026** | Confirmed |
| `chatgpt-image-latest` | **Deprecated, shuts down Dec 1, 2026** | Confirmed |
| `gpt-image-1` | Shut down 2026-10-23 | |
| `dall-e-2`, `dall-e-3` | Removed 2026-05-12 | |

The deprecations page names `gpt-image-2.6-sunburst` or `gpt-image-2.6-flare` as the replacement for every deprecated image model.

**Sunburst vs Flare:** each variant is a **separate model id**. No parameter selects the variant. The prompting guide says: "start with GPT-Image-2.6 Flare if response time matters most. Start with GPT-Image-2.6 Sunburst if the image must meet demanding requirements for detail, layout, or edit accuracy."

**`complexity`** is a separate request field, added with 2.6. Values are `"low" | "medium" | "high"`, and both models use `high` when it is omitted. It controls "how much the image model plans before rendering", independently of `quality`. The guide says "Adjusting complexity has no separate fee", but higher values add latency and can introduce unwanted changes.

The `/v1/images/variations` endpoint is **retired**: "This endpoint is retired and no longer available. Use the image edits endpoint…"

**[CONFLICT]** The guide overview still names `gpt-image-2.5-sunburst`/`-flare` as the main models, and its code samples use 2.5. The 2.6 section, the prompting guide, the deprecation replacements and the reference defaults all point to 2.6.

## 3. Request parameters

### 3a. `POST /v1/images/generations` (JSON body)

| Param | Type / values | Default | Notes |
|---|---|---|---|
| `model` | string id from §2 | none ("Specify a model explicitly") | |
| `prompt` | string | required | max **32000** chars |
| `size` | `"auto"`, `"1024x1024"`, `"1536x1024"`, `"1024x1536"`, or custom `"WxH"` | `"auto"` | See the size rules below. `256x256`, `512x512`, `1792x1024` and `1024x1792` are legacy DALL·E sizes. |
| `quality` | `"low"`, `"medium"`, `"high"`, `"xhigh"`, `"max"`, `"auto"` | `"auto"` | `xhigh`/`max` work on 2.5 and 2.6 only. Earlier models go up to `high`. `standard`/`hd` are legacy DALL·E values. |
| `complexity` | `"low"`, `"medium"`, `"high"` | model default (`high` for 2.6) | 2.6 (and 2.5?). See the §3c conflicts. |
| `background` | `"transparent"`, `"opaque"`, `"auto"` | `"auto"` | `transparent` requires `output_format` `png` or `webp`. Transparent output is in preview on `gpt-image-2`. |
| `output_format` | `"png"`, `"webp"`, `"jpeg"`, `"gif"`, `"svg"` | `"png"` | The guide says JPEG is faster than PNG. |
| `output_compression` | int 0–100 | 100 | jpeg/webp only |
| `n` | int 1–10 | 1 | `svg` requires `n=1` |
| `moderation` | `"auto"`, `"low"` | `"auto"` | |
| `stream` | bool | false | |
| `partial_images` | int 0–3 | 0 | Each partial image adds **100 image output tokens**. You may receive fewer partials than requested. |
| `safety_identifier` | string, max 128 chars | | Replaces the deprecated `user`. Send a hash, never raw PII. |
| `user` | string | | Deprecated, still accepted |
| `frame_count` | int 2–16 | 9 | gif only. "Requires access to the GIF preview for the selected model." |
| `frame_duration_ms` | int ≥20, max 2000 in the Responses schema, rounded to 10 ms | 200 | gif only |
| `svg` | `{ "model": str, "reasoning": {"effort": "none" through "max"} }` | | svg only. Supply it only when "SVG model selection is enabled". Otherwise omit it. |
| `response_format` | `url`/`b64_json` | | **Legacy and unsupported for GPT image models.** They "always return base64-encoded images". |
| `style` | `vivid`/`natural` | | Legacy and unsupported |

**Custom size rules** (guide, for Sunburst and Flare in 2.6 and 2.5):
- Format is `WIDTHxHEIGHT`, for example `1536x864`.
- Width and height must be multiples of 16.
- Aspect ratio must be between 1:3 and 3:1.
- Neither edge may exceed 3840 px.
- Total pixels must be between **655,360 and 8,294,400**. 8,294,400 is 3840x2160, which the reference calls the "maximum supported resolution".
- On 2.5, sizes above `2560x1440` are experimental.
- Note that 1024x1024 = 1,048,576 pixels, so it passes the minimum. 512x512 fails it.

**SVG:** set `output_format:"svg"`, generations only, `n=1`. Streaming, partials and `output_compression` are not supported. The reference adds that SVG also excludes `prompt_rewriter`. Decode `data[0].b64_json` to UTF-8 XML and save it as `.svg`. The output is static vector content only, with no scripts, external resources or embedded rasters. Billing covers the image model's reference image plus the "authoring model" tokens, reported in `svg_usage`. The edit reference says "SVG output requires a supported image model and project access."

**GIF:** set `output_format:"gif"` on generations or edits, with `frame_count` and `frame_duration_ms`. `size` describes each frame. Streaming, partials, custom compression and masks are not supported. Decode `b64_json` and save it as `.gif`. The frame count and frame dimensions must fit "the total request pixel budget".

### 3b. `POST /v1/images/edits`

The edit endpoint accepts two encodings.

**Multipart** (`multipart/form-data`) is what the guide's curl examples use:
- Fields: `model`, `prompt`, then `image[]` repeated for several files or `image` for one.
- Optional `mask` (file), `markup` (file) and every scalar field above, sent as strings.

**JSON** (`application/json`), which the reference documents as the body type and the changelog announced on 2026-02-09:
- `images`: array of `{ "image_url": "<https URL or data:image/...;base64,...>" }` or `{ "file_id": "file-..." }`. minItems 1, **maxItems 16**. `image_url` maxLength is 20,971,520 chars, about 15 MB of binary as base64.
- `mask`: `{image_url | file_id}`, exactly one of the two.
- `markup`: `{image_url | file_id}`.
- **For a stdlib urllib client, JSON with base64 data URLs is the simplest option because it needs no multipart encoder.**

Edit-specific parameters:

| Param | Notes |
|---|---|
| `image[]` / `images` | Up to **16** images. A mask or markup applies to the **first** image. The others act as references. |
| `mask` | PNG with an alpha channel, the same format and size as the first image, under 50 MB. The guide says masking is "entirely prompt-based", so the model "may not follow its exact shape with complete precision". |
| `markup` | A transparent PNG annotation layer with the same width and height as the first image after orientation. It "must contain transparent pixels; do not flatten it onto the original image." At most 16,777,216 px and 50 MB. **It cannot be combined with `mask`.** Supported on 2.5 and 2.6 models, at no extra fee. |
| `input_fidelity` | `"high"`/`"low"`, for `gpt-image-1.5` and `gpt-image-1-mini` (low only) only. **Omit it for gpt-image-2 and later.** Those models process every input at high fidelity, which can push input-image token counts up. The prompting guide repeats "Omit `input_fidelity` on image edits." |
| `model` | Default `gpt-image-2.6-sunburst` |
| `quality`, `size`, `background`, `output_format` (no svg), `output_compression`, `n` (1–10), `moderation`, `stream`, `partial_images`, `complexity`, `frame_count`, `frame_duration_ms`, `safety_identifier`, `user` | Same meaning as on generations |

### 3c. Responses `image_generation` tool options

The tool takes `type:"image_generation"` plus:
- `action`: `"auto"` (default), `"generate"` or `"edit"`. Forcing `edit` with no image in context is an error.
- The shared fields `background`, `complexity`, `frame_count`, `frame_duration_ms`, `input_fidelity`, `moderation`, `output_compression`, `output_format`, `partial_images`, `quality`, `size` and `svg`.
- `input_image_mask`: `{file_id | image_url}`.
- `model`: defaults to `gpt-image-2.6-sunburst`.

To force the tool, set `tool_choice: {"type":"image_generation"}`. The tool's `complexity` "overrides the outer response's `reasoning.effort` for image generation."

Input images go in a message as `{"type":"input_image","image_url":"data:image/png;base64,..."}` or `{"type":"input_image","file_id":"file-..."}`. Files are uploaded with `purpose:"vision"`.

**[CONFLICT] Reference vs guide on 2.6:**
- The reference text for `quality` (xhigh/max), `size` (custom sizes) and `background` names only the 2.5 models. The guide's prose says 2.6 and 2.5 both support xhigh/max and custom sizes.
- The `markup` reference text says "Supports GPT Image 2.5", while the guide and changelog say 2.5 **and** 2.6.
- The Responses tool reference enum includes 2.6 and defaults to `gpt-image-2.6-sunburst`. The tools guide and the 2.6 changelog entry mention only `v1/images/generations` and `v1/images/edits`.
- The guide's streaming section says partials are 0–3, while the tools guide says 1–3.

**[UNVERIFIED]** Neither the 2.5 nor the 2.6 docs say which `complexity` values 2.5 accepts. The guide and changelog tie `complexity` to the 2.6 release.

## 4. Response shape and cost

### Images API response (generations and edits)

```json
{
  "created": 1713833628,
  "background": "opaque",
  "data": [ { "b64_json": "..." } ],
  "output_format": "png",
  "quality": "medium",
  "size": "1024x1024",
  "safety_identifier": "...",
  "svg_usage": { "input_tokens": 0, "model": "...", "output_tokens": 0, "reasoning_tokens": 0, "total_tokens": 0 },
  "usage": {
    "input_tokens": 50,
    "input_tokens_details": { "text_tokens": 10, "image_tokens": 40 },
    "output_tokens": 50,
    "output_tokens_details": { "image_tokens": 50, "text_tokens": 0 },
    "total_tokens": 100
  }
}
```

How to read it:
- Field names come from the reference. The example values are a mix of the reference's two examples.
- `data[].b64_json` is always present. `url` and `revised_prompt` are never returned for GPT image models.
- `svg_usage` is present only for SVG output. `output_tokens_details` is marked optional.
- `quality`, `size` and `background` echo the resolved values. This matters when you sent `auto`.

The guide's Responses-API `image_generation_call` output item:

```json
{ "id": "ig_123", "type": "image_generation_call", "status": "completed",
  "revised_prompt": "A gray tabby cat hugging an otter. ...", "result": "<base64>" }
```

`status` is one of `in_progress`, `completed`, `generating` or `failed`. When moderation blocks the call, the item can carry `error: {code, message, param, type, moderation_details}`.

### Streaming (SSE, `stream: true`)

For a urllib client, read `resp` line by line, track the `event:` line, and run `json.loads` on each `data:` line.

```
event: image_generation.partial_image
data: {"type":"image_generation.partial_image","b64_json":"...","partial_image_index":0}

event: image_generation.completed
data: {"type":"image_generation.completed","b64_json":"...","usage":{...}}
```

- Edits use `image_edit.partial_image` and `image_edit.completed`.
- Responses streaming emits `response.image_generation_call.partial_image` (fields `partial_image_index`, `partial_image_b64`). The final image arrives in `response.completed` → `response.output[]`.

### Prices per 1M tokens (pricing page, Standard tier)

| Model | Text in | Cached text in | Image in | Cached image in | Image out | Text out |
|---|---|---|---|---|---|---|
| gpt-image-2.6-sunburst / -flare | $5 | $1.25 | $8 | $2 | **$30** | not billed |
| gpt-image-2.5-sunburst / -flare | $5 | $1.25 | $8 | $2 | $30 | not billed |
| gpt-image-2 | $5 | $1.25 | $8 | $2 | $30 | not billed |
| gpt-image-1.5, chatgpt-image-latest | $5 | $1.25 | $8 | $2 | $32 | $10 |
| gpt-image-1-mini | $2 | $0.20 | $2.50 | $0.25 | $8 | not billed |

- Batch costs half, but 2.6 does not support Batch.
- Cached input pricing for 2 and 2.5 applies only to the Responses tool, never to `/v1/images/*`.

### Computing cost from `usage` (Images API)

```python
RATES = {  # USD per token
  "gpt-image-2.6-sunburst": dict(text_in=5e-6, image_in=8e-6, image_out=30e-6, text_out=0),
  "gpt-image-2.6-flare":    dict(text_in=5e-6, image_in=8e-6, image_out=30e-6, text_out=0),
  "gpt-image-2.5-sunburst": dict(text_in=5e-6, image_in=8e-6, image_out=30e-6, text_out=0),
  "gpt-image-2.5-flare":    dict(text_in=5e-6, image_in=8e-6, image_out=30e-6, text_out=0),
  "gpt-image-2":            dict(text_in=5e-6, image_in=8e-6, image_out=30e-6, text_out=0),
  "gpt-image-1.5":          dict(text_in=5e-6, image_in=8e-6, image_out=32e-6, text_out=10e-6),
  "gpt-image-1-mini":       dict(text_in=2e-6, image_in=2.5e-6, image_out=8e-6, text_out=0),
}
def cost(model, u):
    r = RATES[model]; i = u.get("input_tokens_details", {}); o = u.get("output_tokens_details") or {}
    img_out = o.get("image_tokens", u.get("output_tokens", 0)); txt_out = o.get("text_tokens", 0)
    return (i.get("text_tokens", 0)*r["text_in"] + i.get("image_tokens", 0)*r["image_in"]
            + img_out*r["image_out"] + txt_out*r["text_out"])
```

Things the formula does not cover:
- SVG output also bills `svg_usage` at the authoring model's rates. The docs do not say which model that is, but `svg_usage.model` names it.
- Partial images are already counted in `usage`, at 100 output tokens each. **[UNVERIFIED]** that `usage` includes them.

### Official per-image output token estimates

The guide's interactive calculator implements this formula. It was read from `GptImageTokenCalculator.react.*.js` and checked against the guide's published gpt-image-2 table: $0.006, $0.053 and $0.211 at 1024², and $0.005, $0.041 and $0.165 at 1536x1024 all match.

```
base = {"gpt-image-2": {low:16, medium:48, high:96},
        "gpt-image-2.5" and "gpt-image-2.6": {low:16, medium:24, high:48, xhigh:64, max:96}}[model][quality]
s = base / (long_edge/short_edge);  d = round-half-to-even(s)
grid = base * d                      # base cells on the long edge, d on the short edge
tokens = ceil(grid * (2_000_000 + w*h) / 4_000_000)
if model is 2.6: tokens = round(tokens * {low:4.2, medium:3.3, high:1, xhigh:1, max:1}[quality])
```

Computed output tokens, with the cost at $30/M in brackets. The calculator itself says these figures exclude input tokens and partial images.

**gpt-image-2.6 (Sunburst and Flare)**

| quality | 1024x1024 | 1536x1024 / 1024x1536 | 1536x864 | 2048x2048 | 3840x2160 |
|---|---|---|---|---|---|
| low | 823 ($0.025) | 664 ($0.020) | 504 ($0.015) | 1667 ($0.050) | 1558 ($0.047) |
| medium | 1449 ($0.043) | 1132 ($0.034) | 924 ($0.028) | 2944 ($0.088) | 2855 ($0.086) |
| high | 1756 ($0.053) | 1372 ($0.041) | 1078 ($0.032) | 3568 ($0.107) | 3336 ($0.100) |
| xhigh | 3122 ($0.094) | 2459 ($0.074) | 1917 ($0.058) | 6343 ($0.190) | 5930 ($0.178) |
| max | 7024 ($0.211) | 5488 ($0.165) | 4312 ($0.129) | 14272 ($0.428) | 13342 ($0.400) |

**gpt-image-2.5 (Sunburst and Flare):** same as 2.6 at high, xhigh and max. Lower at the bottom two levels:

| quality | 1024x1024 | 1536x1024 | 1536x864 | 2048x2048 | 3840x2160 |
|---|---|---|---|---|---|
| low | 196 ($0.006) | 158 ($0.005) | 120 ($0.004) | 397 ($0.012) | 371 ($0.011) |
| medium | 439 ($0.013) | 343 ($0.010) | 280 ($0.008) | 892 ($0.027) | 865 ($0.026) |

**Legacy fixed tables, for models before gpt-image-2:**

| Quality | 1024x1024 | 1024x1536 | 1536x1024 |
|---|---|---|---|
| Low | 272 tokens | 408 tokens | 400 tokens |
| Medium | 1056 tokens | 1584 tokens | 1568 tokens |
| High | 4160 tokens | 6240 tokens | 6208 tokens |

Legacy per-image prices at 1024² for low/medium/high:
- 1.5: $0.009 / $0.034 / $0.133
- 1-mini: $0.005 / $0.011 / $0.036

Caveats on the estimates:
- The calculator is an estimate. The guide says "Use the response's `usage` to measure token consumption". The 2.5 model page even says "The GPT Image 2 calculator does not estimate GPT-Image-2.5 token consumption" **[CONFLICT]**, although the current calculator does include 2.5.
- `auto` quality and size cannot be estimated in advance.
- Text input is cheap: a 300-token prompt costs about $0.0015.
- Edits add input image tokens. No 2.x formula is published, and inputs are always processed at high fidelity, so read `usage.input_tokens_details.image_tokens`. **[UNVERIFIED]** magnitude.

**Budget note for the $5 credit:**
- 2.6 at medium, 1024²: about $0.045 per image, roughly 110 images.
- 2.6 at low is **not** cheap, because of the 4.2× multiplier: about $0.025.
- The cheapest current option is `gpt-image-2.5-flare` at `quality:"low"`, about $0.006 per image.
- Avoid `max` and large sizes by default.
- The plugin should log `usage` and the computed cost per call, and keep a running total.

## 5. Errors and rate limits

All errors use the standard envelope `{"error": {"message", "type", "param", "code"}}`. Log the `x-request-id` response header.

**Moderation block** (guide; HTTP 400, raised as Python `BadRequestError`):

```json
{ "error": { "type": "image_generation_user_error", "code": "moderation_blocked",
    "moderation_details": { "moderation_stage": "input", "categories": ["harassment"] } } }
```

- `moderation_stage` is one of `input`, `output` or `unknown`.
- `categories` holds coarse labels such as `harassment`, `self-harm`, `sexual` and `violence`. "New category values may be added over time."
- `error.code` is "the stable discriminator".
- Do **not** auto-retry `image_generation_user_error`. Change the prompt or inputs first. That error type also covers other user-correctable failures, not only moderation.

**Rate and billing errors** (error-codes page):

| Status | Code / type | Meaning | Retry? |
|---|---|---|---|
| 429 | no code given, "Rate limit reached for requests" | Too many requests | Yes, with backoff, honouring `Retry-After` |
| 429 | `rate_limit_error` / `slow_down` | Ramped up too fast | Yes, with backoff |
| 429 | `credit_balance_exhausted` (type may be `insufficient_quota`) | Prepaid credits used up | **No.** Tell the user to add credits. This is the likely error once the $5 runs out. |
| 429 | `organization_spend_limit_exceeded`, `project_spend_limit_exceeded`, `organization_usage_limit_exceeded` | A spend or usage limit was hit | No |
| 503 | `service_unavailable_error` / `server_is_overloaded` | Model overloaded | Yes, honouring `Retry-After` |
| 500 | | Server error | Yes, after a short wait |
| 401 | | Bad API key | No |
| 403 | | Country not supported | No |

On retries:
- Treat `Retry-After` (in seconds) as a minimum and add jitter.
- Cap both the number of attempts and the total retry time.
- The guide says "Complex prompts may take up to 2 minutes", so set the urllib timeout to at least 180 s.

Rate-limit response headers: `x-ratelimit-limit-requests`, `x-ratelimit-remaining-requests`, `x-ratelimit-reset-requests`, `x-ratelimit-limit-tokens`, `x-ratelimit-remaining-tokens`, `x-ratelimit-reset-tokens`, plus `x-ratelimit-*-project-tokens` when a project limit applies.

**Usage tiers** (rate-limits page): Free, then Build ($5 in total credit purchases), Launch ($100) and Grow ($500). A user who has bought $5 of credit is **Build** tier.

Image-model rate limits from the model pages:

| Tier | IPM | TPM |
|---|---|---|
| Build | 20 | 250,000 |
| Launch | 150 | 3,000,000 |
| Grow | 250 | 8,000,000 |

- These figures apply to 2.5-sunburst, 2, 1.5, 1-mini and chatgpt-image-latest.
- **The 2.6 pages publish no numbers.** They say "Rate limits vary by usage tier and account", so check https://platform.openai.com/settings/organization/limits. **[UNVERIFIED]** 2.6 limits.
- Free-tier image limits are not published. **[UNVERIFIED]** whether image models work on the Free tier at all.

**Org-verification error.** No official page gives the text. The OpenAI community forum reports this 403 for `gpt-image-1`:

```
403 {"error": {"message": "Your organization must be verified to use the model `gpt-image-1`. Please go to: https://platform.openai.com/settings/organization/general and click on Verify Organization. If you just verified, it can take up to 15 minutes for access to propagate.", "type": "invalid_request_error", "param": null, "code": null}}
```

**[UNVERIFIED]** that 2.x models return the same message. To detect it, match HTTP 403 plus "must be verified" in `message`. The forum also reports that **streaming** was separately gated behind verification. **[UNVERIFIED]**

**Model access:** when a model is missing, the API returns `model_not_found`. The rate-limits page adds that "Meeting a usage-tier threshold doesn't grant access to every model."

## 6. Organization verification

The guide says: "To ensure these models are used responsibly, you may need to complete the API Organization Verification from your developer console before using GPT Image models." The console page is https://platform.openai.com/settings/organization/general, and the help article is https://help.openai.com/en/articles/10910291-api-organization-verification.

- "May need to" means the docs do not say it is always required for 2.x. **Assume it is required**, and handle the 403 gracefully with a message that links to the settings page.
- Steps, from the help article and the forum:
  1. Sign in to the organization.
  2. Go to Settings → Organization → General → "Verify Organization".
  3. Complete identity verification: an original physical government ID (passport, driver's licence or national ID; no photocopies or screenshots) plus a selfie if asked.
  4. Each person can verify only one organization.
  5. Access "can take time" to propagate. The API error itself says up to 15 minutes.
- The help article names no models, no processing time and no error text.
- Forum reports describe cases where newly created keys failed after verification while older keys worked. **[UNVERIFIED]**

## 7. Official prompting guidance (brief)

From the Image prompting guide, Overview and Prompting fundamentals:
- Describe the subject, composition, style and constraints. For complex requests, use labeled sections such as scene, subject, details and constraints.
- Put exact text in quotes and describe its position and typography. Spell unusual words letter by letter. Ask for "no extra text", then check the spelling. Use medium or high quality for small text.
- For edits, write "change only X" and list what to preserve. Number the reference images and state each one's role, for example "edit the first image by adding this element from the second image".
- Iterate one change at a time: feed the previous output back as the edit input and restate the critical constraints.
- Use `quality:"low"` for drafts. When tuning, change either quality or complexity, not both at once. Leave complexity at its default first.
- The tool guide adds: "Image generation works best when you use terms like `draw` or `edit` in your prompt."
- Known limitations: latency up to 2 minutes, imperfect text placement, character drift across generations, and weak precise layout control.

---

## 8. Cheat sheet: curl

```bash
# Generate (JSON). The response is always base64.
curl -s https://api.openai.com/v1/images/generations \
  -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"gpt-image-2.6-flare","prompt":"A cute baby sea otter","size":"1024x1024",
       "quality":"medium","output_format":"png"}' \
  | jq -r '.data[0].b64_json' | base64 --decode > otter.png

# Transparent sticker
#   -d '{"model":"gpt-image-2.6-flare","prompt":"...","background":"transparent","output_format":"png"}'

# Edit (multipart), several reference images
curl -s -X POST https://api.openai.com/v1/images/edits \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F "model=gpt-image-2.6-flare" \
  -F "image[]=@body-lotion.png" -F "image[]=@soap.png" \
  -F 'prompt=Create a lovely gift basket with these items in it' \
  | jq -r '.data[0].b64_json' | base64 --decode > basket.png

# Edit (JSON) with a data URL. Easiest from stdlib Python.
curl -s https://api.openai.com/v1/images/edits \
  -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"gpt-image-2.6-flare","prompt":"Add a watercolor effect to this image",
       "images":[{"image_url":"data:image/png;base64,iVBOR..."}],"quality":"high","size":"1024x1024"}'

# Markup-guided edit (Images API only; cannot be combined with mask)
curl --fail -sS https://api.openai.com/v1/images/edits -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F model=gpt-image-2.6-flare -F quality=medium \
  -F 'image=@kitchen.webp;type=image/webp' \
  -F 'markup=@overlay.png;type=image/png' \
  -F 'prompt=Recolor the striped vase inside the red circle to solid cobalt blue ceramic. Keep everything else unchanged. Remove the red circle.' \
  | jq -er '.data[0].b64_json' | base64 --decode > vase.png

# Mask edit
curl -s -X POST https://api.openai.com/v1/images/edits -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F "model=gpt-image-2.6-sunburst" -F "mask=@mask.png" -F "image[]=@sunlit_lounge.png" \
  -F 'prompt=A sunlit indoor lounge area with a pool containing a flamingo'

# SVG (generations only, n=1)
#   -d '{"model":"gpt-image-2.6-flare","prompt":"Flat bakery logo ...","output_format":"svg","n":1}'
#   then: jq -r '.data[0].b64_json' | base64 --decode > logo.svg

# GIF
#   -d '{"model":"gpt-image-2.6-sunburst","prompt":"looping ...","output_format":"gif","frame_count":9,"frame_duration_ms":200}'

# Streaming
curl -N https://api.openai.com/v1/images/generations -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-image-2.6-flare","prompt":"A cute baby sea otter","stream":true,"partial_images":2}'

# Responses API (multi-turn); shown for reference only
curl https://api.openai.com/v1/responses -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"gpt-6.2-astra","input":"Generate an image of a gray tabby cat hugging an otter",
       "tools":[{"type":"image_generation","model":"gpt-image-2.6-sunburst","quality":"medium"}]}'
# Follow-up: same call with "previous_response_id":"resp_...","input":"Now make it look realistic"
# Image: response.output[i] where type == "image_generation_call" -> .result (base64)
```

## 9. Notes for the stdlib (urllib) client

1. **Generate:** `urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")`, then `urlopen(req, timeout=300)`.
2. **Edit:** use JSON `images: [{"image_url": "data:<mime>;base64,<b64>"}]` to avoid writing a multipart encoder. Use the same shape for `mask` and `markup`. The data-URL limit is 20,971,520 chars, so use multipart or the Files API for anything larger.
3. **On `HTTPError`:** read `e.code`, `e.headers.get("Retry-After")` and `e.headers.get("x-request-id")`, then `json.loads(e.read())["error"]`. Branch on `error.code`:
   - `moderation_blocked`: report the stage and categories, do not retry.
   - `credit_balance_exhausted`, `insufficient_quota` or the other spend codes: stop and tell the user.
   - A 403 whose message contains "must be verified": print the verification link.
   - Other 429s and all 5xx: back off, at most 3 tries.
4. **Saving the output:** decode with `base64.b64decode(data[0]["b64_json"])`. Take the extension from the response's `output_format`.
5. **Cost:** print `usage` and the computed cost (§4) after every call, and append both to a local JSON ledger so Claude can report the running spend.
6. **Pre-flight validation:**
   - `size` multiple of 16, aspect between 1:3 and 3:1, edges ≤3840, pixels between 655,360 and 8,294,400.
   - `transparent` only with png or webp.
   - `output_compression` only with jpeg or webp.
   - `svg` only with n=1 and no stream, and not on edits.
   - `markup` and `mask` never together.
   - `input_fidelity` omitted for 2.x.
7. **Defaults:** `gpt-image-2.6-flare`, `quality:"medium"` (or `low` on 2.5-flare for drafts), `size:"1024x1024"`, `png`. Do not use deprecated ids, because they stop working on Dec 1, 2026.

## Open questions / unverified

- Whether org verification is always required for 2.5 and 2.6. The docs say only "may need to". The exact 2.x 403 text is also unconfirmed.
- Rate limits for 2.6 and for the Free tier.
- Input image token counts for edits on 2.x. There is no formula, so measure them through `usage`.
- Whether 2.6 is officially supported in the Responses tool. The reference says yes and the guides say nothing.
- Which `complexity` values 2.5 supports.
- Whether 2.6 officially accepts `xhigh`/`max` and custom sizes. The guide says yes, while the reference text names only 2.5.
- Whether SVG and GIF need per-project access. The reference mentions "project access" and a "GIF preview".
- Whether `usage` includes partial-image tokens.
- Which model authors SVGs, and its rates.
