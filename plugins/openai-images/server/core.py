"""Pure logic for the openai-images MCP server: config, cost, validation, errors, files.

No network and no MCP here, so all of it can be tested directly.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

DEFAULT_MODEL = "gpt-image-2.5-sunburst"
DEFAULT_QUALITY = "medium"
DEFAULT_SIZE = "1024x1024"
DEFAULT_MAX_COST = 0.10
DEFAULT_DATA_DIR = "~/.claude/plugins/data/openai-images"
MAX_N = 4
INPUT_ALLOWANCE_USD = 0.05  # per input image and per mask; OpenAI publishes no 2.x input formula

# USD per token. Same for every gpt-image-2* id; unknown ids are priced the same way.
PRICES = {"text_in": 5e-6, "image_in": 8e-6, "image_out": 30e-6}


# ---------------------------------------------------------------- config

@dataclass(frozen=True)
class Config:
    api_key: str | None
    default_model: str
    default_quality: str
    max_cost_per_call: float
    project_dir: Path
    data_dir: Path


def _env(env: Mapping[str, str], name: str) -> str:
    """The stripped value, or "" when unset, blank, or an unsubstituted ${...} placeholder."""
    value = (env.get(name) or "").strip()
    if value.startswith("${") and value.endswith("}"):
        return ""
    return value


def load_config(env: Mapping[str, str], cwd: Path) -> Config:
    cost_raw = _env(env, "OPENAI_IMAGES_MAX_COST_PER_CALL")
    try:
        max_cost = float(cost_raw)
    except ValueError:
        max_cost = DEFAULT_MAX_COST
    if not math.isfinite(max_cost) or max_cost <= 0:
        max_cost = DEFAULT_MAX_COST
    project = _env(env, "CLAUDE_PROJECT_DIR")
    data = _env(env, "OPENAI_IMAGES_DATA_DIR")
    return Config(
        api_key=_env(env, "OPENAI_IMAGES_API_KEY") or None,
        default_model=_env(env, "OPENAI_IMAGES_DEFAULT_MODEL") or DEFAULT_MODEL,
        default_quality=_env(env, "OPENAI_IMAGES_DEFAULT_QUALITY") or DEFAULT_QUALITY,
        max_cost_per_call=max_cost,
        project_dir=Path(project or cwd).expanduser().resolve(),
        data_dir=Path(data or DEFAULT_DATA_DIR).expanduser(),
    )


# ---------------------------------------------------------------- cost

# Base cells per quality, from the docs' token calculator (openai_api.md §4).
_BASES = {
    "2": {"low": 16, "medium": 48, "high": 96},
    "2.5": {"low": 16, "medium": 24, "high": 48, "xhigh": 64, "max": 96},
    "2.6": {"low": 16, "medium": 24, "high": 48, "xhigh": 64, "max": 96},
}
_MULT_2_6 = {"low": 4.2, "medium": 3.3}
_GPT_IMAGE_2 = re.compile(r"gpt-image-2(-\d{4}-\d{2}-\d{2})?")


def model_family(model: str) -> str:
    """'2.5', '2' or '2.6'. Anything not known to be cheaper is estimated as 2.6 (the most expensive)."""
    m = model.strip().lower()
    if m.startswith("gpt-image-2.5"):
        return "2.5"
    if _GPT_IMAGE_2.fullmatch(m):
        return "2"
    return "2.6"


def estimate_output_tokens(model: str, quality: str, width: int, height: int) -> int:
    family = model_family(model)
    q = quality.strip().lower()
    bases = _BASES[family]
    if q not in bases:  # a level this family doesn't list: use the most expensive one listed anywhere
        base, q = 96, "max"
    else:
        base = bases[q]
    long_edge, short_edge = max(width, height), min(width, height)
    d = round(base / (long_edge / short_edge))  # Python's round is half-to-even, like the calculator
    grid = base * d
    tokens = math.ceil(grid * (2_000_000 + width * height) / 4_000_000)
    if family == "2.6":
        tokens = round(tokens * _MULT_2_6.get(q, 1))
    return tokens


@dataclass
class Estimate:
    output_usd: float
    input_allowance_usd: float
    total_usd: float
    notes: list[str] = field(default_factory=list)


def estimate_cost(model: str, quality: str, size: str, n: int, input_images: int) -> Estimate:
    notes: list[str] = []
    q = quality.strip().lower()
    if q == "auto":
        q = "high"
        notes.append("quality auto is estimated as high; OpenAI picks the real level")
    elif q not in _BASES["2.6"] and q not in _BASES[model_family(model)]:
        notes.append(f"quality {quality!r} is unknown here and is estimated as max")
    dims = parse_size(size)
    if dims is None:
        dims = (1024, 1024)
        notes.append("size auto is estimated as 1024x1024; OpenAI picks the real size")
    if model_family(model) == "2.6" and not model.strip().lower().startswith("gpt-image-2.6"):
        notes.append(f"{model} is not a known model; estimated at gpt-image-2.6 rates, the most expensive")
    output = estimate_output_tokens(model, q, *dims) * PRICES["image_out"] * n
    allowance = INPUT_ALLOWANCE_USD * input_images
    if input_images:
        notes.append(f"includes an allowance of ${INPUT_ALLOWANCE_USD:.2f} per input image and mask "
                     f"({input_images}); the real input cost is in the usage after the call")
    return Estimate(output_usd=output, input_allowance_usd=allowance, total_usd=output + allowance, notes=notes)


def cost_from_usage(model: str, usage: dict) -> float:
    """Real cost from the response's usage. Missing breakdowns are priced at the higher rate."""
    usage = usage or {}
    inp = usage.get("input_tokens_details") or {}
    out = usage.get("output_tokens_details") or {}
    if inp:
        cost_in = (inp.get("text_tokens", 0) * PRICES["text_in"]
                   + inp.get("image_tokens", 0) * PRICES["image_in"])
    else:
        cost_in = usage.get("input_tokens", 0) * PRICES["image_in"]
    image_out = out.get("image_tokens", usage.get("output_tokens", 0))
    return cost_in + image_out * PRICES["image_out"]


