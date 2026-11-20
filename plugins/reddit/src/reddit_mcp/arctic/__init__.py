"""The Arctic Shift client module: HTTP client, cache, errors and shared helpers.

Tool modules import from here::

    from reddit_mcp.arctic import (
        ArcticShiftClient, archive_tool, make_result, shape_post, shape_comment,
        resolve_window, parse_post_ref, DEFAULT_POST_FIELDS, InputError,
    )

See docs/architecture.md for the stable interface.
"""

from .cache import NullCache, ResponseCache
from .client import (
    COMMENT_FIELDS,
    DEFAULT_COMMENT_FIELDS,
    DEFAULT_POST_FIELDS,
    FULL_ONLY_FIELDS,
    IDS_BATCH,
    MAX_LIMIT,
    POST_FIELDS,
    RULES_BATCH,
    SHORT_LINKS_BATCH,
    WIKI_PATHS_BATCH,
    ArchiveResponse,
    ArcticShiftClient,
    item_is_final,
)
from .config import DEFAULT_BASE_URL, DEFAULT_STATUS_URL, DEFAULT_USER_AGENT, Settings
from .errors import (
    ArchiveError,
    ArchiveUnavailable,
    Attempt,
    InputError,
    QueryRejected,
    QueryTooHeavy,
    RateLimited,
    format_error,
)
from .freshness import Freshness, freshness_warnings, get_freshness, parse_freshness
from .helpers import (
    ARCHIVE_NOTICE,
    COMMENT_COMPLETENESS_NOTE,
    COMMENT_TEXT_CHARS,
    DEFAULT_MAX_TOKENS,
    POST_TEXT_CHARS,
    SOURCE_NOTE,
    Window,
    age_words,
    archive_tool,
    chunked,
    estimate_tokens,
    fit_to_budget,
    iso,
    make_result,
    parse_comment_ref,
    parse_post_ref,
    permalink_comment,
    permalink_post,
    resolve_window,
    score_status,
    shape_comment,
    shape_post,
    strip_prefix,
    to_epoch,
    trim_text,
    unavailable_feature,
)

__all__ = [name for name in dir() if not name.startswith("_")]
