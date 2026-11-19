---
name: spec
description: Spec stage of the flow workflow. Dispatches the spec-writer subagent to write spec.md for one flow work item from its files only, then adds the writer's guesses as decision rows. Use for /flow:spec <item>, or when /flow:start reaches the spec stage. Not for writing other specs.
argument-hint: <item>
---

# Spec

A fresh subagent, `flow:spec-writer`, writes `spec.md` from the item files only. It does not see this
conversation. Reason: a writer that sees only the files also finds the gaps in them, and each gap comes
back as a guess. You turn each guess into a decision row, so the owner sees it at approval.

Read these first. They are the shared rules. Do not copy them into the item files.

- `${CLAUDE_PLUGIN_ROOT}/resources/conventions.md` (work store, item, stages, commits, style)
- `${CLAUDE_PLUGIN_ROOT}/resources/rules/decision-table.md` (rows, K1 and K2, ⚠)
- `${CLAUDE_PLUGIN_ROOT}/resources/templates/decisions.md`

Nothing is built in this stage.

## 1. Find the item and check the input

1. Find the work store and the item as `conventions.md` says. The argument is the item ID or a unique
   part of it.
2. Read `item.md`. Check `stage`:
   - No value: intake did not finish. Say "Run `/flow:start <id>` first" and stop.
   - `intake` or `researched`: the plan is not done. Say "Run `/flow:plan <id>` first" and stop.
   - `approved`: the spec is binding now. Say that a change needs a new revision, which this version
     does not support, and stop.
   - `planned`: go on.
   - `specified` or `validated`: this is a new spec. Say in one line that `validation.md` is out of date
     and that validation runs again.
3. Check that `plan.md` and `decisions.md` exist. When one is missing, name it, say "Run
   `/flow:plan <id>`", and stop.
4. Check `decisions.md` for an open ⚠ row with `Source: intake` or `Source: plan`. The spec waits for
   those rows (the stop after the plan). Show them in the table format of `decision-table.md` and wait.
   Record the answers by the reply rules, commit, then go on. Open ⚠ rows from an earlier spec writer or
   validator do not block: they wait for approval.

When this step stops, end with `Stop: <reason>` as the last line. Reason: `/flow:start` reads the
last line to know whether to go on.

## 2. Put the conversation into the files

When this conversation holds something the spec needs that is not in `item.md` or `decisions.md` (an
owner reply, a constraint, a correction), write it into `decisions.md` now, as an owner row. Reason: the
writer sees only the files. What is not in the files does not reach the spec.

## 3. Dispatch the writer

Call the Agent tool with `subagent_type: flow:spec-writer` and this prompt. Fill in the three values.
Add nothing else: no goal text, no file content, no summary of the conversation, no hints.

```
Item folder: <absolute path of the item folder>
Resources folder: ${CLAUDE_PLUGIN_ROOT}/resources
Date: <yyyy-mm-dd>
Write spec.md for this item and return your report.
```

When the dispatch fails, or the writer returns without a `spec.md` in the item folder, say so and end
with `Stop: the spec writer did not run: <reason>`. Do not write the spec yourself. Reason: a spec
written with this conversation in mind hides the gaps that the fresh writer would find.

## 4. Turn the report into rows

The writer returns two lists: guesses (`G#`) and goal parts with no possible Done line (`U#`). Add one
row to `decisions.md` for each item in both lists. Continue the `D#` numbers.

- **Guess `G#`:** the decision is the question the files left open. Recommended: what the writer wrote,
  with its reason. Options: the writer's choice and the other option it names. Answer K1 and K2 and
  set the kind from them, as for any row. `About:` the topic the writer gave (`build` or `check`).
  `Source: spec writer guess G<n>`. `Status: open`.
- **No Done line `U#`:** Done rule 6 says the spec is underspecified for that goal part. K1 is "yes":
  without a check, the owner may get only part of the goal. Kind: `⚠ changes the request`. Recommend a
  checkable form: a narrower goal part, or a person line (`P#`). `About: build`.
  `Source: spec writer guess U<n>`. `Status: open`.

Then update `spec.md`, and change nothing else in it:

1. Replace each `(G<n>)` marker with the `(D<n>)` of its new row. Reason: every "In" line and every
   Areas entry needs a trace to the goal or a `D#`, or the validator flags it as a hidden decision.
2. Add each new row to the `## Decisions` section as `D<n> <decision> — AI — details in decisions.md`.

A new ⚠ row from this stage does not stop the run. It shows in the table at approval.

## 5. Save, commit, show

1. Set `stage: specified` in `item.md`. Do this last.
2. Commit the item folder as `conventions.md` says.
3. Tell the owner in one or two lines: the number of Done lines, and the rows added (with how many
   have ⚠). Do not show the spec now; the approval message shows its Done lines.
4. End with this last line:

`Next: /flow:validate <id>`

Do not start the validation yourself. `/flow:start` runs the stages in order; when the owner runs this
skill alone, they run the next stage.
