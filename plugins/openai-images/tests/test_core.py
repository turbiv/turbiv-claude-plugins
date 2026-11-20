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
