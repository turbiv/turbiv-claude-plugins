# flow

Takes a goal to an approved, binding spec. The stages: intake, research, plan, spec, validation and
approval. All design decisions go into one decision table that you can discuss in free text. A fresh
validator checks every spec. Nothing is built before you approve.

The binding design is [`docs/design/pre-implementation-stages.md`](docs/design/pre-implementation-stages.md).
The research behind it is in [`docs/research/`](docs/research/planning-comparison.md).

## Commands

Each stage is its own skill. You can run any stage alone with an item ID. Each one checks that the files
of the stage before it exist, and says what is missing.

| Command | Does |
|---|---|
| `/flow:start <goal> [KEY] [depth=none\|quick\|deep]` | Intake, then runs the next stages. Stops for open questions, a ⚠ row in the plan, and approval |
| `/flow:research <item> [depth]` | Research at the chosen depth |
| `/flow:plan <item>` | Writes `plan.md` and the decision rows; shows a summary of 10 lines or fewer |
| `/flow:spec <item>` | A fresh subagent writes `spec.md` and returns its guesses as rows |
| `/flow:validate <item \| path to a spec>` | A fresh, read-only subagent checks the spec: `READY` or `NOT READY` |
| `/flow:approve <item>` | Shows the plan summary, the Done lines and the decision table; records your approval |
| `/flow:status [item]` | Stage, open rows and the next step. Use it to resume in a new session |
| `/flow:mirror <item> pull\|push` | Runs the tracker connector. `push` is version 2 |

`<item>` is the item ID, or a unique part of it.

## Replies at a stop

- `ok` accepts the recommended rows and the rows "made by me". It never accepts a ⚠ row.
- Answer a ⚠ row by name: `D1 ok` (the recommendation) or `D1 B` (option B).
- `D4: <text>` changes a row. `explain D2` starts a discussion of that row.
- `skip` or `no questions` at intake ends the questions.

## Where the files go

Work items go to `~/git/turbiv-claude-plugins/work-items/<yyyymmdd>-<slug>/`. To use another folder, set
`FLOW_WORK_ITEMS` in the `env` block of `~/.claude/settings.json`:

```json
{
  "env": {
    "FLOW_WORK_ITEMS": "/path/to/work-items"
  }
}
```

These permission rules stop the prompts for the shell commands the skills run: `Bash(printenv FLOW_WORK_ITEMS)`,
`Bash(printenv EVAL_FLOW_WORK_ITEMS)`, `Bash(git log:*)`, `Bash(git -C:*)`, `Bash(tail:*)`, `Bash(shasum:*)`.
Also add the work store to `permissions.additionalDirectories`; without it, Claude Code asks before
`tail` reads `spec.md` in a folder outside the session's repo. Each skill also works without the shell,
and says what it skipped.

The plugin never writes into its own folder or the plugin cache. Each stage commits its item folder, and
only that. It never pushes.

## Version 1 limits

- Local files, plus a Jira read at intake (`/flow:start <goal> KEY`) and on `/flow:mirror <item> pull`.
- No Jira writes. `/flow:mirror push` only says "version 2". Use your own hook if you
  want Jira writes blocked.
- No hooks. The "nothing built before approval" gate is in the skill text only.
- The spec writer and the tracker connector can write files. Their limits (the item folder, `mirror/`)
  are in their instructions. Claude Code does not enforce them.

## How it is built

- `skills/<stage>/SKILL.md`: one short skill per stage.
- `agents/`: `repo-researcher`, `outside-researcher`, `spec-writer`, `spec-validator`, `tracker-jira`.
  Skills dispatch them as `flow:<name>`.
- `resources/conventions.md`: the work store, item IDs, folder layout, stages and writing style.
  `resources/rules/`: `sizes.md`, `done-rules.md`, `decision-table.md`. `resources/templates/`: one
  template per item file. Skills point to these files and never copy them.
- `docs/design/`, `docs/research/`: the design and the research, moved here from
  `turbiv-agentic-workflow` on 2026-11-18.

## Licence

`skills/start` is a fork of the superpowers `brainstorming` skill, v7.0.2, by Jesse Vincent, under the
MIT licence. The licence text for the forked parts is in [`LICENSE-superpowers`](LICENSE-superpowers).
