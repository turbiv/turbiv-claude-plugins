---
plugins: ["../.."]
description: >-
  The owner answers the ⚠ row by name and approves: "D2 ok, ok". The spec gets status approved and an
  approved line with the date and the SHA-256 (or "unavailable" when the hash command cannot run),
  D2 is recorded as accepted, log.md gets an end note, stage approved is set, and nothing goes to Jira.
tags: [one-arm]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Skill, Agent, Read, Glob, Grep, Write, Edit, AskUserQuestion, TodoWrite]
env:
  EVAL_FLOW_WORK_ITEMS: work-items
---
/flow:approve 20261118-demo-footer D2 ok, ok
