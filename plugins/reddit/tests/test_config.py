from pathlib import Path

import pytest

from reddit_mcp.arctic import DEFAULT_BASE_URL, DEFAULT_STATUS_URL, Settings


def test_defaults_are_the_public_archive():
    s = Settings.from_env({})
    assert s.base_url == DEFAULT_BASE_URL == "https://arctic-shift.photon-reddit.com/api"
    assert s.status_url == DEFAULT_STATUS_URL
    assert s.min_interval == 1.0
    assert s.allowed_hosts == {"arctic-shift.photon-reddit.com", "status.arctic-shift.photon-reddit.com"}


def test_env_overrides():
    s = Settings.from_env(
        {
            "REDDIT_MCP_BASE_URL": "http://127.0.0.1:9/api/",
            "REDDIT_MCP_STATUS_URL": "http://127.0.0.1:9/status",
            "REDDIT_MCP_MIN_INTERVAL": "2",
            "REDDIT_MCP_CACHE": "off",
        }
    )
    assert s.base_url == "http://127.0.0.1:9/api"
    assert s.min_interval == 2.0
    assert s.cache_path is None


def test_eval_prefixed_copies():
    s = Settings.from_env({"EVAL_REDDIT_MCP_BASE_URL": "https://arctic-shift.invalid/api"})
    assert s.base_url == "https://arctic-shift.invalid/api"
    s = Settings.from_env(
        {"REDDIT_MCP_BASE_URL": "https://a.example/api", "EVAL_REDDIT_MCP_BASE_URL": "https://b.example/api"}
    )
    assert s.base_url == "https://a.example/api"


def test_cache_path_from_env(tmp_path: Path):
    s = Settings.from_env({"REDDIT_MCP_CACHE": str(tmp_path / "x.sqlite3")})
    assert s.cache_path == tmp_path / "x.sqlite3"


@pytest.mark.parametrize("url", ["https://www.reddit.com/api", "https://oauth.reddit.com", "https://redd.it/x"])
def test_reddit_hosts_cannot_be_configured(url):
    with pytest.raises(ValueError, match="Reddit"):
        Settings(base_url=url)


def test_interval_floor():
    assert Settings(min_interval=0).min_interval == 0.5
