---
plugins: ["../.."]
description: >-
  The item is validated and D2 is an open ⚠ row. The owner replies "ok" alone. "ok" accepts the
  recommended rows and the rows made by me, never a ⚠ row, so the spec stays a draft and the reply names
  D2. The reply comes as the skill's argument: a run has no second turn.
tags: [one-arm, smoke]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Skill, Agent, Read, Glob, Grep, Write, Edit, AskUserQuestion, TodoWrite]
env:
  EVAL_FLOW_WORK_ITEMS: work-items
---
/flow:approve 20261118-demo-footer ok
