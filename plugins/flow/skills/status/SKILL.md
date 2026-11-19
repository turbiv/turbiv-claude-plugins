---
name: status
description: Shows where a flow work item stands - stage, open decision rows, validation result, new Jira comments and the next step - and lists the items when no ID is given. Use for /flow:status, to resume a flow item in a new session, or when the owner asks what is open on an item.
argument-hint: "[item]"
---

# Status

Shows where an item stands and what comes next. A new session uses it to resume.

This skill only reads. It writes no file, makes no commit and calls no tracker. Reason: the owner can run
it at any time, also in the middle of another stage, and nothing changes.

Read `${CLAUDE_PLUGIN_ROOT}/resources/conventions.md` first. It defines the work store, item IDs, stages
and the resume order.

Find the work store as the conventions say, also when the shell is not available.

## Without an item

List the items, newest ID first, at most 10, one line each: `<id> — <stage> — <title>`. Put items that are
not approved first. Give the count of the rest. End with: "Run `/flow:status <id>` for one item."
When the store has no items, say so and name `/flow:start <goal>`.

## With an item

Read in the resume order: `item.md`, then the file of the current stage, then the last end note in
`log.md`. Read `decisions.md`, `validation.md` and `mirror/jira-pull.md` when they exist.

Show this, and leave out a line that has nothing to say:

```
<id> — <title>
Stage: <stage>. Size: <size>. Depth: <depth>. Jira: <KEY | none>.
Open decisions: <n> ⚠ (<D#, D#>), <n> recommended, <n> made by me.
Validation: <READY | NOT READY — high: V#, V#>
New from Jira: <n> comments in the pull of <date>. (Local copy; run /flow:mirror <id> pull to refresh.)
Last note, <date>: <the Next line of the last end note>
Next: <step>
```

Then list each open ⚠ row in one line: `D1 — <decision> — <⚠ line>`. Offer "show the table" for the
other open rows.

Open rows are the rows in `decisions.md` with `Status: open`.

## The next step

| `stage` | Next |
|---|---|
| no value | Intake did not finish. `/flow:start <id>` |
| `intake` | `/flow:research <id>` |
| `researched` | `/flow:plan <id>` |
| `planned` | Open ⚠ rows: they need the owner's answer before the spec; list them. Else `/flow:spec <id>` |
| `specified` | `/flow:validate <id>` |
| `validated` | `/flow:approve <id>` |
| `approved` | The build is a later stage. Nothing to run in version 1 |

## Half-done states

`stage` is written last, so a stage that stopped early shows an older stage. Report each of these in one
line, with the step that finishes it:

- A file of a later stage exists, but `stage` is older. Example: "`spec.md` exists, but the stage is
  `planned`. The spec stage did not finish. Next: `/flow:spec <id>`."
- `stage` names a stage, but that stage's file is missing. Name the file and the skill that makes it.
  Exception: with depth `none`, `researched` has no files.
- `spec.md` has `status: approved`, but `stage` is `validated`. "The approval stopped before its end.
  Next: `/flow:approve <id>` finishes it."
- `stage` is `approved`: compute the spec hash as "Spec hash" in `conventions.md` says. When it differs
  from the hash in
  `approved:`, say "`spec.md` changed after approval." When the command fails or the hash is
  `unavailable`, say in one line that the hash was not checked.
- The folder has no `item.md`: it is not a work item. Say so.
