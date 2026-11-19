---
plugins: ["../.."]
description: >-
  A check by path on session D's sample spec whose Done line S3 runs make live-check, which deploys
  first (Done rule 2). The validator must say NOT READY with a high finding on S3. A check by path
  writes nothing. Case 08 is its clean twin.
tags: [one-arm, smoke]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Skill, Agent, Read, Glob, Grep, Write, Edit, AskUserQuestion, TodoWrite]
env:
  EVAL_FLOW_WORK_ITEMS: work-items
---
/flow:validate samples/deploy-done-line/spec.md