# ---------------------------------------------------------------- errors

BILLING_URL = "https://platform.openai.com/settings/organization/billing"
VERIFY_URL = "https://platform.openai.com/settings/organization/general"
USAGE_URL = "https://platform.openai.com/usage"
_QUOTA_WORDS = ("quota", "credit", "spend_limit", "usage_limit", "billing")
_KEYLIKE = re.compile(r"sk-[A-Za-z0-9_\-*.]{3,}")


def scrub(text: str, secret: str | None = None) -> str:
    """Remove anything that looks like an API key (and the given secret) from text."""
    if secret:
        text = text.replace(secret, "[key]")
    return _KEYLIKE.sub("sk-[hidden]", text)


class ImagesError(Exception):
    """A failure with a stable code, a plain message and what to do next."""

    def __init__(self, code: str, message: str, next_step: str, retryable: bool = False,
                 retry_after: float | None = None):
        super().__init__(code, message, next_step)
        self.code = code
        self.message = scrub(message)
        self.next_step = scrub(next_step)
        self.retryable = retryable
        self.retry_after = retry_after

    def __str__(self) -> str:
        return f"{self.code}: {self.message} Next: {self.next_step}"


def _retry_after(headers: Mapping[str, str]) -> float | None:
    raw = None
    for k, v in headers.items():
        if k.lower() == "retry-after":
            raw = v
    try:
        value = float(raw) if raw is not None else None
    except ValueError:  # an HTTP date; the default back-off is used instead
        return None
    if value is None or not math.isfinite(value) or value < 0:
        return None
    return value


