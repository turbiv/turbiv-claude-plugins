---
name: plan
description: Plan stage of the flow workflow. Writes plan.md and the decision rows for one flow work item, and stops only when a row changes the request or the scope. Use for /flow:plan <item>, or when /flow:start reaches the plan stage. Not for general planning requests outside a flow item.
argument-hint: <item>
---

# Plan

You write the plan for one work item: a free-form `plan.md` and one row in `decisions.md` for every
design decision. The owner sees a summary of 10 lines or fewer. The spec is written later, by a fresh
subagent, from these files. So everything the spec needs must be in the files, not only in the chat.

Read these first. They are the shared rules. Do not copy them into the item files.

- `${CLAUDE_PLUGIN_ROOT}/resources/conventions.md` (work store, item, stages, commits, facts, style)
- `${CLAUDE_PLUGIN_ROOT}/resources/rules/decision-table.md` (rows, K1 and K2, ⚠, the table, replies)
- `${CLAUDE_PLUGIN_ROOT}/resources/rules/sizes.md`
- `${CLAUDE_PLUGIN_ROOT}/resources/templates/plan-summary.md`
- `${CLAUDE_PLUGIN_ROOT}/resources/templates/decisions.md`

Nothing is built in this stage. Read the code as much as you need. Do not change it. Read with Read,
Glob and Grep; use the shell only for `git log` and `git show`. Outside sources belong to the research
stage: when a fact needs one, record it as `unchecked` and say so in the plan's Risk line. Reason: every
other shell or web call asks the owner for approval.

## 1. Find the item and check the input

1. Find the work store and the item as `conventions.md` says. The argument is the item ID or a unique
   part of it.
2. Read `item.md`. Check `stage`:
   - No value: intake did not finish. Say "Run `/flow:start <id>` first" and stop.
   - `intake` with depth `none`: go on. There is no research step at this depth.
   - `intake` with depth `quick` or `deep`: research is not done. Name the missing `research/` files,
     say "Run `/flow:research <id>` first", and stop.
   - `approved`: the spec is binding now. Say that a change needs a new revision, which this version
     does not support, and stop. Reason: a new plan under an approved spec makes two truths.
   - `researched`: go on.
   - `planned` with an open ⚠ row: the plan waits for answers. Go to step 6 and show the stop again,
     unless the owner asked for a new plan. Reason: a new session resumes here.
   - `planned`, `specified` or `validated`: this is a new plan. Say in one line that `spec.md` and
     `validation.md` are out of date and that the spec stage runs again. Keep the existing rows and
     their numbers.
3. Check the research files for the depth in `item.md`: `research/notes.md` for `quick`;
   `research/questions.md`, `research/repo.md` and `research/outside.md` for `deep`; none for `none`.
   When one is missing, name it, say "Run `/flow:research <id>`", and stop.

When this step stops, end with `Stop: <reason>` as the last line. Reason: `/flow:start` reads the
last line to know whether to go on.

## 2. Read

Read `item.md` (the goal, word for word, and the reading), every file in `research/`, and
`decisions.md` if intake made one. Owner rows and the constraints in them are already decided. Do not
ask them again, and do not plan against them.

Read the code that the plan depends on. When the work turns out larger or smaller than the size in
`item.md`, change `size` and its reason in `item.md`, and say so in one line.

## 3. Write `plan.md`

- The file starts with the plan summary of `templates/plan-summary.md`. No front matter, no heading
  and no comment before it. The summary is 10 lines or fewer and its last line is `More: plan.md`.
  Reason: the owner reads only this block, and a check counts its lines from the top of the file.
- After the summary, write the plan in any form and at any length. Cover what the spec writer needs:
  the approach and why, the alternatives you dropped and why, the facts you used, the risks, and what
  you leave to the implementation agent.
- A fact you find in this stage gets the next free `F#`, in the format of `conventions.md`.
- Every goal part has a step in the approach. A goal part that the plan leaves out is a decision row,
  with K1 "yes".
- For size L, the plan can propose a split into child items. The split is a row, because one run
  handles one item.

## 4. Write the rows in `decisions.md`

- Create `decisions.md` from the template if it does not exist, even when there are no rows. Reason:
  the spec stage checks for it.
- Continue the `D#` numbers. Never renumber a row.
- One row for every design decision: each choice between approaches (with 2 or 3 options and a
  recommendation), and each call you made yourself as "made by me". See "Kinds of row" in
  `decision-table.md`: a default the owner never heard is one they could not reject.
- Every row has a recommendation, K1 and K2 answers, evidence and `Source: plan`. Use the exact kind
  lines of the template: `⚠ changes the request`, `⚠ changes the scope`, `⚠ may change the scope`.
- Check each row against "What makes a good row" in `decision-table.md`. A row that is too thin for the
  owner to choose from is not done.

## 5. Check, save, commit

1. Check: the summary is the first block and has 10 lines or fewer; every row has K1, K2 and a
   recommendation; every "yes" or "not sure" answer has a ⚠ kind; every goal part is in the approach
   or in a row.
2. Set `stage: planned` in `item.md`. Do this last.
3. Commit the item folder as `conventions.md` says.

## 6. Show the result

Show the plan summary in a code block, word for word from `plan.md`. Do not reformat or shorten it.
Reason: the owner learns one fixed shape, and a check counts its lines.

**No open ⚠ row:** show the plan summary. Then end with this last line:

`Next: /flow:spec <id>`

**One or more open ⚠ rows:** this is the stop before the spec (design: one early stop, only for ⚠).
When this conversation has not shown the intake play-back yet, start with it: the lines under
`## Reading` in `item.md`, then `Size: <size> — <reason>. Research: <depth>.` Reason: the owner must see
how the goal was read before answering rows that rest on that reading. Then show the plan summary, then
the decision table in the format of `decision-table.md`. End with this last line:

`Stop: answer the ⚠ rows <D#, D#>, then the run goes on.`

Then wait. The reply rules of `decision-table.md` apply:

- Record each answer in `decisions.md`.
- When an answer picks an option other than the recommendation, change `plan.md` and its summary to
  match, and say in one line what changed.
- "ok" with ⚠ rows still open: name them in one line and wait.
- When no ⚠ row is open, commit again and end with `Next: /flow:spec <id>`.

Do not start the spec stage yourself. `/flow:start` runs the stages in order; when the owner runs this
skill alone, they run the next stage.
