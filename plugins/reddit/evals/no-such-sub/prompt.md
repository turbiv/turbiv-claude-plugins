---
plugins: ["../.."]
description: >-
  Mocked. A subreddit with no posts in the archive. Claude must say plainly that it is not in
  the archive (it may not exist, or be private, quarantined or banned) and must not invent
  posts. The server is mocked (mocks/reddit/).
tags: [session-2, mocked]
runs: 3
max_turns: 10
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, ToolSearch, "mcp__plugin_reddit_reddit__*"]
---
What's new in r/thisdoesnotexist12345?
