---
plugins: ["../.."]
description: >-
  Live. A Reddit-style search with a flair and a year. search_posts maps flair to
  link_flair_text and 2025 to an absolute epoch range. Every result must be from 2025.
  Run with --allow-tools "mcp__plugin_reddit_reddit__*".
tags: [session-2, live]
runs: 3
max_turns: 15
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, ToolSearch, "mcp__plugin_reddit_reddit__*"]
---
Find posts in r/MechanicalKeyboards with the flair 'Help' about key chatter from 2025.
