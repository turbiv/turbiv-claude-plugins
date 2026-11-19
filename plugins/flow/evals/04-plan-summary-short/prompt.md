---
plugins: ["../.."]
description: >-
  /flow:plan on an item at stage intake with depth none writes plan.md whose first block is the summary
  of 10 lines or fewer ending with "More: plan.md", writes decisions.md where every row has a
  recommendation and K1/K2 answers, sets stage planned, and does not start the spec stage itself.
tags: [one-arm]
max_turns: 60
timeout_seconds: 900
allowed_tools: [Skill, Agent, Read, Glob, Grep, Write, Edit, AskUserQuestion, TodoWrite]
env:
  EVAL_FLOW_WORK_ITEMS: work-items
---
/flow:plan 20261118-demo-footer
