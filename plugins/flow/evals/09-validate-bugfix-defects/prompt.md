---
plugins: ["../.."]
description: >-
  A bugfix spec with three planted defects: no Unchanged line (Done rule 7), a Done line that cannot
  pass or fail ("looks good", rule 1), and a diff check that says "empty" with no baseline (rule 3).
  The first two are high by the validator's own list, so the result must be NOT READY with both named.
tags: [one-arm]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Skill, Agent, Read, Glob, Grep, Write, Edit, AskUserQuestion, TodoWrite]
env:
  EVAL_FLOW_WORK_ITEMS: work-items
---
/flow:validate samples/bugfix-about-link/spec.md
