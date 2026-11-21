"""Prompt-injection hardening for text written by Reddit users (Session 5).

`archive_tool` runs `harden()` over every tool result, so every tool gets it once:

- `clean_text()` removes text a reader cannot see but a model reads: zero-width characters, bidi
  controls and every other Unicode format character (category Cf, which includes the "tag"
  characters used to smuggle ASCII), their numeric HTML entities (`&#x200B;`), and HTML comments
  (`<!-- … -->`, raw or escaped as `&lt;!-- … --&gt;`). Each item says how much it lost in
  `stripped_invisible`, so nothing disappears silently.
- `find_injection()` is a short regex check for text that addresses an AI tool or baits a tool
  call. A hit only marks the item (`possible_injection: true`, `injection_match`). Nothing is
  hidden or dropped.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

# Keys whose string values are written by Reddit users: post, comment, wiki and sidebar text,
# snippets, flair and usernames.
TEXT_KEYS = frozenset(
    {"title", "selftext", "body", "content", "public_description", "sidebar", "description",
     "snippet", "text", "flair", "link_flair_text", "author_flair_text", "author", "username"}
)

_HTML_COMMENT = re.compile(r"<!--.*?(?:-->|\Z)|&lt;!--.*?(?:--&gt;|\Z)", re.S)
_ENTITY = re.compile(r"&#(?:[xX]([0-9a-fA-F]{1,6})|([0-9]{1,7}));")


def _is_invisible(ch: str) -> bool:
    # Cf covers U+200B-U+200D, U+2060, U+FEFF, U+202A-U+202E, U+2066-U+2069, U+00AD, tags, ...
    return unicodedata.category(ch) == "Cf"


def _entity_char(m: re.Match[str]) -> str | None:
    try:
        cp = int(m.group(1), 16) if m.group(1) else int(m.group(2))
        return chr(cp)
    except (ValueError, OverflowError):
        return None


def clean_text(text: str) -> tuple[str, int]:
    """`text` without invisible characters, their entities and HTML comments; and how many were removed."""
    removed = 0
    if "<!--" in text or "&lt;!--" in text:
        text, n = _HTML_COMMENT.subn("", text)
        removed += n
    if "&#" in text:
        def drop(m: re.Match[str]) -> str:
            nonlocal removed
            ch = _entity_char(m)
            if ch is not None and _is_invisible(ch):
                removed += 1
                return ""
            return m.group(0)

        text = _ENTITY.sub(drop, text)
    if not text.isascii():
        kept = [ch for ch in text if not _is_invisible(ch)]
        if len(kept) != len(text):
            removed += len(text) - len(kept)
            text = "".join(kept)
    return text, removed


# Short on purpose: each pattern is covered by tests/test_hardening.py. A hit marks, never hides.
INJECTION_PATTERNS = tuple(
    re.compile(p, re.I)
    for p in (
        r"\b(?:ignore|disregard|forget|override)\b[^.\n]{0,40}?\b(?:instructions?|rules|prompts?|guidelines)\b",
        r"\byou are (?:now |an? )+(?:AI|assistant|chatbot|language model|LLM)\b",
        r"\bAI (?:assistant|agent|model|tool)s?\b",
        r"\bsystem (?:prompt|message|notice|instruction)s?\b",
        r"\brun (?:this|the following|these) (?:shell )?(?:command|script)s?\b",
        r"\b(?:curl|wget)\s+(?:-\S+\s+)*['\"]?https?://",
        r"\brm\s+-rf\b",
        r"\|\s*(?:ba|z)?sh\b",
        r"\b(?:fetch|open|visit|browse to|go to) (?:this|the following|that) (?:url|link|page|site|address)\b",
        r"(?:~|\$HOME)/\.ssh\b|\.env\b|\b(?:api[_ ]?key|secret key|access token|env(?:ironment)? var(?:iable)?s?)\b",
    )
)


def find_injection(text: str) -> str | None:
    """The first phrase that looks like an instruction to an AI tool, or None."""
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
            clean, n = clean_text(v)
            if n:
                obj[k] = clean
                stripped += n
            if match is None and k != "author" and k != "username":
                match = find_injection(clean)
        elif isinstance(v, (dict, list)):
            _walk(v, tally)
    if stripped:
        obj["stripped_invisible"] = obj.get("stripped_invisible", 0) + stripped
        tally.stripped += stripped
    if match is not None:
        obj["possible_injection"] = True
        obj["injection_match"] = match
        tally.flagged += 1


def harden(result: Any) -> tuple[Any, int, int]:
    """Clean and mark `result` in place. Returns (result, characters/comments stripped, items flagged)."""
    tally = _Tally()
    if isinstance(result, (dict, list)):
        _walk(result, tally)
    return result, tally.stripped, tally.flagged
