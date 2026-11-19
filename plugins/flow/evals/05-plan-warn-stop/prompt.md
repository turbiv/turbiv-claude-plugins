---
plugins: ["../.."]
description: >-
  /flow:plan on an item whose research shows that every fix either changes another team's repo (scope)
  or changes what the goal gets (request). The plan must give that row ⚠, stop before the spec with the
  plan summary and the decision table, and end with the Stop line. No spec writer, no spec.md.
tags: [one-arm]
max_turns: 60
timeout_seconds: 900
allowed_tools: [Skill, Agent, Read, Glob, Grep, Write, Edit, AskUserQuestion, TodoWrite]
env:
  EVAL_FLOW_WORK_ITEMS: work-items
---
/flow:plan 20261118-deploy-fix
