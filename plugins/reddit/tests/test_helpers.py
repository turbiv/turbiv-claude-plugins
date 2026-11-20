"""Shared helpers: permalinks, score_status, shaping, trimming, time, IDs, archive_tool."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastmcp import Client, FastMCP

from reddit_mcp.arctic import (
    ARCHIVE_NOTICE,
    SOURCE_NOTE,
    InputError,
    QueryTooHeavy,
    archive_tool,
    estimate_tokens,
    fit_to_budget,
    make_result,
    parse_comment_ref,
    parse_post_ref,
    permalink_comment,
    permalink_post,
    resolve_window,
    score_status,
    shape_comment,
    shape_post,
    to_epoch,
    trim_text,
    unavailable_feature,
)
from support import PROBE_TIME, load_fixture

NOW = PROBE_TIME


def ts(*a: int) -> int:
    return int(datetime(*a, tzinfo=UTC).timestamp())


def tree_comments():
    out = []

    def walk(children):
        for c in children:
            if c["kind"] == "t1":
                out.append(c["data"])
                r = c["data"].get("replies")
                if isinstance(r, dict):
                    walk(r["data"]["children"])

    walk(load_fixture("comments/tree-wi7uhk.json")["data"])
    return out


# ---------------------------------------------------------------- permalinks


def test_permalinks():
    assert permalink_post("buildapc", "t3_wi7uhk") == "https://www.reddit.com/r/buildapc/comments/wi7uhk/"
    assert permalink_comment("buildapc", "t3_wi7uhk", "ijao2ef") == (
        "https://www.reddit.com/r/buildapc/comments/wi7uhk/_/ijao2ef/"
    )


# ---------------------------------------------------------------- score_status


def test_second_pass_means_snapshot():
    c = load_fixture("comments/askreddit-45d-full.json")["data"][0]
    assert score_status(c, NOW) == "snapshot"


def test_late_first_archive_means_snapshot():
    # probed 2026-11-20: first archived 80 h after posting, no _meta
    c = load_fixture("comments/askreddit-4d-full.json")["data"][0]
    assert c["retrieved_on"] - c["created_utc"] > 36 * 3600
    assert score_status(c, NOW) == "snapshot"


def test_full_object_without_second_pass_is_initial():
    c = {"id": "x", "created_utc": NOW - 3600, "retrieved_on": NOW - 3590, "_meta": {}}
    assert score_status(c, NOW) == "initial"


def test_pushshift_era_is_snapshot():
    c = next(x for x in tree_comments() if x["id"] == "ijao2ef")
    assert score_status(c, NOW) == "snapshot"


def test_fields_object_young_is_initial_old_is_snapshot():
    assert score_status({"created_utc": NOW - 3600, "retrieved_on": NOW - 3590}, NOW) == "initial"
    assert score_status({"created_utc": NOW - 5 * 86400, "retrieved_on": NOW - 5 * 86400 + 10}, NOW) == "snapshot"


def test_every_tree_comment_has_a_status():
    assert {score_status(c, NOW) for c in tree_comments()} == {"snapshot"}


# ---------------------------------------------------------------- shaping


def test_shape_post_has_required_labels():
    raw = load_fixture("posts/buildapc-title-phrase.json")["data"][0]
    raw = {**raw, "subreddit": "buildapc", "selftext": "word " * 1000, "upvote_ratio": 1.7}
    p = shape_post(raw, now=NOW)
    assert p["permalink"] == f"https://www.reddit.com/r/buildapc/comments/{raw['id']}/"
    assert p["created_utc"] == raw["created_utc"]
    assert p["score_status"] in {"initial", "snapshot"}
    assert p["truncated"] is True and len(p["selftext"]) < 1600
    assert p["upvote_ratio"] == 1.0


def test_shape_comment_has_required_labels():
    c = next(x for x in tree_comments() if x["id"] == "jqqr5hr")
    s = shape_comment(c, now=NOW)
    assert s["permalink"] == "https://www.reddit.com/r/buildapc/comments/wi7uhk/_/jqqr5hr/"
    assert s["score_status"] == "snapshot"
    assert s["retrieved_2nd_on"] == 1689549302
    assert "truncated" not in s
    assert "downs" not in s


# ---------------------------------------------------------------- size


def test_trim_text():
    assert trim_text("short", 10) == ("short", False)
    text, cut = trim_text("one two three four five six", 12)
    assert cut and text.endswith("…") and len(text) <= 14
    assert trim_text(None, 5) == (None, False)


def test_fit_to_budget_drops_and_flags():
    result = {"items": [{"t": "x" * 3000} for _ in range(20)]}
    fit_to_budget(result, "items", max_tokens=8000)
    assert estimate_tokens(result) <= 8000
    assert result["truncated"] is True and result["omitted_items"] > 0
    assert len(result["items"]) + result["omitted_items"] == 20


@pytest.mark.anyio
async def test_make_result_header(client, fake_archive):
    fake_archive.add_status()
    r = await make_result(client, items=[{"a": 1}], comments=True, window="x")
    assert list(r)[0] == "source" and r["source"] == ARCHIVE_NOTICE
    assert "third-party Reddit archive, not live Reddit" in r["source"]
    assert r["count"] == 1 and r["window"] == "x"
    assert any("90-95%" in n for n in r["notes"])


@pytest.mark.anyio
async def test_make_result_warns_when_ingest_stalls(client, fake_archive):
    status = load_fixture("status/status-2026-11-20.json")
    status["api"] = {**status["api"], "mostRecentPostAt": int((NOW - 2 * 86400) * 1000)}
    fake_archive.add_status(status)
    r = await make_result(client, items=[])
    assert any("stopped ingesting" in w for w in r["warnings"])


@pytest.mark.anyio
async def test_make_result_survives_status_outage(client, fake_archive):
    import httpx

    fake_archive.add("STATUS", httpx.ConnectError("down"))
    r = await make_result(client, items=[])
    assert "warnings" not in r


# ---------------------------------------------------------------- time (T8)


def test_to_epoch_forms():
    assert to_epoch(1659849574) == 1659849574
    assert to_epoch(1659849574000) == 1659849574
    assert to_epoch("1659849574") == 1659849574
    assert to_epoch("2022-08-07") == ts(2022, 8, 7)
    assert to_epoch("2022-08") == ts(2022, 8, 1)
    assert to_epoch("2022") == ts(2022, 1, 1)
    assert to_epoch("2022-08-07T05:19:34Z") == 1659849574
    assert to_epoch("2 days", now=NOW) == NOW - 2 * 86400


def test_m_is_ambiguous():
    with pytest.raises(InputError, match="ambiguous"):
        to_epoch("3m", now=NOW)


def test_last_three_months_is_calendar_months():
    now = ts(2026, 11, 21, 12)
    w = resolve_window("last 3 months", now=now)
    assert (w.after, w.before) == (ts(2026, 8, 21, 12), now)
    assert w.label == "last 3 months"
    assert "2026-08-21 12:00 UTC to 2026-11-21 12:00 UTC" == w.describe()


@pytest.mark.parametrize(
    "t,days", [("hour", 1 / 24), ("day", 1), ("week", 7), ("year", 365)]
)
def test_reddit_time_filters(t, days):
    now = ts(2026, 11, 21)
    w = resolve_window(t, now=now)
    assert w.before == now
    assert w.after == pytest.approx(now - days * 86400, abs=86400 if t == "year" else 1)


def test_month_filter_and_all():
    now = ts(2026, 3, 31)
    assert resolve_window("month", now=now).after == ts(2026, 2, 28)
    assert resolve_window("all", now=now).params() == {}


def test_custom_range_and_year_end():
    w = resolve_window(after="2025", before="2025")
    assert (w.after, w.before) == (ts(2025, 1, 1), ts(2026, 1, 1))
    with pytest.raises(InputError):
        resolve_window("week", after="2025")
    with pytest.raises(InputError):
        resolve_window(after="2026-01-01", before="2025-01-01")


# ---------------------------------------------------------------- IDs


@pytest.mark.parametrize(
    "ref",
    [
        "wi7uhk",
        "t3_wi7uhk",
        "https://www.reddit.com/r/buildapc/comments/wi7uhk/intel_9900k_underclockingpower_limit_experiments/",
        "https://old.reddit.com/r/buildapc/comments/wi7uhk/",
        "reddit.com/r/buildapc/comments/wi7uhk",
        "https://redd.it/wi7uhk",
    ],
)
def test_parse_post_ref(ref):
    assert parse_post_ref(ref) == "wi7uhk"


def test_share_link_needs_resolving():
    with pytest.raises(InputError, match="share link"):
        parse_post_ref("https://www.reddit.com/r/buildapc/s/AbCdEf123")


def test_parse_comment_ref():
    assert parse_comment_ref("t1_ijao2ef") == ("ijao2ef", None)
    url = "https://www.reddit.com/r/buildapc/comments/wi7uhk/intel_9900k/ijao2ef/"
    assert parse_comment_ref(url) == ("ijao2ef", "wi7uhk")
    assert parse_comment_ref("https://www.reddit.com/r/buildapc/comments/wi7uhk/_/ijao2ef/") == ("ijao2ef", "wi7uhk")
    assert parse_comment_ref("19sqrqixbulj5") == ("19sqrqixbulj5", None)  # new random-ID format


def test_not_an_id():
    with pytest.raises(InputError):
        parse_post_ref("https://example.com/x")


# ---------------------------------------------------------------- refusals and archive_tool


def test_unavailable_feature_messages():
    for f in ("hot", "relevance", "global search"):
        msg = unavailable_feature(f)
        assert msg.startswith(f"not available from an archive: {f}")
        assert "not live Reddit" in msg


@pytest.mark.anyio
async def test_archive_tool_registers_read_only_and_converts_errors():
    mcp = FastMCP("t")

    @archive_tool(mcp)
    async def heavy(q: str) -> dict:
        """Search something."""
        raise QueryTooHeavy(attempts=[], suggestions=["add a window"], error="Timeout. Maybe slow down a bit")

    async with Client(mcp) as c:
        (tool,) = await c.list_tools()
        assert tool.name == "heavy"
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.destructive_hint is False
        assert SOURCE_NOTE in tool.description
        assert "q" in tool.input_schema["properties"]
        r = await c.call_tool("heavy", {"q": "x"}, raise_on_error=False)
        assert r.is_error
        assert "too heavy for the archive" in r.content[0].text
