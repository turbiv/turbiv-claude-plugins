---
plugins: ["../.."]
description: >-
  An unclear goal gets one open question in normal chat (exactly one question mark), with no picker
  dialog, one ask (not two joined by "and"), no example answers or readings before the owner says
  why, and no plan is written.
  AskUserQuestion is allowed, so the no-picker gate means something.
  The prompt does not say how many questions to ask.
tags: [one-arm, smoke]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Skill, Agent, Read, Glob, Grep, Write, Edit, AskUserQuestion, TodoWrite]
env:
  EVAL_FLOW_WORK_ITEMS: work-items
---
/flow:start Make the about page better.
