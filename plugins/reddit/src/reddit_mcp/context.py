"""What every tool module's `register(mcp, ctx)` receives."""

from __future__ import annotations

from dataclasses import dataclass

from .arctic import ArcticShiftClient


@dataclass
class ServerContext:
    client: ArcticShiftClient
