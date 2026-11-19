---
plugins: ["../.."]
description: >-
  A clear goal gets no questions: intake sizes it and goes on through plan, spec and validation to the
  approval stop. Graded on progress (plan.md made, both subagents ran), not only on the last message,
  because the approval message can look like a question. Also checks that nothing is approved without
  an "ok" and nothing is written outside the work store. The longest and most costly case.
tags: [one-arm, long]
max_turns: 150
timeout_seconds: 2400
allowed_tools: [Skill, Agent, Read, Glob, Grep, Write, Edit, AskUserQuestion, TodoWrite]
env:
  EVAL_FLOW_WORK_ITEMS: work-items
---
/flow:start Add a footer to the home page, site/index.html, with the contact address info@example.com as a mailto link. depth=none
