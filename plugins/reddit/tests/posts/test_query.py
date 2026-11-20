"""Query parsing, the archive plan, and local matching (T7; probes Q6)."""

from __future__ import annotations

import pytest

from reddit_mcp.arctic import InputError
from reddit_mcp.tools.posts import (
    TermMatcher,
    TextIndex,
    parse_query,
    plan_query,
    query_matches,
)


def test_words_and_or_phrase_exclude():
    q = parse_query('undervolt OR underclock "power limit" -laptop NOT gpu')
    assert [[t.show() for t in c] for c in q.clauses] == [
        ["undervolt", "underclock"], ['"power limit"'], ["-laptop"], ["-gpu"],
    ]


def test_operators_map():
    q = parse_query('flair:Help title:chatter author:u/bob nsfw:no site:github.com self:yes url:https://x.io/a')
    fields = [c[0].field for c in q.clauses]
    assert fields == ["flair", "title", "author", "nsfw", "site", "self", "url"]
    plan = plan_query(q, ["MechanicalKeyboards"])
    assert plan.params == {"link_flair_text": "Help", "author": "bob", "over_18": False, "url": "https://x.io/a"}
    assert plan.keyword == ("title", "chatter")
    assert any("site:github.com" in n and "self:yes" in n for n in plan.notes)


def test_only_one_keyword_goes_to_the_archive():
    plan = plan_query(parse_query('9900k "power limit" undervolt OR underclock -laptop'), ["buildapc"])
    assert plan.keyword == ("query", '"power limit"')  # the most specific single-term clause
    local = plan.notes[0]
    assert "9900k" in local and "undervolt OR underclock" in local and "-laptop" in local


def test_model_names_are_sent_by_their_core():
    plan = plan_query(parse_query("title:i9-9900K"), ["intel"])
    assert plan.keyword == ("title", "9900k")
    assert plan.keyword_clause not in plan.satisfied  # checked locally too


def test_subreddit_operator_adds_a_scope():
    plan = plan_query(parse_query("subreddit:framework hinge"), [])
    assert plan.subreddits == ["framework"]


def test_bad_bool_and_empty():
    with pytest.raises(InputError):
        plan_query(parse_query("nsfw:maybe x"), ["a1"])
    with pytest.raises(InputError):
        parse_query("   ")


@pytest.mark.parametrize("text", ["Intel i9-9900K power", "i9 9900k", "my 9900K", "the 9900 K runs hot"])
def test_model_name_normalization(text):
    for term in ("i9-9900K", "i9 9900k", "9900k"):
        assert TermMatcher(term).matches(TextIndex(text)), (term, text)


def test_model_numbers_are_not_fuzzy():
    m = TermMatcher("9900k", fuzzy=True)
    m.expand({"9700k", "9900ks"})
    assert not m.matches(TextIndex("my 9700K"))


def test_fuzzy_words_and_phrases():
    m = TermMatcher("undervolting", fuzzy=True)
    idx = TextIndex("I undervolted it and also tried undervoltign")
    m.expand(idx.set)
    assert m.matches(idx)
    p = TermMatcher("power limit", fuzzy=True)
    idx2 = TextIndex("set the power limits in bios")
    p.expand(idx2.set)
    assert p.matches(idx2)
    assert TermMatcher("power limit").matches(TextIndex("POWER-LIMIT experiments"))
    assert TermMatcher("undervolt").matches(TextIndex("under volt"))
    assert not TermMatcher("power limit").matches(TextIndex("limit the power"))


def test_query_matches_local_logic():
    q = parse_query('9900k undervolt OR underclock -laptop')
    yes = {"id": "a", "title": "9900K underclocking?", "selftext": "underclock test"}
    no_exclude = {"id": "b", "title": "9900k undervolt laptop", "selftext": ""}
    no_or = {"id": "c", "title": "9900k temps", "selftext": ""}
    assert query_matches(q, yes)
    assert not query_matches(q, no_exclude)
    assert not query_matches(q, no_or)


def test_site_and_self_filters():
    q = parse_query("site:github.com keyboard")
    link = {"id": "a", "title": "keyboard firmware", "url": "https://www.github.com/qmk"}
    selfpost = {"id": "b", "title": "keyboard", "url": "https://www.reddit.com/r/x/comments/b/k/"}
    assert query_matches(q, link) and not query_matches(q, selfpost)
    assert query_matches(parse_query("self:yes keyboard"), selfpost)
