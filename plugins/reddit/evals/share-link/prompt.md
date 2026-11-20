---
plugins: ["../.."]
description: >-
  Live. A Reddit app share link (/r/<sub>/s/<code>) is opaque. resolve_share_link resolves it
  through the archive's short_links table (never reddit.com). Fact, checked on 2026-11-21:
  /r/running/s/0MH2aME2Z9 resolves to comment k1unwm1 in post 16puhb3, "Achievements for
  Saturday, September 23, 2023" in r/running.
tags: [session-4, live, real-server]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, WebFetch, WebSearch, Bash, ToolSearch, "mcp__plugin_reddit_reddit__*"]
---
Open this link: https://www.reddit.com/r/running/s/0MH2aME2Z9
