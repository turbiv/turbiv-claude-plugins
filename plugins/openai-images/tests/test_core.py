"""Tests for core.py: config, cost, validation, errors, files."""
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import fixtures  # noqa: F401  (puts server/ on sys.path)
import core


def usd(tokens):
    return tokens * 30e-6


class ConfigTest(unittest.TestCase):
    def test_config_defaults(self):
        c = core.load_config({}, Path("/work/proj"))
        self.assertIsNone(c.api_key)
        self.assertEqual(c.default_model, "gpt-image-2.5-sunburst")
        self.assertEqual(c.default_quality, "medium")
        self.assertEqual(c.max_cost_per_call, 0.10)
        self.assertEqual(c.project_dir, Path("/work/proj").resolve())
        self.assertEqual(c.data_dir, Path("~/.claude/plugins/data/openai-images").expanduser())

    def test_config_from_env(self):
        env = {"OPENAI_IMAGES_API_KEY": " sk-test-123 ", "OPENAI_IMAGES_DEFAULT_MODEL": "gpt-image-2.6-flare",
               "OPENAI_IMAGES_DEFAULT_QUALITY": "low", "OPENAI_IMAGES_MAX_COST_PER_CALL": "0.25",
               "OPENAI_IMAGES_DATA_DIR": "/data/oi", "CLAUDE_PROJECT_DIR": "/other/proj"}
        c = core.load_config(env, Path("/work/proj"))
        self.assertEqual(c.api_key, "sk-test-123")
        self.assertEqual(c.default_model, "gpt-image-2.6-flare")
        self.assertEqual(c.default_quality, "low")
        self.assertEqual(c.max_cost_per_call, 0.25)
        self.assertEqual(c.data_dir, Path("/data/oi"))
        self.assertEqual(c.project_dir, Path("/other/proj").resolve())

    def test_blank_key_is_no_key(self):
        for raw in ("", "  ", "${user_config.openai_api_key}", "\n"):
            self.assertIsNone(core.load_config({"OPENAI_IMAGES_API_KEY": raw}, Path("/p")).api_key, repr(raw))

    def test_placeholders_and_bad_numbers_fall_back(self):
        env = {"OPENAI_IMAGES_DEFAULT_MODEL": "${user_config.default_model}", "OPENAI_IMAGES_DEFAULT_QUALITY": " ",
               "OPENAI_IMAGES_MAX_COST_PER_CALL": "lots", "OPENAI_IMAGES_DATA_DIR": "${CLAUDE_PLUGIN_DATA}",
               "CLAUDE_PROJECT_DIR": "  "}
        c = core.load_config(env, Path("/work/proj"))
        self.assertEqual(c.default_model, "gpt-image-2.5-sunburst")
        self.assertEqual(c.default_quality, "medium")
        self.assertEqual(c.max_cost_per_call, 0.10)
        self.assertEqual(c.data_dir, Path("~/.claude/plugins/data/openai-images").expanduser())
        self.assertEqual(c.project_dir, Path("/work/proj").resolve())
        for bad in ("0", "-1", "nan", "inf"):
            c = core.load_config({"OPENAI_IMAGES_MAX_COST_PER_CALL": bad}, Path("/p"))
            self.assertEqual(c.max_cost_per_call, 0.10, bad)


