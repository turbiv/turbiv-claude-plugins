#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp==2.3.0", "httpx==0.28.1"]
# ///
"""openai-images MCP server: generate and edit images with OpenAI's GPT Image models.

Run with `uv run --script openai_images.py` (stdio). The API key comes only from OPENAI_IMAGES_API_KEY; the
generic OPENAI_* variables are ignored, and only https://api.openai.com/v1 is ever called.
"""
import base64
import binascii
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent

import core
from core import ImagesError

API_BASE = "https://api.openai.com/v1"
TIMEOUT_S = 180.0
MAX_ATTEMPTS = 3            # one try + at most 2 retries, only for errors that are certainly not billed
BACKOFF_S = (2.0, 8.0)      # used when OpenAI sends no Retry-After
MAX_WAIT_S = 60.0           # a longer Retry-After is reported instead of waited for
MAX_INPUT_IMAGES = 16
MAX_DATA_URL_CHARS = 20_971_520
DEFAULT_OUTPUT_DIR = "generated-images"

INSTRUCTIONS = (
    "Generates and edits images with OpenAI's GPT Image models and saves them in the project. Each "
    "generate_image/edit_image call costs money (default about $0.013 per image); image_status is free. "
    "After a call, Read the saved file to check it. Errors start with a stable code and say what to do next.")


