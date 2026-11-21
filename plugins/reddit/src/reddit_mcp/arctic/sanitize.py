"""Prompt-injection hardening for text written by Reddit users (Session 5).

`archive_tool` runs `harden()` over every tool result, so every tool gets it once:

- `clean_text()` removes text a reader cannot see but a model reads: Unicode format characters
  (category Cf: zero-width space, word joiner, BOM, bidi overrides and isolates, and the "tag"
  characters used to smuggle ASCII), their numeric HTML entities (`&#x200B;`), and closed HTML
  comments (`<!-- … -->`, raw or escaped as `&lt;!-- … --&gt;`). It keeps what ordinary text
  needs: ZWJ/ZWNJ between two letters or emoji, and the LRM/RLM/ALM marks. Each item says how much
  it lost in `stripped_invisible`, so nothing disappears silently.
- `find_injection()` is a short regex check for text that addresses an AI tool or baits a tool
  call or a secret. It also runs on the hidden parts that were removed. A hit only marks the item
  (`possible_injection: true`, `injection_match`). Nothing is hidden or dropped.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

# Keys whose string values are written by Reddit users: post, comment, wiki and sidebar text,
# snippets, subreddit rules, flair and usernames. helpers.has_user_text uses the same set.
TEXT_KEYS = frozenset(
    {"title", "selftext", "body", "content", "public_description", "sidebar", "description",
     "snippet", "text", "rule", "flair", "link_flair_text", "author_flair_text", "author", "username"}
)
# Usernames are cleaned but not checked for injections.
_NAME_KEYS = frozenset({"author", "username"})

# Closed comments only: Reddit shows an unclosed "<!--" to readers (a post about HTML), so it stays.
_HTML_COMMENT = re.compile(r"<!--(.*?)-->|&lt;!--(.*?)--&gt;", re.S)
_ENTITY = re.compile(r"&#(?:[xX]([0-9a-fA-F]{1,6})|([0-9]{1,7}));")

ZWNJ, ZWJ = "\u200c", "\u200d"
# Format characters with a visible job in ordinary text: left-to-right, right-to-left and Arabic
# letter marks. ZWNJ/ZWJ are kept too when they join two letters or emoji (_joins).
_KEEP = frozenset({"\u200e", "\u200f", "\u061c"})
_TAG_FIRST, _TAG_LAST = 0xE0000, 0xE007F


def _joinable(ch: str) -> bool:
    """A character a ZWJ/ZWNJ may sit next to: a letter, a mark (virama, variation selector),
    or an emoji or emoji modifier (category So or Sk)."""
    cat = unicodedata.category(ch)
    return cat[0] in "LM" or cat in ("So", "Sk")


def _invisible_at(text: str, i: int) -> bool:
    """True when text[i] is a format character to remove (category Cf, with the exceptions above)."""
    ch = text[i]
    if unicodedata.category(ch) != "Cf" or ch in _KEEP:
        return False
    if ch in (ZWNJ, ZWJ):
        # 👨‍👩‍👧, Persian می‌خواهم and Indic conjuncts need these between two letters or emoji.
        return not (0 < i < len(text) - 1 and _joinable(text[i - 1]) and _joinable(text[i + 1]))
    return True


def _entity_char(m: re.Match[str]) -> str | None:
    try:
        cp = int(m.group(1), 16) if m.group(1) else int(m.group(2))
        return chr(cp)
    except (ValueError, OverflowError):
        return None


def _clean(text: str) -> tuple[str, int, list[str]]:
    """(clean text, items removed, the hidden text that was removed, for the injection check)."""
    removed = 0
    hidden: list[str] = []
    if "<!--" in text or "&lt;!--" in text:
        def comment(m: re.Match[str]) -> str:
            hidden.append(m.group(1) if m.group(1) is not None else m.group(2) or "")
            return ""

        text, n = _HTML_COMMENT.subn(comment, text)
        removed += n
    if "&#" in text:
        def drop(m: re.Match[str]) -> str:
            nonlocal removed
            ch = _entity_char(m)
            if ch is not None and ch not in (ZWNJ, ZWJ) and ch not in _KEEP \
                    and unicodedata.category(ch) == "Cf":
                removed += 1
                return ""
            return m.group(0)

        text = _ENTITY.sub(drop, text)
    if not text.isascii():
        kept: list[str] = []
        tags: list[str] = []
        for i, ch in enumerate(text):
            if _invisible_at(text, i):
                removed += 1
                cp = ord(ch)
                if _TAG_FIRST + 0x20 <= cp <= _TAG_FIRST + 0x7E:
                    tags.append(chr(cp - _TAG_FIRST))  # tag characters spell invisible ASCII
            else:
                kept.append(ch)
        if tags:
            hidden.append("".join(tags))
        if len(kept) != len(text):
            text = "".join(kept)
    return text, removed, hidden


def clean_text(text: str) -> tuple[str, int]:
    """`text` without invisible characters, their entities and closed HTML comments; and how many
    were removed."""
    clean, n, _ = _clean(text)
    return clean, n


# Short on purpose: each pattern is covered by tests/test_hardening.py, with ordinary tech and AI
# talk as negative cases. A hit marks, never hides.
_NOT_NEGATED = r"(?<!never )(?<!not )(?<!n't )(?<!dont )"
INJECTION_PATTERNS = tuple(
    re.compile(p, re.I)
    for p in (
        # addressing the model
        r"\b(?:ignore|disregard|forget|override)\b[^.\n]{0,40}?\b(?:instructions?|rules|prompts?|guidelines)\b",
        r"\byou are (?:now |an? )+(?:AI|assistant|chatbot|language model|LLM)\b",
        r"\b(?:AI|LLM)s?(?: (?:assistants?|agents?|models?|tools?|bots?))?(?:\s*:|,? (?:must|should|reading|"
        r"summari[sz]ing|processing|that (?:read|summari[sz]e))\b)",
        r"\b(?:note|message|notice|attention|instructions?) (?:to|for) (?:all |any )?(?:AI|LLM)s?\b",
        r"\[\s*system\b|\bsystem (?:prompt|message|notice|instruction)s?\s*:|\bnew system prompt\b",
        # tool and command bait
        r"\brun (?:this|the following|these) (?:shell )?(?:command|script)s?\b",
        r"\b(?:curl|wget)\s+(?:-\S+\s+)*['\"]?https?://\S+[^\n]*\|\s*(?:sudo\s+)?(?:ba|z)?sh\b|\brm\s+-rf\s+[/~]",
        r"\b(?:fetch|open|visit|browse to|go to) (?:this|the following|that) (?:url|link|page|site|address)\b",
        # secrets bait: a verb aimed at the reader's own secrets
        _NOT_NEGATED + r"\b(?:print|send|e-?mail|post|paste|share|upload|include|read|cat|search(?: reddit)? for)\b"
        r"[^.\n]{0,60}?(?:~/\.ssh|\$HOME/\.ssh|id_rsa|\.env\b|api[_ ]?keys?|secret keys?|access tokens?|"
        r"passwords?|env(?:ironment)? var(?:iable)?s?)",
    )
)


def find_injection(text: str) -> str | None:
    """The first phrase that looks like an instruction to an AI tool, or None."""
    # Joiners kept between letters must not split a trigger word ("ig\u200dnore") past the check.
    text = text.replace(ZWJ, "").replace(ZWNJ, "")
    for p in INJECTION_PATTERNS:
        m = p.search(text)
        if m:
            return m.group(0).strip()[:80]
    return None


class _Tally:
    def __init__(self) -> None:
        self.stripped = 0
        self.flagged = 0


def _walk(obj: Any, tally: _Tally) -> None:
    """Clean and mark every dict in place. Idempotent: a second pass removes nothing new and keeps
    the marks, and the tally counts what the items carry, so the totals stay right."""
    if isinstance(obj, list):
        for v in obj:
            _walk(v, tally)
        return
    if not isinstance(obj, dict):
        return
    stripped = 0
    match: str | None = None
    for k, v in list(obj.items()):
        if k in TEXT_KEYS and isinstance(v, str) and v:
            clean, n, hidden = _clean(v)
            if n:
                obj[k] = clean
                stripped += n
            if match is None and k not in _NAME_KEYS:
                match = find_injection(clean) or next(
                    (f"(hidden) {m}" for h in hidden if (m := find_injection(h))), None)
        elif isinstance(v, (dict, list)):
            _walk(v, tally)
    if stripped:
        obj["stripped_invisible"] = obj.get("stripped_invisible", 0) + stripped
    if match is not None and not obj.get("possible_injection"):
        obj["possible_injection"] = True
        obj["injection_match"] = match[:80]
    if isinstance(obj.get("stripped_invisible"), int):
        tally.stripped += obj["stripped_invisible"]
    if obj.get("possible_injection") is True:
        tally.flagged += 1


def harden(result: Any) -> tuple[Any, int, int]:
    """Clean and mark `result` in place. Returns (result, characters/comments stripped, items flagged)."""
    tally = _Tally()
    if isinstance(result, (dict, list)):
        _walk(result, tally)
    return result, tally.stripped, tally.flagged
