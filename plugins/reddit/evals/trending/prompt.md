---
plugins: ["../.."]
description: >-
  Live. "What is trending" has no archive equivalent: Reddit's hot and r/all need live votes.
  Claude must say so, then either ask for a topic or pick large subreddits, name them, and rank
  posts by recent comment activity with that method labelled (trending_posts).
tags: [session-4, live, real-server]
max_turns: 16
timeout_seconds: 480
allowed_tools: [Read, Glob, Grep, WebFetch, WebSearch, Bash, ToolSearch, "mcp__plugin_reddit_reddit__*"]
---
What is currently trending on Reddit?