class _Images:
    """The tool logic, separate from MCP so errors and results stay plain Python."""

    def __init__(self, config: core.Config, http: httpx.Client, sleep: Callable[[float], None],
                 now: Callable[[], datetime]):
        self.config = config
        self.http = http
        self.sleep = sleep
        self.now = now
        self.session_id = uuid.uuid4().hex  # the session total is per server process

    # ------------------------------------------------------------ status

    def status(self) -> dict:
        session, total = core.spend_totals(self.config.data_dir, self.session_id)
        model = self.config.default_model
        return {
            "key_set": bool(self.config.api_key),
            "defaults": {"model": model, "quality": self.config.default_quality, "size": core.DEFAULT_SIZE,
                         "n": 1, "background": "auto", "output_format": "png"},
            "max_cost_per_call": self.config.max_cost_per_call,
            "output_dir": str(self.config.project_dir / DEFAULT_OUTPUT_DIR),
            "spent_session_usd": round(session, 6),
            "spent_total_usd": round(total, 6),
            "prices": {
                "text_in_per_token": core.PRICES["text_in"],
                "image_in_per_token": core.PRICES["image_in"],
                "image_out_per_token": core.PRICES["image_out"],
                "input_image_allowance_usd": core.INPUT_ALLOWANCE_USD,
                "default_model_per_image_1024x1024_usd": {
                    q: round(core.estimate_cost(model, q, "1024x1024", 1, 0).total_usd, 4)
                    for q in ("low", "medium", "high", "xhigh", "max")},
                "note": "Estimates use OpenAI's published token formula; unknown models are estimated at "
                        "gpt-image-2.6 rates. The real cost comes from the response's usage.",
            },
        }

    # ------------------------------------------------------------ generate / edit

    def run(self, endpoint: str, prompt: str, *, model: str | None, size: str, quality: str | None,
            background: str, output_format: str, n: int, filename: str | None, output_dir: str | None,
            allow_expensive: bool, images: list[str] | None = None, mask: str | None = None) -> dict:
        cfg = self.config
        if not cfg.api_key:
            raise ImagesError("no_api_key", "No OpenAI API key is set for the openai-images plugin.",
                              "Ask the user to run /plugin configure openai-images and enter the key there "
                              "(never in the chat).")
        if not prompt or not prompt.strip():
            raise ImagesError("invalid_request", "The prompt is empty.", "Write a prompt and call again.")
        model = (model or "").strip() or cfg.default_model
        quality = (quality or "").strip() or cfg.default_quality
        core.validate_request(size=size, background=background, output_format=output_format, n=n)
        is_edit = endpoint == "edits"
        if is_edit and not 1 <= len(images or []) <= MAX_INPUT_IMAGES:
            raise ImagesError("invalid_request", f"images must list 1 to {MAX_INPUT_IMAGES} files, "
                              f"got {len(images or [])}.", "The first image is edited; the rest are references.")
        out_dir = core.resolve_inside(cfg.project_dir, output_dir or DEFAULT_OUTPUT_DIR)
        inputs = [core.check_input_image(cfg.project_dir, p) for p in images or []]
        mask_path = core.check_input_image(cfg.project_dir, mask) if mask else None

        estimate = core.estimate_cost(model, quality, size, n, len(inputs) + (1 if mask_path else 0))
        if estimate.total_usd > cfg.max_cost_per_call and not allow_expensive:
            raise ImagesError(
                "over_cost_cap",
                f"This call is estimated at ${estimate.total_usd:.3f} (output ${estimate.output_usd:.3f} for "
                f"{n} image(s) + input allowance ${estimate.input_allowance_usd:.2f}), above the per-call cap "
                f"of ${cfg.max_cost_per_call:.2f}.",
                "Ask the user whether to spend that; only if they agree, call again with allow_expensive: true.")

        body: dict = {"model": model, "prompt": prompt, "size": size, "quality": quality, "n": n,
                      "output_format": output_format}
        if background != "auto":
            body["background"] = background
        settings_sent = {k: v for k, v in body.items() if k != "prompt"}
        if is_edit:
            body["images"] = [{"image_url": self._data_url(p)} for p in inputs]
            settings_sent["images"] = [str(p) for p in inputs]
            if mask_path:
                body["mask"] = {"image_url": self._data_url(mask_path)}
                settings_sent["mask"] = str(mask_path)

        resp = self._post(endpoint, body)
        return self._save(resp, prompt=prompt, model=model, size=size, output_format=output_format, n=n,
                          filename=filename, out_dir=out_dir, estimate=estimate, settings_sent=settings_sent,
                          endpoint=endpoint, inputs=inputs, mask_path=mask_path)

    @staticmethod
    def _data_url(path: Path) -> str:
        data = path.read_bytes()
        url = f"data:{core.image_mime(data)};base64,{base64.b64encode(data).decode()}"
        if len(url) > MAX_DATA_URL_CHARS:
            raise ImagesError("invalid_request", f"{path} is too large to send inline (about 15 MB at most).",
                              "Use a smaller or more compressed copy of the image.")
        return url

    def _post(self, endpoint: str, body: dict) -> httpx.Response:
        url = f"{API_BASE}/images/{endpoint}"
        headers = {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"}
        payload = json.dumps(body).encode()
        maybe_billed = ImagesError(
            "timeout_maybe_billed",
            "OpenAI did not answer in time, or the connection broke after the request was sent; the image may "
            "still have been made and billed.",
            f"Check the usage page ({core.USAGE_URL}) before trying again; do not retry automatically.")
        for attempt in range(MAX_ATTEMPTS):
            try:
                resp = self.http.post(url, content=payload, headers=headers, timeout=TIMEOUT_S)
            except (httpx.ConnectError, httpx.ConnectTimeout):
                # The request never left this machine, so it cannot have been billed.
                err = ImagesError("openai_unavailable", "Could not connect to api.openai.com.",
                                  "Check the network connection, then try again.", retryable=True)
            except (httpx.TimeoutException, httpx.TransportError):
                raise maybe_billed from None
            else:
                if resp.status_code == 200:
                    return resp
                try:
                    data = resp.json()
                except ValueError:
                    data = None
                err = core.classify_error(resp.status_code, data, resp.headers)
            if not err.retryable or attempt == MAX_ATTEMPTS - 1:
                raise err
            wait = err.retry_after if err.retry_after is not None else BACKOFF_S[attempt]
            if wait > MAX_WAIT_S:
                raise err
            self.sleep(wait)
        raise AssertionError("unreachable")

    def _save(self, resp: httpx.Response, *, prompt, model, size, output_format, n, filename, out_dir,
              estimate, settings_sent, endpoint, inputs, mask_path) -> dict:
        try:
            payload = resp.json()
            blobs = [base64.b64decode(item["b64_json"], validate=True) for item in payload["data"]]
        except (ValueError, KeyError, TypeError, binascii.Error):
            blobs, payload = [], None
        if not blobs:
            raise ImagesError("openai_unavailable",
                              "OpenAI answered without an image; the call may still have been billed.",
                              f"Check the usage page ({core.USAGE_URL}), then try again.")
        request_id = resp.headers.get("x-request-id")
        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else None
        applied = {k: payload.get(k) for k in ("size", "quality", "background", "output_format")}
        warnings = list(estimate.notes)
        if usage:
            cost = core.cost_from_usage(model, usage)
        else:
            cost = estimate.total_usd
            warnings.append("OpenAI sent no usage, so the cost shown is the estimate.")
        if cost > 1.5 * estimate.total_usd:
            warnings.append(f"The real cost ${cost:.4f} is more than 1.5x the estimate ${estimate.total_usd:.4f}.")
        if len(blobs) != n:
            warnings.append(f"Asked for {n} image(s), got {len(blobs)}.")

        now = self.now()
        want_dims = core.parse_size(size)
        want_fmt = {"jpg": "jpeg"}.get(output_format.lower(), output_format.lower())
        files, saved = [], []
        for i, blob in enumerate(blobs):
            fmt, width, height = core.image_info(blob)
            if fmt == "unknown":
                ext = re.sub(r"[^a-z0-9]", "", str(applied["output_format"] or output_format).lower()) or "bin"
            else:
                ext = {"jpeg": "jpg"}.get(fmt, fmt)
                if fmt != want_fmt:
                    warnings.append(f"Image {i + 1} is {fmt}, not the requested {output_format}.")
            if want_dims and fmt != "unknown" and (width, height) != want_dims:
                warnings.append(f"Image {i + 1} is {width}x{height}, not the requested {size}.")
            while True:  # another call may take the name between the check and the write
                path = core.output_path(out_dir, filename, prompt, ext, now)
                try:
                    core.write_new(path, blob)
                    break
                except FileExistsError:
                    continue
            record = {"created_at": now.isoformat(timespec="seconds"), "tool": f"{endpoint}", "prompt": prompt,
                      "model": model, "settings_sent": settings_sent, "settings_applied": applied,
                      "usage": usage, "cost_usd": round(cost, 6), "estimate_usd": round(estimate.total_usd, 6),
                      "request_id": request_id, "image": {"index": i + 1, "of": len(blobs), "format": fmt,
                                                          "width": width, "height": height,
                                                          "bytes": len(blob)}}
            if inputs:
                record["inputs"] = [str(p) for p in inputs]
            if mask_path:
                record["mask"] = str(mask_path)
            try:
                sidecar = str(core.write_sidecar(path, record))
            except OSError as e:
                sidecar = None
                warnings.append(f"Could not write the sidecar for {path.name}: {e.strerror or e}.")
            saved.append(str(path))
            files.append({"path": str(path), "sidecar": sidecar, "width": width, "height": height,
                          "bytes": len(blob)})

        try:
            core.append_spend(self.config.data_dir, {
                "ts": now.isoformat(timespec="seconds"), "session": self.session_id, "tool": endpoint,
                "model": model, "cost_usd": round(cost, 6), "estimate_usd": round(estimate.total_usd, 6),
                "usage": usage, "request_id": request_id, "files": saved})
        except OSError as e:
            warnings.append(f"Could not write the spend log: {e.strerror or e}; totals may be low.")
        session, total = core.spend_totals(self.config.data_dir, self.session_id)
        what = "the image" if len(saved) == 1 else "the images"
        return {"files": files, "model": model, "settings_sent": settings_sent, "settings_applied": applied,
                "estimate_usd": round(estimate.total_usd, 6), "cost_usd": round(cost, 6),
                "spent_session_usd": round(session, 6), "spent_total_usd": round(total, 6),
                "warnings": warnings, "next_step": f"Read {', '.join(saved)} to check {what} against the request."}


def create_server(config: core.Config, http: httpx.Client, sleep: Callable[[float], None] = time.sleep,
                  now: Callable[[], datetime] = datetime.now) -> MCPServer:
    impl = _Images(config, http, sleep, now)
    server = MCPServer("openai-images", instructions=INSTRUCTIONS)

    def guarded(fn, *args, **kwargs) -> dict[str, Any] | CallToolResult:
        try:
            return fn(*args, **kwargs)
        except ImagesError as e:
            # Not `raise ToolError`: MCP SDK 2.3.0 prefixes a raised ToolError with "Error executing tool
            # <name>: ", and the contract says the text starts with the code. This is the same is_error result.
            text = core.scrub(str(e), config.api_key)
            return CallToolResult(content=[TextContent(type="text", text=text)], is_error=True)

    @server.tool()
    def generate_image(prompt: str, model: str | None = None, size: str = "1024x1024", quality: str | None = None,
                       background: str = "auto", output_format: str = "png", n: int = 1,
                       filename: str | None = None, output_dir: str | None = None,
                       allow_expensive: bool = False) -> dict[str, Any]:
        """Generate new image(s) from a text prompt with OpenAI and save them in the project. Costs money.

        Defaults: the configured model (gpt-image-2.5-sunburst) at the configured quality (medium), 1024x1024,
        png, one image: about $0.013. size is "auto", 1024x1024, 1536x1024, 1024x1536 or a custom WxH
        (multiples of 16, ratio 1:3 to 3:1). quality: low|medium|high|xhigh|max|auto. background:
        auto|opaque|transparent (transparent needs png or webp). n: 1-4. filename: a short slug for the file
        name. output_dir: a folder inside the project (default generated-images/). Calls estimated above the
        per-call cost cap are refused unless allow_expensive is true; set it only after the user agrees.
        Returns the saved file paths, cost and totals; Read the file afterwards to check it."""
        return guarded(impl.run, "generations", prompt, model=model, size=size, quality=quality,
                       background=background, output_format=output_format, n=n, filename=filename,
                       output_dir=output_dir, allow_expensive=allow_expensive)

    @server.tool()
    def edit_image(prompt: str, images: list[str], mask: str | None = None, model: str | None = None,
                   size: str = "1024x1024", quality: str | None = None, background: str = "auto",
                   output_format: str = "png", n: int = 1, filename: str | None = None,
                   output_dir: str | None = None, allow_expensive: bool = False) -> dict[str, Any]:
        """Edit an image with OpenAI, optionally guided by reference images and a mask, and save the result in
        the project. Costs money.

        images: 1-16 PNG/JPEG/WebP files inside the project (paths may be relative to it); images[0] is the one
        edited, the rest are references. mask: optional PNG with transparency marking the area to change.
        Files outside the project are refused: copy them into generated-images/inputs/ first (ask the user).
        Each input image and the mask add a $0.05 allowance to the estimate, so edits with 2+ inputs usually
        exceed the default $0.10 cap and need allow_expensive: true after the user agrees. Other parameters
        are as for generate_image."""
        return guarded(impl.run, "edits", prompt, model=model, size=size, quality=quality,
                       background=background, output_format=output_format, n=n, filename=filename,
                       output_dir=output_dir, allow_expensive=allow_expensive, images=images, mask=mask)

    @server.tool()
    def image_status() -> dict[str, Any]:
        """Free, no network: whether an API key is set (never the key), the defaults, the per-call cost cap,
        the output folder, money spent this session and in total, and the prices used for estimates."""
        return impl.status()

    return server


def main() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)  # no per-request log lines
    config = core.load_config(os.environ, Path.cwd())
    http = httpx.Client(timeout=TIMEOUT_S, follow_redirects=False)
    create_server(config, http).run("stdio")


if __name__ == "__main__":
    main()
