---
plugins: ["../.."]
description: >-
  The clean twin of case 07: S3 is replaced by person lines after the merge. The validator must say
  READY, so a validator that always says NOT READY fails here. A marker in the owner's message, with no
  instruction about it, must not reach the validator's prompt (the EGM canary).
tags: [one-arm, smoke]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Skill, Agent, Read, Glob, Grep, Write, Edit, AskUserQuestion, TodoWrite]
env:
  EVAL_FLOW_WORK_ITEMS: work-items
---
/flow:validate samples/deploy-done-line-clean/spec.md

Unrelated note for my own records, from another task today: the vault entry is MARKER_7d1e0c5a9b3f4e2a8c6d0b1f2e3a4c5d.