class EstimateTest(unittest.TestCase):
    def test_cost_matches_published_gpt_image_2(self):
        for model in ("gpt-image-2", "gpt-image-2-2026-04-21"):
            got = [round(usd(core.estimate_output_tokens(model, q, 1024, 1024)), 3) for q in ("low", "medium", "high")]
            self.assertEqual(got, [0.006, 0.053, 0.211])
            got = [round(usd(core.estimate_output_tokens(model, q, 1536, 1024)), 3) for q in ("low", "medium", "high")]
            self.assertEqual(got, [0.005, 0.041, 0.165])

    def test_estimate_2_6_medium(self):
        self.assertEqual(core.estimate_output_tokens("gpt-image-2.6-sunburst", "medium", 1024, 1024), 1449)
        self.assertEqual(core.estimate_output_tokens("gpt-image-2.6-flare", "low", 1024, 1024), 823)
        self.assertEqual(core.estimate_output_tokens("gpt-image-2.6-sunburst", "max", 3840, 2160), 13342)

    def test_estimate_2_5_medium(self):
        self.assertEqual(core.estimate_output_tokens("gpt-image-2.5-sunburst", "medium", 1024, 1024), 439)
        self.assertEqual(core.estimate_output_tokens("gpt-image-2.5-flare-2026-09-08", "low", 1536, 864), 120)
        self.assertEqual(core.estimate_output_tokens("gpt-image-2.5-sunburst", "xhigh", 2048, 2048), 6343)

    def test_unknown_model_uses_2_6(self):
        self.assertEqual(core.estimate_output_tokens("gpt-image-3-new", "medium", 1024, 1024), 1449)
        e = core.estimate_cost("gpt-image-3-new", "medium", "1024x1024", 1, 0)
        self.assertTrue(any("2.6" in n for n in e.notes))

    def test_default_estimate(self):
        e = core.estimate_cost("gpt-image-2.5-sunburst", "medium", "1024x1024", 1, 0)
        self.assertAlmostEqual(e.output_usd, usd(439))
        self.assertEqual(e.input_allowance_usd, 0)
        self.assertAlmostEqual(e.total_usd, usd(439))
        self.assertEqual(round(e.total_usd, 3), 0.013)
        e4 = core.estimate_cost("gpt-image-2.5-sunburst", "medium", "1024x1024", 4, 0)
        self.assertAlmostEqual(e4.output_usd, 4 * usd(439))

    def test_estimate_auto_is_worst_case(self):
        auto = core.estimate_cost("gpt-image-2.6-sunburst", "auto", "auto", 1, 0)
        high = core.estimate_cost("gpt-image-2.6-sunburst", "high", "1024x1024", 1, 0)
        self.assertAlmostEqual(auto.total_usd, high.total_usd)
        self.assertGreater(auto.total_usd, 0)
        self.assertEqual(len(auto.notes), 2)
        # An unknown quality word is estimated at the top level, not skipped.
        odd = core.estimate_cost("gpt-image-2.6-sunburst", "ultra", "1024x1024", 1, 0)
        top = core.estimate_cost("gpt-image-2.6-sunburst", "max", "1024x1024", 1, 0)
        self.assertAlmostEqual(odd.total_usd, top.total_usd)

    def test_input_allowance(self):
        e = core.estimate_cost("gpt-image-2.5-sunburst", "medium", "1024x1024", 1, 3)
        self.assertAlmostEqual(e.input_allowance_usd, 0.15)
        self.assertAlmostEqual(e.total_usd, usd(439) + 0.15)
        self.assertTrue(any("allowance" in n for n in e.notes))

    def test_estimate_includes_prompt_text(self):
        # First real call (2026-11-21): a 650-character prompt used 160 text tokens ($0.0008).
        bare = core.estimate_cost("gpt-image-2.5-sunburst", "medium", "1024x1536", 1, 0)
        with_prompt = core.estimate_cost("gpt-image-2.5-sunburst", "medium", "1024x1536", 1, 0, prompt_chars=650)
        self.assertAlmostEqual(with_prompt.prompt_usd, 217 * 5e-6)
        self.assertAlmostEqual(with_prompt.total_usd, bare.total_usd + 217 * 5e-6)
        self.assertGreaterEqual(with_prompt.prompt_usd, 160 * 5e-6)

    def test_cost_from_usage(self):
        usage = {"input_tokens": 50, "input_tokens_details": {"text_tokens": 10, "image_tokens": 40},
                 "output_tokens": 50, "output_tokens_details": {"image_tokens": 50, "text_tokens": 0},
                 "total_tokens": 100}
        self.assertAlmostEqual(core.cost_from_usage("gpt-image-2.5-sunburst", usage),
                               10 * 5e-6 + 40 * 8e-6 + 50 * 30e-6)

    def test_cost_from_usage_without_details(self):
        # No breakdown: input counted at the image-in rate, output at the image-out rate (the higher rates).
        self.assertAlmostEqual(core.cost_from_usage("x", {"input_tokens": 100, "output_tokens": 200}),
                               100 * 8e-6 + 200 * 30e-6)
        self.assertEqual(core.cost_from_usage("x", {}), 0)


def err(status, code=None, message="m", type_=None, headers=None, **extra):
    body = {"error": {"message": message, "type": type_, "param": None, "code": code, **extra}}
    return core.classify_error(status, body, headers or {})


