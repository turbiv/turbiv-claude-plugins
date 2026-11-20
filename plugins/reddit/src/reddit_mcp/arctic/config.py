"""Settings for the Arctic Shift client, read from environment variables (D3)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from .. import __version__

DEFAULT_BASE_URL = "https://arctic-shift.photon-reddit.com/api"
DEFAULT_STATUS_URL = "https://status.arctic-shift.photon-reddit.com/api"
PROJECT_URL = "https://github.com/turbiv/turbiv-claude-plugins/tree/main/plugins/reddit"
DEFAULT_USER_AGENT = (
    f"reddit-research-mcp/{__version__} "
    f"(read-only research client for the Arctic Shift archive; +{PROJECT_URL})"
)

# R1: the spacing between two requests can be configured, but never below this.
MIN_INTERVAL_FLOOR = 0.5

# D1: the server never talks to Reddit itself, whatever the configuration says.
FORBIDDEN_HOST_SUFFIXES = (
    "reddit.com",
    "redd.it",
    "redditmedia.com",
    "redditstatic.com",
    "reddituploads.com",
)


def is_forbidden_host(host: str) -> bool:
    host = host.lower().rstrip(".")
    return any(host == s or host.endswith("." + s) for s in FORBIDDEN_HOST_SUFFIXES)


def _default_cache_path() -> Path:
    root = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(root) / "reddit-mcp" / "cache.sqlite3"


_ENV_KEYS = (
    "REDDIT_MCP_BASE_URL",
    "REDDIT_MCP_STATUS_URL",
    "REDDIT_MCP_MIN_INTERVAL",
    "REDDIT_MCP_TIMEOUT",
    "REDDIT_MCP_CACHE_TTL",
    "REDDIT_MCP_USER_AGENT",
    "REDDIT_MCP_CACHE",
)


@dataclass(frozen=True)
class Settings:
    base_url: str = DEFAULT_BASE_URL
    status_url: str = DEFAULT_STATUS_URL
    min_interval: float = 1.0
    timeout: float = 30.0
    cache_path: Path | None = field(default_factory=_default_cache_path)
    cache_ttl: float = 600.0
    user_agent: str = DEFAULT_USER_AGENT
    max_rate_limit_wait: float = 65.0
    retry_delay_422: float = 2.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_url", self.base_url.rstrip("/"))
        object.__setattr__(self, "status_url", self.status_url.rstrip("/"))
        object.__setattr__(self, "min_interval", max(MIN_INTERVAL_FLOOR, float(self.min_interval)))
        object.__setattr__(self, "retry_delay_422", min(3.0, max(1.0, float(self.retry_delay_422))))
        for url in (self.base_url, self.status_url):
            host = urlsplit(url).hostname or ""
            if not host:
                raise ValueError(f"not a valid URL: {url!r}")
            if is_forbidden_host(host):
                raise ValueError(f"{url!r} points at Reddit; this server only talks to the archive")

    @property
    def allowed_hosts(self) -> frozenset[str]:
        return frozenset(
            (urlsplit(u).hostname or "").lower() for u in (self.base_url, self.status_url)
        )

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Settings":
        raw = dict(os.environ if env is None else env)
        # `claude plugin eval` lets a case set only EVAL_* variables, so each setting also
        # reads an EVAL_-prefixed copy. The plain name wins when both are set.
        env = {k: raw.get(k) or raw.get("EVAL_" + k, "") for k in _ENV_KEYS}
        kw: dict = {}
        if v := env.get("REDDIT_MCP_BASE_URL"):
            kw["base_url"] = v
        if v := env.get("REDDIT_MCP_STATUS_URL"):
            kw["status_url"] = v
        if v := env.get("REDDIT_MCP_MIN_INTERVAL"):
            kw["min_interval"] = float(v)
        if v := env.get("REDDIT_MCP_TIMEOUT"):
            kw["timeout"] = float(v)
        if v := env.get("REDDIT_MCP_CACHE_TTL"):
            kw["cache_ttl"] = float(v)
        if v := env.get("REDDIT_MCP_USER_AGENT"):
            kw["user_agent"] = v
        if v := env.get("REDDIT_MCP_CACHE"):
            kw["cache_path"] = None if v.lower() in {"off", "0", "false", "none"} else Path(v).expanduser()
        return cls(**kw)
