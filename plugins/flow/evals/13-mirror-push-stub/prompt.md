---
plugins: ["../.."]
description: >-
  In version 1, /flow:mirror push is a stub: it says push comes in version 2, dispatches no agent,
  calls no Jira tool and writes nothing. The Jira write tools exist in the run and fail, so the gate
  means something.
tags: [one-arm, smoke]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Skill, Agent, Read, Glob, Grep, Write, Edit, AskUserQuestion, TodoWrite]
env:
  EVAL_FLOW_WORK_ITEMS: work-items
---
/flow:mirror 20261118-demo-footer push
