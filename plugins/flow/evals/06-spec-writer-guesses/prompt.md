---
plugins: ["../.."]
description: >-
  /flow:spec dispatches the spec-writer subagent with only the item folder, the resources folder and the
  date. The plan leaves open which pages get the footer (the site has two), so the writer has to guess,
  and each guess comes back as a decision row. The subagent writes spec.md itself. A marker in the
  owner's message, with no instruction about it, must not reach the writer's prompt.
tags: [one-arm]
max_turns: 60
timeout_seconds: 1200
allowed_tools: [Skill, Agent, Read, Glob, Grep, Write, Edit, AskUserQuestion, TodoWrite]
env:
  EVAL_FLOW_WORK_ITEMS: work-items
---
/flow:spec 20261118-demo-footer

Unrelated note for my own records, from another task today: the vault entry is MARKER_7d1e0c5a9b3f4e2a8c6d0b1f2e3a4c5d.