class ErrorTest(unittest.TestCase):
    def test_error_str(self):
        e = core.ImagesError("rate_limited", "Slow down.", "Wait.", retryable=True)
        self.assertEqual(str(e), "rate_limited: Slow down. Next: Wait.")
        self.assertTrue(e.retryable)
        self.assertIsNone(e.retry_after)

    def test_401_bad_key_does_not_echo_key(self):
        e = err(401, "invalid_api_key", "Incorrect API key provided: sk-proj-abc***xyz.")
        self.assertEqual(e.code, "bad_api_key")
        self.assertFalse(e.retryable)
        self.assertNotIn("sk-", str(e))
        self.assertIn("/plugin configure openai-images", str(e))

    def test_403_verification(self):
        e = err(403, None, "Your organization must be verified to use the model `gpt-image-2`. Please go to ...",
                "invalid_request_error")
        self.assertEqual(e.code, "org_verification_required")
        self.assertIn("platform.openai.com/settings/organization/general", str(e))
        self.assertIn("15 minutes", str(e))
        self.assertFalse(e.retryable)

    def test_other_403(self):
        e = err(403, "unsupported_country_region_territory", "Country, region, or territory not supported")
        self.assertEqual(e.code, "invalid_request")
        self.assertIn("not supported", str(e))
        self.assertFalse(e.retryable)

    def test_400_moderation(self):
        e = err(400, "moderation_blocked", "Your request was rejected by the safety system.",
                "image_generation_user_error",
                moderation_details={"moderation_stage": "output", "categories": ["violence", "harassment"]})
        self.assertEqual(e.code, "moderation_blocked")
        self.assertFalse(e.retryable)
        self.assertIn("output", e.message)
        self.assertIn("violence", e.message)
        self.assertIn("harassment", e.message)
        self.assertIn("rephrase", e.next_step.lower())

    def test_other_400(self):
        e = err(400, "unknown_parameter", "Unknown parameter: 'foo'.", "invalid_request_error")
        self.assertEqual(e.code, "invalid_request")
        self.assertIn("Unknown parameter: 'foo'.", e.message)
        self.assertFalse(e.retryable)

    def test_404_model_not_found(self):
        for status, code in ((404, "model_not_found"), (404, None), (400, "model_not_found")):
            e = err(status, code, "The model `gpt-image-9` does not exist.")
            self.assertEqual(e.code, "model_not_found", (status, code))
            self.assertFalse(e.retryable)

    def test_429_quota_codes_not_retryable(self):
        for code, type_ in (("credit_balance_exhausted", "insufficient_quota"), ("insufficient_quota", None),
                            (None, "insufficient_quota"), ("organization_spend_limit_exceeded", None),
                            ("project_spend_limit_exceeded", None), ("organization_usage_limit_exceeded", None),
                            ("billing_hard_limit_reached", None)):
            e = err(429, code, "You exceeded your current quota.", type_, headers={"Retry-After": "1"})
            self.assertEqual(e.code, "out_of_credit", (code, type_))
            self.assertFalse(e.retryable, (code, type_))
            self.assertIn("platform.openai.com/settings/organization/billing", str(e))

    def test_429_rate_limit_retryable(self):
        e = err(429, None, "Rate limit reached for requests", "requests", headers={"retry-after": "7"})
        self.assertEqual(e.code, "rate_limited")
        self.assertTrue(e.retryable)
        self.assertEqual(e.retry_after, 7.0)
        e = err(429, "rate_limit_exceeded", "Rate limit", headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"})
        self.assertTrue(e.retryable)
        self.assertIsNone(e.retry_after)

    def test_500_503_retryable(self):
        for status in (500, 503):
            e = core.classify_error(status, None, {"Retry-After": "3"})
            self.assertEqual(e.code, "openai_unavailable")
            self.assertTrue(e.retryable)
            self.assertEqual(e.retry_after, 3.0)

    def test_other_5xx_not_retried(self):
        # 502/504 may come after OpenAI started (and billed) the work, so they are not retried.
        for status in (502, 504):
            e = core.classify_error(status, None, {})
            self.assertEqual(e.code, "openai_unavailable")
            self.assertFalse(e.retryable)

    def test_messages_scrub_keys(self):
        e = err(400, "x", "bad key sk-proj-AbC123_def in body")
        self.assertNotIn("AbC123", str(e))


class ValidateTest(unittest.TestCase):
    def ok(self, **kw):
        args = dict(size="1024x1024", background="auto", output_format="png", n=1)
        args.update(kw)
        core.validate_request(**args)

    def bad(self, **kw):
        with self.assertRaises(core.ImagesError) as cm:
            self.ok(**kw)
        self.assertEqual(cm.exception.code, "invalid_request")
        self.assertFalse(cm.exception.retryable)
        return cm.exception

    def test_parse_size(self):
        self.assertEqual(core.parse_size("1536x864"), (1536, 864))
        self.assertEqual(core.parse_size(" 1024X1536 "), (1024, 1536))
        self.assertIsNone(core.parse_size("auto"))
        with self.assertRaises(core.ImagesError):
            core.parse_size("big")

    def test_sizes(self):
        for size in ("1536x864", "1024x1024", "1536x1024", "1024x1536", "3840x1280", "3840x2160", "auto"):
            self.ok(size=size)
        self.assertIn("16", self.bad(size="1000x1000").message)
        self.assertIn("3840", self.bad(size="4000x1504").message)
        self.assertIn("655,360", self.bad(size="512x512").message)
        self.assertIn("1:3", self.bad(size="3840x1264").message)
        self.bad(size="square")
        self.bad(size="0x0")

    def test_transparent_needs_png_or_webp(self):
        self.ok(background="transparent", output_format="png")
        self.ok(background="transparent", output_format="webp")
        self.assertIn("png", self.bad(background="transparent", output_format="jpeg").message)

    def test_n(self):
        for n in (1, 4):
            self.ok(n=n)
        for n in (0, 5, -1):
            self.bad(n=n)

    def test_unknown_values_pass_to_api(self):
        self.ok(background="something-new", output_format="gif")


class FilesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(os.path.realpath(self._tmp.name))
        self.proj = self.root / "proj"
        self.proj.mkdir()
        self.outside = self.root / "outside"
        self.outside.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def assertCode(self, code, fn, *args):
        with self.assertRaises(core.ImagesError) as cm:
            fn(*args)
        self.assertEqual(cm.exception.code, code)
        return cm.exception

    def test_resolve_inside(self):
        self.assertEqual(core.resolve_inside(self.proj, "generated-images"), self.proj / "generated-images")
        self.assertEqual(core.resolve_inside(self.proj, str(self.proj / "a/b")), self.proj / "a/b")
        self.assertEqual(core.resolve_inside(self.proj, "."), self.proj)

    def test_dotdot_refused(self):
        self.assertCode("path_outside_project", core.resolve_inside, self.proj, "../outside/x.png")
        self.assertCode("path_outside_project", core.resolve_inside, self.proj, "a/../../outside")

    def test_absolute_outside_refused(self):
        self.assertCode("path_outside_project", core.resolve_inside, self.proj, str(self.outside / "x.png"))
        self.assertCode("path_outside_project", core.resolve_inside, self.proj, "/etc/passwd")
        # A sibling folder whose name starts with the project's name is still outside.
        (self.root / "proj-evil").mkdir()
        self.assertCode("path_outside_project", core.resolve_inside, self.proj, str(self.root / "proj-evil"))

    def test_symlink_escape_refused(self):
        secret = self.outside / "secret.png"
        secret.write_bytes(fixtures.png_bytes())
        (self.proj / "link.png").symlink_to(secret)
        (self.proj / "linkdir").symlink_to(self.outside, target_is_directory=True)
        self.assertCode("path_outside_project", core.check_input_image, self.proj, "link.png")
        self.assertCode("path_outside_project", core.check_input_image, self.proj, "linkdir/secret.png")
        self.assertCode("path_outside_project", core.resolve_inside, self.proj, "linkdir/new")

    def test_symlink_inside_ok(self):
        real = self.proj / "real.png"
        real.write_bytes(fixtures.png_bytes())
        (self.proj / "alias.png").symlink_to(real)
        self.assertEqual(core.check_input_image(self.proj, "alias.png"), real)

    def test_check_input_image(self):
        for name, data in (("a.png", fixtures.png_bytes()), ("b.jpg", fixtures.jpeg_bytes()),
                           ("c.webp", fixtures.webp_bytes())):
            (self.proj / name).write_bytes(data)
            self.assertEqual(core.check_input_image(self.proj, name), self.proj / name)
        self.assertCode("input_not_found", core.check_input_image, self.proj, "missing.png")
        (self.proj / "dir.png").mkdir()
        self.assertCode("input_not_found", core.check_input_image, self.proj, "dir.png")
        (self.proj / "fake.png").write_bytes(b"GIF89a not really")
        self.assertCode("invalid_request", core.check_input_image, self.proj, "fake.png")

    def test_image_mime(self):
        self.assertEqual(core.image_mime(fixtures.png_bytes()), "image/png")
        self.assertEqual(core.image_mime(fixtures.jpeg_bytes()), "image/jpeg")
        self.assertEqual(core.image_mime(fixtures.webp_bytes()), "image/webp")
        self.assertIsNone(core.image_mime(b"hello"))

    def test_output_path_name(self):
        now = datetime(2026, 11, 21, 9, 5, 7)
        p = core.output_path(self.proj, None, "A red fox, jumping over the LAZY dog at dawn!", "png", now)
        self.assertEqual(p.parent, self.proj)
        self.assertTrue(p.name.startswith("20261121-090507-a-red-fox-jumping"), p.name)
        self.assertTrue(p.name.endswith(".png"))
        self.assertRegex(p.stem[16:], r"^[a-z0-9-]{1,40}$")
        p = core.output_path(self.proj, "My Logo.png", "ignored", "webp", now)
        self.assertEqual(p.name, "20261121-090507-my-logo.webp")
        p = core.output_path(self.proj, "x" * 90, "ignored", "png", now)
        self.assertEqual(len(p.stem), 16 + 40)
        p = core.output_path(self.proj, "../../etc", "", "png", now)
        self.assertEqual(p.parent, self.proj)
        p = core.output_path(self.proj, None, "日本語", "png", now)
        self.assertEqual(p.name, "20261121-090507-image.png")

    def test_output_path_unique_same_second(self):
        now = datetime(2026, 11, 21, 9, 5, 7)
        first = core.output_path(self.proj, "fox", "p", "png", now)
        core.write_new(first, b"one")
        second = core.output_path(self.proj, "fox", "p", "png", now)
        self.assertNotEqual(first, second)
        self.assertEqual(second.name, "20261121-090507-fox-2.png")
        core.write_new(second, b"two")
        third = core.output_path(self.proj, "fox", "p", "png", now)
        self.assertEqual(third.name, "20261121-090507-fox-3.png")
        # A sidecar taking the name also counts as taken.
        (self.proj / "20261121-090507-fox-3.png.json").write_text("{}")
        self.assertEqual(core.output_path(self.proj, "fox", "p", "png", now).name, "20261121-090507-fox-4.png")
        self.assertEqual(first.read_bytes(), b"one")
        self.assertEqual(second.read_bytes(), b"two")

    def test_write_new_never_overwrites(self):
        p = self.proj / "deep" / "dir" / "img.png"
        core.write_new(p, b"first")
        with self.assertRaises(FileExistsError):
            core.write_new(p, b"second")
        self.assertEqual(p.read_bytes(), b"first")

    def test_image_info(self):
        self.assertEqual(core.image_info(fixtures.png_bytes(2, 3)), ("png", 2, 3))
        self.assertEqual(core.image_info(fixtures.jpeg_bytes(5, 7)), ("jpeg", 5, 7))
        for kind in ("VP8X", "VP8", "VP8L"):
            self.assertEqual(core.image_info(fixtures.webp_bytes(9, 4, kind)), ("webp", 9, 4), kind)
        self.assertEqual(core.image_info(b"nope"), ("unknown", 0, 0))

    def test_sidecar(self):
        img = self.proj / "a.png"
        img.write_bytes(fixtures.png_bytes())
        record = {"prompt": "a fox", "settings_sent": {"model": "m", "size": "1024x1024"},
                  "usage": {"output_tokens": 439}, "cost_usd": 0.013,
                  "response": {"data": [{"b64_json": "QUFBQQ=="}], "size": "1024x1024"},
                  "inputs": ["data:image/png;base64,QUFBQQ==", "in.png"]}
        side = core.write_sidecar(img, record)
        self.assertEqual(side, self.proj / "a.png.json")
        text = side.read_text()
        saved = json.loads(text)
        self.assertEqual(saved["prompt"], "a fox")
        self.assertEqual(saved["settings_sent"]["size"], "1024x1024")
        self.assertEqual(saved["usage"]["output_tokens"], 439)
        self.assertEqual(saved["cost_usd"], 0.013)
        self.assertNotIn("b64", text)
        self.assertNotIn("QUFBQQ", text)
        self.assertIn("in.png", saved["inputs"])
        with self.assertRaises(FileExistsError):
            core.write_sidecar(img, record)

    def test_spend_totals(self):
        data = self.root / "data"
        self.assertEqual(core.spend_totals(data, "s1"), (0.0, 0.0))
        core.append_spend(data, {"session": "s1", "cost_usd": 0.013})
        core.append_spend(data, {"session": "s1", "cost_usd": 0.02})
        core.append_spend(data, {"session": "s2", "cost_usd": 0.5})
        with open(data / "spend.jsonl", "a") as f:
            f.write("not json\n{\"session\": \"s1\"}\n")
        session, total = core.spend_totals(data, "s1")
        self.assertAlmostEqual(session, 0.033)
        self.assertAlmostEqual(total, 0.533)
        self.assertAlmostEqual(core.spend_totals(data, "s2")[0], 0.5)
