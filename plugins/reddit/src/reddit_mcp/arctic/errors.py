"""Errors the Arctic Shift client raises (E1-E4), and how a tool shows them."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Attempt:
    """One HTTP attempt: what was sent and what came back."""

    params: dict[str, Any]
    status: int | None
    elapsed: float
    error: str | None = None


class InputError(ValueError):
    """The caller asked for something invalid. Raised before any network call."""


class ArchiveError(Exception):
    """Base class. `kind` is a stable machine name, `str(e)` is plain words."""

    kind = "archive_error"

    def __init__(self, message: str, *, attempts: list[Attempt] | None = None):
        super().__init__(message)
        self.message = message
        self.attempts = attempts or []


class QueryRejected(ArchiveError):
    """E4: HTTP 400 (or another 4xx). `error` is the archive's own text, verbatim."""

    kind = "query_error"

    def __init__(self, error: str, *, status: int, attempts: list[Attempt] | None = None):
        super().__init__(f"the archive rejected the query (HTTP {status}): {error}", attempts=attempts)
        self.error = error
        self.status = status


class QueryTooHeavy(ArchiveError):
    """E2: HTTP 422 after the bounded retries."""

    kind = "query_too_heavy"

    def __init__(self, *, attempts: list[Attempt], suggestions: list[str], error: str | None = None):
        tries = ", ".join(
            f"limit={a.params.get('limit', 'default')} -> {a.status} in {a.elapsed:.2f} s" for a in attempts
        )
        msg = "the query is too heavy for the archive (HTTP 422"
        if error:
            msg += f": {error}"
        msg += f"); tried {tries}."
        if suggestions:
            msg += " Try: " + "; ".join(suggestions) + "."
        super().__init__(msg, attempts=attempts)
        self.suggestions = suggestions
        self.error = error

    @property
    def fast(self) -> bool:
        """True when every 422 came back in under 1 s (see docs/probes.md, Q7)."""
        return bool(self.attempts) and all(a.elapsed < 1.0 for a in self.attempts)


class RateLimited(ArchiveError):
    """E1: HTTP 429 again after one wait-and-retry."""

    kind = "rate_limited"

    def __init__(self, wait_seconds: float, *, attempts: list[Attempt] | None = None):
        super().__init__(
            f"the archive is rate limiting this client; wait about {wait_seconds:.0f} s and ask again",
            attempts=attempts,
        )
        self.wait_seconds = wait_seconds


@dataclass
class ComponentStatus:
    name: str
    is_available: bool | None
    failed_at: Any = None
    raw: dict[str, Any] = field(default_factory=dict)


class ArchiveUnavailable(ArchiveError):
    """E3: 5xx, Cloudflare 52x/530, DNS failure, refused connection or timeout.

    `components` comes from the status feed on its own host. `status_error` says why the
    feed itself could not be read, when that happened.
    """

    kind = "archive_unavailable"

    def __init__(
        self,
        cause: str,
        *,
        components: list[ComponentStatus] | None = None,
        status_error: str | None = None,
        attempts: list[Attempt] | None = None,
    ):
        self.cause = cause
        self.components = components or []
        self.status_error = status_error
        api = next((c for c in self.components if c.name == "api"), None)
        if status_error:
            verdict = f"the status page could not be read either ({status_error})"
        elif api is not None and api.is_available is False:
            verdict = "the status page says the API is down"
            if api.failed_at:
                verdict += f" (failed at {api.failed_at})"
        elif api is not None and api.is_available:
            verdict = (
                "the status page says the API is up, so this may be a passing fault or an "
                "archive bug with this kind of query"
            )
        else:
            verdict = "the status page gave no verdict"
        parts = [f"archive unavailable: {cause}; {verdict}."]
        if self.components:
            parts.append(
                "Components: "
                + ", ".join(
                    f"{c.name} {'up' if c.is_available else 'down' if c.is_available is False else 'unknown'}"
                    + (f" (failed at {c.failed_at})" if c.failed_at else "")
                    for c in self.components
                )
                + "."
            )
        parts.append("There is no other source: this server never falls back to reddit.com.")
        super().__init__(" ".join(parts), attempts=attempts)

    @property
    def outage(self) -> bool:
        """True when this looks like an outage, False when it looks like a query error."""
        if self.status_error:
            return True
        api = next((c for c in self.components if c.name == "api"), None)
        return not (api is not None and api.is_available)


def format_error(exc: Exception) -> str:
    """The text a tool returns for an error. Starts with the error category."""
    if isinstance(exc, ArchiveError):
        return exc.message
    if isinstance(exc, InputError):
        return f"input error: {exc}"
    return f"unexpected error: {exc}"
