---
name: validate
description: Checks a flow spec with a fresh, read-only validator, then applies small fixes and turns other findings into decision rows. Use for /flow:validate, after the spec stage, or to check any spec file. Returns READY or NOT READY.
argument-hint: <item | path to a spec> [repo path ...]
---

# Validate

Stage 4 of `flow`. A fresh validator answers two questions. Is the spec correct? Can an implementation
agent use it without guessing? It runs for every size.

Shared rules, read when you need them:

- `${CLAUDE_PLUGIN_ROOT}/resources/conventions.md`: work store, item folder, stages, commits, style.
- `${CLAUDE_PLUGIN_ROOT}/resources/rules/done-rules.md`: the spec and its Done lines.
- `${CLAUDE_PLUGIN_ROOT}/resources/rules/decision-table.md`: rows, K1 and K2, ⚠.
- `${CLAUDE_PLUGIN_ROOT}/resources/templates/validation.md` and `templates/decisions.md`.

## 1. Find the spec

The first argument is a path or an item.

- **Path:** it names an existing file. This is a **check only**: you write nothing and change nothing.
  Reason: the path can be any file, also a sample or someone else's spec. Use `decisions.md` and
  `item.md` from the same folder when they exist.
- **Item:** first find the work store as `conventions.md` says (also when Bash cannot run), then find the
  item folder in that store as it says. Do not search elsewhere. The folder needs
  `spec.md` and `decisions.md`. When one is missing, name it, say that `/flow:spec <id>` makes it, and
  stop.
- **Stage, by item:** `specified` or `validated`: go on. `approved`: see below. No value: intake did not
  finish; name `/flow:start <id>` and stop. `intake`, `researched` or `planned`: a `spec.md` here is
  missing or out of date (a new plan makes the spec stage run again); name `/flow:spec <id>` and stop.
  Reason: a stale spec must not reach `validated`.
- When this step stops, end with `Stop: <reason>` as the last line. Reason: `/flow:start` reads the last
  line of each stage skill.
- **Approved spec** (`status: approved` in its front matter): a check only, also by item. Reason: after
  approval the spec text is frozen (Done rule 11).

## 2. Collect the inputs

- **Size:** from `item.md`; `unknown` when there is no `item.md`.
- **Repos:** the extra arguments, else `repos:` in `item.md`, else the current working directory. Read a
  relative `repos:` entry from the folder of `item.md`. When you fall back to the working directory, say
  so in one line.
- Use absolute paths. Run no shell command for this. Reason: a check by path must also work where shell
  calls are denied.

## 3. Run the validator

Dispatch the `flow:spec-validator` agent with the Agent tool. The prompt holds these lines and nothing
else:

```
Mode: full
Spec: <absolute path of spec.md>
Decisions: <absolute path of decisions.md, or none>
Size: <S|M|L|unknown>
Repos: <absolute path>, <absolute path>
Rules: ${CLAUDE_PLUGIN_ROOT}/resources/rules/done-rules.md, ${CLAUDE_PLUGIN_ROOT}/resources/rules/decision-table.md, ${CLAUDE_PLUGIN_ROOT}/resources/conventions.md, ${CLAUDE_PLUGIN_ROOT}/resources/templates/validation.md
```

Never add the goal, the plan, the conversation or your own view of the spec. Reason: the validator must
read the spec as the implementation agent will, with nothing else. Anything you add hides a gap.

## 4. Compare the restatement

When `item.md` exists, compare the validator's restatement with the goal in `item.md`. When the outcome
differs, the spec misleads: add a `high` finding with the next `V#`, "restatement differs from the goal",
and quote both in one line each. Then set the Result line again: `READY` only with no `high` finding.

## 5. A check only: report and stop

Reply in this shape, and nothing before it. Copy the finding lines as the validator wrote them; do not
reword them. Reason: the owner and the evals read the lines in one fixed format.

```
Validation: <the Result line, word for word>
Not covered: Done rules 3 and 4 (baseline, red first). They run at the build start.   (only with READY)
<each high and medium finding line, V# — severity — …>
Low: <n>. Say "show all" to see them.        (only when there are low findings)
Check only: nothing was written.
```

Stop here.

## 6. By item: write and act

1. Write `validation.md` in the item folder from the template: the header lines (`Run: full`), then the
   validator's text. Replace an earlier `validation.md` and say so.
2. Handle every finding, highest first:
   - **Small fix:** the row for it would get K1 no and K2 no. Change `spec.md` or `decisions.md`, and add
     a row "made by me" with `Source: validator V#`. A row the validator says needs ⚠ gets its ⚠ here.
   - **Else:** add a row with `Source: validator V#`: ⚠ or recommended, by K1 and K2. Never ask the
     owner now. Reason: all decisions wait for one table at approval.
   - Give each new row `About: check` when it changes only how a Done line checks, else `About: build`.
3. **After `NOT READY`:** dispatch a fresh `flow:spec-validator` once, for all `high` findings: the ones
   you fixed and the ones that became rows. Reason: a `high` finding that waits for the owner is still
   open, and the Result line must say so.

   ```
   Mode: re-check
   Spec: <path>
   Decisions: <path>
   Size: <size>
   Repos: <paths>
   Rules: <the same four paths>
   Validation: <absolute path of validation.md>
   Findings: V1, V3
   Changed: <the spec IDs and sections you changed, for example S2, P2, Scope>
   ```

   Add its text to `validation.md` before `## After`, with its headings as it returns them: `## Re-check`
   and `## Result`. Its Result line is the binding one: the last `## Result` in the file. Each finding
   that is still open becomes a ⚠ row, or its row gets ⚠, so the owner sees it at approval. No second
   re-check. Reason: one round is the rule; the owner can ask for a new full run.
4. Write `## After` in `validation.md`: one line per finding, as in the template. Name every spec line
   ID and section that the fix changed (`changed: S2, P1, Scope`). Reason: `approve` marks those lines
   as not checked by the validator, unless a re-check covered them.
5. Set `stage: validated` in `item.md`, last. Also with open ⚠ rows: approval shows them.
6. Commit the item folder as `conventions.md` says. When `git` fails, go on and say so in one line.

## 7. Tell the owner

Short, in this order. Add at most two lines on the open ⚠ rows.

```
Validation: <binding Result line, word for word>
Not covered: Done rules 3 and 4 (baseline, red first). They run at the build start.   (only with READY)
Fixed: V2 → D7, V4 → D8          (only when there were fixes)
New ⚠ rows: D9                   (only when there are any)
Next: /flow:approve <id>
```

When `/flow:start` called this skill, go back to it with the result. Do not stop for questions.
