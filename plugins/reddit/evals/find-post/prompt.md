---
plugins: ["../.."]
description: >-
  Live. A question whose best answer is an old, loosely titled r/buildapc thread (wi7uhk, 2022).
  Claude should use deep_search with two concept groups (the CPU, and power-limit terms) over at
  least two fitting subreddits, find wi7uhk and cite it. Fallback that still passes: a web search
  finds the URL and the plugin reads it. Run with
  --allow-tools "mcp__plugin_reddit_reddit__*" WebSearch.
tags: [session-2, live, beats-baseline]
runs: 3
max_turns: 25
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, ToolSearch, WebSearch, "mcp__plugin_reddit_reddit__*"]
---
I want to know what power limits I should set for my Intel i9 9900K. What do people on Reddit say?
