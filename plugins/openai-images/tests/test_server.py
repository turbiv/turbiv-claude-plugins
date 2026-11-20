"""Tests for the MCP server against a fake OpenAI (httpx.MockTransport). No network, no spend."""
import base64
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import httpx
from mcp.client import Client

import fixtures
import core
import openai_images

KEY = "sk-test-key-0123456789"
NOW = datetime(2026, 11, 21, 9, 5, 7)
USAGE = {"input_tokens": 20, "input_tokens_details": {"text_tokens": 20, "image_tokens": 0},
         "output_tokens": 439, "output_tokens_details": {"image_tokens": 439, "text_tokens": 0},
         "total_tokens": 459}
PNG_1024 = fixtures.png_bytes(1024, 1024)


def ok_response(n=1, usage=USAGE, data=PNG_1024, **fields):
    body = {"created": 1, "background": "opaque", "output_format": "png", "quality": "medium",
            "size": "1024x1024", "data": [{"b64_json": base64.b64encode(data).decode()} for _ in range(n)],
            "usage": usage}
    body.update(fields)
    return httpx.Response(200, json=body, headers={"x-request-id": "req_123"})


def error_response(status, code=None, message="m", type_=None, headers=None, **extra):
    return httpx.Response(status, headers=headers or {},
                          json={"error": {"message": message, "type": type_, "param": None, "code": code, **extra}})


class ServerTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(os.path.realpath(self._tmp.name))
        self.proj = root / "proj"
        self.proj.mkdir()
        self.data = root / "data"
        self.requests = []
        self.responses = []
        self.sleeps = []

    def tearDown(self):
        self._tmp.cleanup()

    def handler(self, request):
        self.requests.append(request)
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def server(self, key=KEY, cap=0.10):
        config = core.Config(api_key=key, default_model="gpt-image-2.5-sunburst", default_quality="medium",
                             max_cost_per_call=cap, project_dir=self.proj, data_dir=self.data)
        http = httpx.Client(transport=httpx.MockTransport(self.handler))
        return openai_images.create_server(config, http, sleep=self.sleeps.append, now=lambda: NOW)

    async def call(self, name, args, server=None):
        async with Client(server or self.server()) as c:
            return await c.call_tool(name, args)

    def text(self, result):
        return "".join(getattr(b, "text", "") for b in result.content)

    def assertToolError(self, result, code):
        self.assertTrue(result.is_error, self.text(result))
        self.assertTrue(self.text(result).startswith(f"{code}: "), self.text(result))
        self.assertIn(" Next: ", self.text(result))
        self.assertNotIn(KEY, self.text(result))

    def body(self, i=0):
        return json.loads(self.requests[i].content)

    # ------------------------------------------------------------ generate

    async def test_generate_ok(self):
        self.responses = [ok_response()]
        r = await self.call("generate_image", {"prompt": "A red fox in snow"})
        self.assertFalse(r.is_error, self.text(r))
        sc = r.structured_content
        self.assertEqual(len(sc["files"]), 1)
        f = sc["files"][0]
        path = Path(f["path"])
        self.assertEqual(path.parent, self.proj / "generated-images")
        self.assertEqual(path.name, "20261121-090507-a-red-fox-in-snow.png")
        self.assertEqual(path.read_bytes(), PNG_1024)
        self.assertEqual((f["width"], f["height"], f["bytes"]), (1024, 1024, len(PNG_1024)))
        sidecar = json.loads(Path(f["sidecar"]).read_text())
        self.assertEqual(sidecar["prompt"], "A red fox in snow")
        self.assertEqual(sidecar["request_id"], "req_123")
        self.assertEqual(sidecar["usage"], USAGE)
        self.assertEqual(sc["model"], "gpt-image-2.5-sunburst")
        self.assertEqual(sc["settings_sent"]["quality"], "medium")
        self.assertEqual(sc["settings_applied"], {"size": "1024x1024", "quality": "medium",
                                                  "background": "opaque", "output_format": "png"})
        self.assertEqual(round(sc["estimate_usd"], 3), 0.013)
        self.assertAlmostEqual(sc["cost_usd"], core.cost_from_usage("x", USAGE), places=4)
        self.assertAlmostEqual(sc["spent_session_usd"], sc["cost_usd"], places=4)
        self.assertAlmostEqual(sc["spent_total_usd"], sc["cost_usd"], places=4)
        self.assertEqual(sc["warnings"], [])
        self.assertIn(str(path), sc["next_step"])
        self.assertTrue(sc["next_step"].startswith("Read "))
        # Request: the right URL, the key as a bearer token, the defaults in the body.
        req = self.requests[0]
        self.assertEqual(str(req.url), "https://api.openai.com/v1/images/generations")
        self.assertEqual(req.headers["authorization"], f"Bearer {KEY}")
        body = self.body()
        self.assertEqual(body["model"], "gpt-image-2.5-sunburst")
        self.assertEqual(body["quality"], "medium")
        self.assertEqual(body["size"], "1024x1024")
        self.assertEqual(body["prompt"], "A red fox in snow")
        self.assertEqual(body.get("n", 1), 1)
        self.assertNotIn("input_fidelity", body)
        # No base64 or key anywhere in the result or on disk next to the image.
        out = self.text(r) + json.dumps(sc)
        self.assertNotIn(base64.b64encode(PNG_1024).decode()[:40], out)
        self.assertNotIn("b64", out)
        self.assertNotIn(KEY, out)
        self.assertNotIn(KEY, Path(f["sidecar"]).read_text())
        self.assertNotIn(KEY, (self.data / "spend.jsonl").read_text())

    async def test_generate_params_and_n(self):
        self.responses = [ok_response(n=2, output_format="webp", size="1536x1024", background="transparent")]
        r = await self.call("generate_image", {
            "prompt": "sticker", "model": "gpt-image-2.5-flare", "size": "1536x1024", "quality": "low",
            "background": "transparent", "output_format": "webp", "n": 2, "filename": "My Sticker",
            "output_dir": "art/out"})
        self.assertFalse(r.is_error, self.text(r))
        body = self.body()
        self.assertEqual((body["model"], body["size"], body["quality"], body["background"],
                          body["output_format"], body["n"]),
                         ("gpt-image-2.5-flare", "1536x1024", "low", "transparent", "webp", 2))
        names = [Path(f["path"]).name for f in r.structured_content["files"]]
        # The fake sends PNG bytes: the extension follows the real bytes, and the result warns about both
        # the format and the size not matching the request.
        self.assertEqual(names, ["20261121-090507-my-sticker.png", "20261121-090507-my-sticker-2.png"])
        self.assertTrue(any("webp" in w for w in r.structured_content["warnings"]))
        self.assertTrue(all(Path(f["path"]).parent == self.proj / "art/out" for f in r.structured_content["files"]))
        self.assertTrue(any("1536x1024" in w for w in r.structured_content["warnings"]))

    async def test_never_overwrites(self):
        self.responses = [ok_response(), ok_response()]
        server = self.server()
        a = await self.call("generate_image", {"prompt": "fox", "filename": "fox"}, server)
        b = await self.call("generate_image", {"prompt": "fox", "filename": "fox"}, server)
        pa, pb = a.structured_content["files"][0]["path"], b.structured_content["files"][0]["path"]
        self.assertNotEqual(pa, pb)
        self.assertTrue(Path(pa).exists() and Path(pb).exists())
        self.assertAlmostEqual(b.structured_content["spent_session_usd"], 2 * a.structured_content["cost_usd"],
                               places=4)

    async def test_no_key(self):
        for key in (None, ""):
            r = await self.call("generate_image", {"prompt": "fox"}, self.server(key=key))
            self.assertToolError(r, "no_api_key")
            self.assertIn("/plugin configure openai-images", self.text(r))
        r = await self.call("edit_image", {"prompt": "fox", "images": ["a.png"]}, self.server(key=None))
        self.assertToolError(r, "no_api_key")
        self.assertEqual(self.requests, [])

    async def test_over_cost_cap(self):
        args = {"prompt": "fox", "quality": "high", "n": 2}  # 2 x 1756 tokens x $30/M = $0.105
        r = await self.call("generate_image", args)
        self.assertToolError(r, "over_cost_cap")
        self.assertIn("0.105", self.text(r))
        self.assertIn("0.10", self.text(r))
        self.assertIn("allow_expensive", self.text(r))
        self.assertIn("ask the user", self.text(r).lower())
        self.assertEqual(self.requests, [])
        self.responses = [ok_response(n=2)]
        r = await self.call("generate_image", {**args, "allow_expensive": True})
        self.assertFalse(r.is_error, self.text(r))
        self.assertEqual(len(self.requests), 1)

    async def test_cost_warning_when_far_above_estimate(self):
        self.responses = [ok_response(usage={"input_tokens": 10, "output_tokens": 2000})]
        r = await self.call("generate_image", {"prompt": "fox"})
        self.assertTrue(any("estimate" in w for w in r.structured_content["warnings"]))

    async def test_local_validation_before_network(self):
        cases = [({"prompt": "x", "size": "1000x1000"}, "invalid_request"),
                 ({"prompt": "x", "n": 5}, "invalid_request"),
                 ({"prompt": "x", "background": "transparent", "output_format": "jpeg"}, "invalid_request"),
                 ({"prompt": "x", "output_dir": "../elsewhere"}, "path_outside_project"),
                 ({"prompt": "x", "output_dir": "/tmp"}, "path_outside_project")]
        for args, code in cases:
            self.assertToolError(await self.call("generate_image", args), code)
        self.assertEqual(self.requests, [])

    # ------------------------------------------------------------ edit

    async def test_edit_ok(self):
        (self.proj / "a.png").write_bytes(fixtures.png_bytes(4, 4))
        (self.proj / "refs").mkdir()
        (self.proj / "refs/b.jpg").write_bytes(fixtures.jpeg_bytes())
        (self.proj / "mask.png").write_bytes(fixtures.png_bytes(4, 4))
        self.responses = [ok_response(usage={**USAGE, "input_tokens_details": {"text_tokens": 20,
                                                                               "image_tokens": 3000}})]
        # Two inputs + a mask = $0.15 allowance, over the default $0.10 cap, so this test raises the cap.
        r = await self.call("edit_image", {"prompt": "Make it blue", "images": ["a.png", str(self.proj / "refs/b.jpg")],
                                           "mask": "mask.png"}, self.server(cap=0.5))
        self.assertFalse(r.is_error, self.text(r))
        req = self.requests[0]
        self.assertEqual(str(req.url), "https://api.openai.com/v1/images/edits")
        body = self.body()
        self.assertEqual(len(body["images"]), 2)
        self.assertTrue(body["images"][0]["image_url"].startswith("data:image/png;base64,"))
        self.assertTrue(body["images"][1]["image_url"].startswith("data:image/jpeg;base64,"))
        self.assertEqual(base64.b64decode(body["images"][1]["image_url"].split(",", 1)[1]), fixtures.jpeg_bytes())
        self.assertTrue(body["mask"]["image_url"].startswith("data:image/png;base64,"))
        self.assertNotIn("input_fidelity", body)
        sc = r.structured_content
        self.assertAlmostEqual(sc["estimate_usd"], 0.15 + 439 * 30e-6, places=4)
        self.assertIn("images", sc["settings_sent"])
        self.assertNotIn("base64", json.dumps(sc))
        sidecar = json.loads(Path(sc["files"][0]["sidecar"]).read_text())
        self.assertEqual(sidecar["inputs"], [str(self.proj / "a.png"), str(self.proj / "refs/b.jpg")])
        self.assertEqual(sidecar["mask"], str(self.proj / "mask.png"))
        self.assertNotIn("base64", json.dumps(sidecar))

    async def test_edit_single_input_fits_default_cap(self):
        (self.proj / "a.png").write_bytes(fixtures.png_bytes())
        self.responses = [ok_response()]
        r = await self.call("edit_image", {"prompt": "x", "images": ["a.png"]})
        self.assertFalse(r.is_error, self.text(r))

    async def test_edit_input_errors(self):
        outside = self.proj.parent / "outside.png"
        outside.write_bytes(fixtures.png_bytes())
        (self.proj / "link.png").symlink_to(outside)
        (self.proj / "a.png").write_bytes(fixtures.png_bytes())
        cases = [({"images": ["missing.png"]}, "input_not_found"),
                 ({"images": [str(outside)]}, "path_outside_project"),
                 ({"images": ["link.png"]}, "path_outside_project"),
                 ({"images": ["a.png"], "mask": "../outside.png"}, "path_outside_project"),
                 ({"images": []}, "invalid_request"),
                 ({"images": ["a.png"] * 17, "allow_expensive": True}, "invalid_request"),
                 ({"images": ["https://example.com/x.png"]}, "input_not_found")]
        for args, code in cases:
            self.assertToolError(await self.call("edit_image", {"prompt": "x", **args}), code)
        self.assertEqual(self.requests, [])

    # ------------------------------------------------------------ errors and retries

    async def test_moderation_not_retried(self):
        self.responses = [error_response(400, "moderation_blocked", "Rejected", "image_generation_user_error",
                                         moderation_details={"moderation_stage": "input",
                                                             "categories": ["violence"]})]
        r = await self.call("generate_image", {"prompt": "x"})
        self.assertToolError(r, "moderation_blocked")
        self.assertIn("violence", self.text(r))
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.sleeps, [])

    async def test_quota_429_not_retried(self):
        for code in ("credit_balance_exhausted", "insufficient_quota", "project_spend_limit_exceeded"):
            self.requests.clear()
            self.responses = [error_response(429, code, "You exceeded your current quota.", "insufficient_quota",
                                             headers={"Retry-After": "1"}), ok_response()]
            r = await self.call("generate_image", {"prompt": "x"})
            self.assertToolError(r, "out_of_credit")
            self.assertEqual(len(self.requests), 1, code)
            self.assertEqual(self.sleeps, [])

    async def test_rate_limit_retried_then_ok(self):
        self.responses = [error_response(429, None, "Rate limit reached for requests", "requests",
                                         headers={"Retry-After": "3"}),
                          error_response(503, "server_is_overloaded", "Overloaded"),
                          ok_response()]
        r = await self.call("generate_image", {"prompt": "x"})
        self.assertFalse(r.is_error, self.text(r))
        self.assertEqual(len(self.requests), 3)
        self.assertEqual(self.sleeps, [3.0, 8.0])
        self.assertEqual(len(r.structured_content["files"]), 1)

    async def test_rate_limit_gives_up_after_two_retries(self):
        self.responses = [error_response(429, None, "Rate limit")] * 3 + [ok_response()]
        r = await self.call("generate_image", {"prompt": "x"})
        self.assertToolError(r, "rate_limited")
        self.assertEqual(len(self.requests), 3)
        self.assertEqual(self.sleeps, [2.0, 8.0])

    async def test_long_retry_after_not_waited(self):
        self.responses = [error_response(429, None, "Rate limit", headers={"Retry-After": "600"}), ok_response()]
        r = await self.call("generate_image", {"prompt": "x"})
        self.assertToolError(r, "rate_limited")
        self.assertIn("600", self.text(r))
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.sleeps, [])

    async def test_timeout_maybe_billed(self):
        def timeout(request):
            raise httpx.ReadTimeout("timed out", request=request)
        for exc in (timeout, lambda req: (_ for _ in ()).throw(httpx.RemoteProtocolError("dropped", request=req))):
            self.requests.clear()
            self.responses = [exc, ok_response()]
            orig = self.handler

            def handler(request, orig=orig):
                self.requests.append(request)
                r = self.responses.pop(0)
                return r(request) if callable(r) else r
            self.handler = handler
            r = await self.call("generate_image", {"prompt": "x"})
            self.handler = orig
            self.assertToolError(r, "timeout_maybe_billed")
            self.assertIn("usage", self.text(r))
            self.assertEqual(len(self.requests), 1)
            self.assertEqual(self.sleeps, [])

    async def test_connect_error_retried(self):
        # The request never left, so it can't have been billed.
        self.responses = [httpx.ConnectError("no route"), ok_response()]
        r = await self.call("generate_image", {"prompt": "x"})
        self.assertFalse(r.is_error, self.text(r))
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.sleeps, [2.0])

    async def test_bad_key_and_echoed_key_hidden(self):
        self.responses = [error_response(401, "invalid_api_key", f"Incorrect API key provided: {KEY}.")]
        r = await self.call("generate_image", {"prompt": "x"})
        self.assertToolError(r, "bad_api_key")
        self.responses = [error_response(400, "x", f"weird echo {KEY}")]
        r = await self.call("generate_image", {"prompt": "x"})
        self.assertToolError(r, "invalid_request")

    async def test_unexpected_success_body(self):
        self.responses = [httpx.Response(200, text="<html>proxy</html>")]
        r = await self.call("generate_image", {"prompt": "x"})
        self.assertToolError(r, "openai_unavailable")
        self.assertIn("billed", self.text(r))
        self.assertEqual(len(self.requests), 1)

    # ------------------------------------------------------------ status and listing

    async def test_image_status_no_network(self):
        core.append_spend(self.data, {"session": "old", "cost_usd": 0.25})
        r = await self.call("image_status", {})
        self.assertFalse(r.is_error, self.text(r))
        sc = r.structured_content
        self.assertIs(sc["key_set"], True)
        self.assertEqual(sc["defaults"]["model"], "gpt-image-2.5-sunburst")
        self.assertEqual(sc["defaults"]["quality"], "medium")
        self.assertEqual(sc["max_cost_per_call"], 0.10)
        self.assertEqual(sc["output_dir"], str(self.proj / "generated-images"))
        self.assertEqual(sc["spent_session_usd"], 0)
        self.assertAlmostEqual(sc["spent_total_usd"], 0.25)
        self.assertIn("image_out_per_token", sc["prices"])
        self.assertNotIn(KEY, self.text(r) + json.dumps(sc))
        self.assertEqual(self.requests, [])
        r = await self.call("image_status", {}, self.server(key=None))
        self.assertIs(r.structured_content["key_set"], False)

    async def test_list_tools_names(self):
        async with Client(self.server()) as c:
            tools = (await c.list_tools()).tools
        self.assertEqual(sorted(t.name for t in tools), ["edit_image", "generate_image", "image_status"])
        gen = next(t for t in tools if t.name == "generate_image")
        self.assertEqual(set(gen.input_schema["properties"]),
                         {"prompt", "model", "size", "quality", "background", "output_format", "n", "filename",
                          "output_dir", "allow_expensive"})
        self.assertEqual(gen.input_schema["required"], ["prompt"])
        edit = next(t for t in tools if t.name == "edit_image")
        self.assertEqual(set(edit.input_schema["properties"]) - set(gen.input_schema["properties"]),
                         {"images", "mask"})
        self.assertEqual(sorted(edit.input_schema["required"]), ["images", "prompt"])


class MainTest(unittest.TestCase):
    def test_build_from_env_ignores_openai_env(self):
        env = {"OPENAI_API_KEY": "sk-shell", "OPENAI_BASE_URL": "https://evil.example", "OPENAI_IMAGES_API_KEY": ""}
        config = core.load_config(env, Path("/p"))
        self.assertIsNone(config.api_key)
        self.assertEqual(openai_images.API_BASE, "https://api.openai.com/v1")
