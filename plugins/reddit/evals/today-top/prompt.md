---
plugins: ["../.."]
description: >-
  Mocked. "Top posts of today": the archive's scores for posts under ~36 h are the first value
  (1 or 0), so the plugin refuses a score ranking for the last day. Claude must refuse or warn,
  and must not rank by scores of 1 or 0. The server is mocked (mocks/reddit/).
tags: [session-2, mocked]
runs: 3
max_turns: 10
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, ToolSearch, "mcp__plugin_reddit_reddit__*"]
---
Show the top posts of today in r/buildapc.
