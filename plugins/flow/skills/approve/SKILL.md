---
name: approve
description: The approval stop of a flow work item. Shows the plan summary, the Done lines and one decision table, takes the owner's free-text answers, and on approval marks spec.md approved with its SHA-256. Use for /flow:approve <item>, or when the owner answers the approval table of a flow item.
argument-hint: <item> [reply]
---

# Approval

The one stop that always happens. The owner sees the plan summary, the Done lines and every open decision
together, and approves the spec. Nothing is built at this stage. Building comes in a later stage.

Read first, from `${CLAUDE_PLUGIN_ROOT}/resources/`:

- `conventions.md`: work store, item IDs, stages, commits, what to do when git or a hash fails.
- `rules/decision-table.md`: the kinds of row, the table format and the reply rules.

## Arguments

- `<item>`: the item ID or a unique part of it.
- Text after the ID is the owner's reply, for example `ok` or `D1 B`. Show the message of step 3 first,
  then handle the reply as in step 4. Reason: the owner must see what the reply accepts.

## 1. Check the item

When this step stops, end with `Stop: <reason>` as the last line. Reason: `/flow:start` reads the last
line of each stage skill.

1. Find the work store and the item folder, as the conventions say, also when the shell is not
   available.
2. Read `item.md`, then act on `stage`:
   - `approved`: say "Already approved on <date>, sha256 <first 12 characters>." Change nothing. Stop.
   - `validated`: go on.
   - No value: intake did not finish. Say "Run `/flow:start <id>` first." Stop.
   - Any other stage: name the missing file and the skill that makes it, for example "`validation.md` is
     missing. Run `/flow:validate <id>`." Stop.
3. When `spec.md` has `status: approved` but `stage` is still `validated`, an earlier approval stopped
   before its end. Do not ask again and do not compute the hash again. Do steps 5.4 to 5.6 (skip 5.4 when
   `log.md` already has the approval note), and say so in one line.
4. Read `validation.md`. When the result is `NOT READY`, every high finding must have a line in its
   "After" part. A high finding without one blocks approval: name it, say "the validation stage did not
   finish; run `/flow:validate <id>`", and stop. Reason: an unhandled high finding means an implementation
   agent would have to guess.

## 2. Collect

- The plan summary: the first block of `plan.md`, up to and including the line `More: plan.md`.
- The Done lines: every `S#`, `N#` and `P#` line of `spec.md`.
- The open rows: every row in `decisions.md` with `Status: open`. Leave out rows of kind "owner" and rows
  that are already answered.
- A row without K1 or K2 answers is invalid. Show it as "⚠ may change the scope — K1/K2 not answered".
  Reason: a missing check must not let a row pass on "ok".
- When `mirror/jira-pull.md` exists: its new comments. Read the local file only. Do not call Jira here;
  version 1 reads Jira at intake and on `/flow:mirror <id> pull` only.
- Lines not checked by the validator: every spec line ID and section named after `changed:` in the
  "After" part of `validation.md`, unless a `## Re-check` covered it. Reason: the validator read the
  spec before those fixes.

## 3. The message

Keep this order. Leave out a part that is empty.

````
<id> — <title>. Validation: <READY | NOT READY, all high findings handled>.

<the play-back: the lines under "## Reading" in item.md>     (only when this conversation has not shown it)
Size: <S|M|L> — <reason>. Research: <depth>.                 (same condition)

```
<the plan summary, word for word from plan.md>
```

Done when:
S1 <check> — passes when <...>
N1 <check> — passes when <...>
P1 <check> — <how> — <when>
(Mark each line not checked by the validator: "— the validator has not checked this line".)

<the decision table, in the format of rules/decision-table.md, with its folded line>

New from Jira:
- <author>, <date>: <first sentence>

Jira: nothing is sent to Jira (version 1 reads only).
````

- Show the "Jira" line only when the item has a Jira key.
- With no open rows, end with: `No open decisions. Reply "ok" to approve.`
- Never use a picker dialog. The owner answers in free text.

## 4. The owner's reply

Follow the reply rules in `rules/decision-table.md`. On top of them:

- **Approval** needs the word "ok" for the whole table, and a named answer for every ⚠ row. Both can come
  in one reply ("D1 B, ok").
- **"ok" with an open ⚠ row** does not approve. Name the open ⚠ rows in one line and wait. This holds for
  "just approve", "approve all" and every other wording. Reason: a ⚠ row changes the request or the
  scope, so the owner must answer it by name.
- **Record each answer** in `decisions.md` at once: the `Answer:` line, and `Status:` `accepted`,
  `changed` or `delegated by owner`.
- **An option picked from the table** ("D1 B") changes `spec.md` as that option says. Show the changed
  lines. This change needs no extra "ok".
- **A free-text answer that changes the spec**: make the change, show the changed lines (before and after),
  and ask for "ok" once more. An "ok" given before the change does not cover it.
- **A changed or new Done line** gets the note "the validator has not checked this line" in the same
  message. Reason: validation ran on the old text.
- **An answer that creates a new ⚠ row**: add the row to `decisions.md` and show it. It blocks approval
  until it is answered.
- **A question** ("explain D2", "show plan") starts a short discussion. The table stays open.

## 5. On approval, in this order

The order matters: `stage` is written last, so a half-done approval never looks done.

1. **Decisions.** Every row that was open gets its `Answer:` line and its `Status:`. "ok" gives
   `Answer: ok — owner — <date>` and `Status: accepted`.
2. **Spec.** In the front matter of `spec.md`, set `status: approved` and
   `approved: <yyyy-mm-dd> sha256:<hash>`. Do this after the last change to the body.
   - Compute the hash as "Spec hash" in `conventions.md` says. Reason for one recipe: `status` and the
     build stage compute it again in the same way, to find a change after approval.
   - When the command fails, write `sha256:unavailable` and say so in one line. Do not stop.
3. **Tracker.** Version 1 sends nothing. Make no Jira call.
4. **End note.** Add an end note to `log.md` (template: `resources/templates/log.md`; create the file from
   it when it does not exist). `Next:` says "Build is a later stage. Nothing is built yet."
5. **Stage.** Set `stage: approved` in `item.md`. Last.
6. **Commit** the item folder, as the conventions say, with the message `<id>: approved`. When git fails,
   go on and say so in one line.

Then reply in 3 lines or fewer: the item is approved, and the first 12 characters of the hash (or
"hash unavailable"). The last line is `Next: the build is a later stage. Nothing is built yet.`

## Limits

- Write only inside the item folder. Use Edit, or Write the whole file when Edit is not available.
- Change the spec only as the owner's answers say.
- Build nothing: no product code, no scaffolding, no installs.