def classify_error(status: int, body: dict | None, headers: Mapping[str, str]) -> ImagesError:
    err = (body or {}).get("error") if isinstance(body, dict) else None
    err = err if isinstance(err, dict) else {}
    code = str(err.get("code") or "")
    etype = str(err.get("type") or "")
    msg = str(err.get("message") or "").strip()
    said = f" OpenAI said: {msg}" if msg else ""
    retry_after = _retry_after(headers)

    if status == 401:
        return ImagesError("bad_api_key", "OpenAI rejected the API key.",
                           "Run /plugin configure openai-images and enter a valid key.")
    if status == 403 and "must be verified" in msg.lower():
        return ImagesError("org_verification_required",
                           "Your OpenAI organization must be verified to use this model.",
                           f"Verify it at {VERIFY_URL} (Verify Organization); access can take up to 15 minutes "
                           "to start working after verifying.")
    if code == "moderation_blocked":
        details = err.get("moderation_details") or (body or {}).get("moderation_details") or {}
        stage = details.get("moderation_stage") or "unknown"
        cats = ", ".join(str(c) for c in details.get("categories") or []) or "none given"
        return ImagesError("moderation_blocked",
                           f"OpenAI's safety system blocked the request at the {stage} stage "
                           f"(categories: {cats}).",
                           "Rephrase the prompt or change the inputs; do not resend it unchanged.")
    if code == "model_not_found" or status == 404:
        return ImagesError("model_not_found", f"The model is not available to this account.{said}",
                           "Use another model id, or check which models the account can use.")
    if status == 429:
        if any(w in f"{code} {etype}".lower() for w in _QUOTA_WORDS):
            return ImagesError("out_of_credit", f"The OpenAI account is out of credit or hit a spend limit.{said}",
                               f"Add credit or raise the limit at {BILLING_URL}; do not retry until then.")
        wait = f" OpenAI asked to wait {retry_after:g} s." if retry_after is not None else ""
        return ImagesError("rate_limited", f"OpenAI's rate limit was reached.{wait}",
                           "Wait a minute, then try again.", retryable=True, retry_after=retry_after)
    if status >= 500:
        return ImagesError("openai_unavailable", f"OpenAI returned HTTP {status}.{said}",
                           "Try again later.", retryable=status in (500, 503), retry_after=retry_after)
    return ImagesError("invalid_request", f"OpenAI refused the request (HTTP {status}).{said}",
                       "Fix the request using OpenAI's message; do not resend it unchanged.")


# ---------------------------------------------------------------- validation

def _invalid(message: str) -> ImagesError:
    return ImagesError("invalid_request", message, "Fix the parameter and call again.")


def parse_size(size: str) -> tuple[int, int] | None:
    s = size.strip().lower()
    if s == "auto":
        return None
    m = re.fullmatch(r"(\d+)x(\d+)", s)
    if not m:
        raise _invalid(f"size {size!r} is not 'auto' or WIDTHxHEIGHT, e.g. 1536x1024.")
    return int(m.group(1)), int(m.group(2))


def validate_request(*, size: str, background: str, output_format: str, n: int) -> None:
    """Check only what is certain; everything else goes to the API."""
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= MAX_N:
        raise _invalid(f"n must be 1 to {MAX_N}, got {n!r}.")
    if background.strip().lower() == "transparent" and output_format.strip().lower() not in ("png", "webp"):
        raise _invalid(f"background transparent needs output_format png or webp, not {output_format!r}.")
    dims = parse_size(size)
    if dims is None:
        return
    w, h = dims
    if w <= 0 or h <= 0 or w % 16 or h % 16:
        raise _invalid(f"size {size}: width and height must be multiples of 16.")
    if max(w, h) > 3840:
        raise _invalid(f"size {size}: no edge may be larger than 3840 px.")
    if max(w, h) > 3 * min(w, h):
        raise _invalid(f"size {size}: the aspect ratio must be between 1:3 and 3:1.")
    if not 655_360 <= w * h <= 8_294_400:
        raise _invalid(f"size {size}: total pixels must be between 655,360 and 8,294,400 "
                       f"(1024x1024 is fine; 512x512 is too small).")
