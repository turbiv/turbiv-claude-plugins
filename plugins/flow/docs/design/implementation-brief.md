# Implementation brief: `flow` plugin, version 1

2026-11-18. For the session that builds version 1. The design is agreed with the owner.

## Split into sessions (owner, 2026-11-18)

The owner wants each category built by its own session, with fresh context. Each session touches only its own files.

| Session | Builds | Starts |
|---|---|---|
| A `flow-build` (foundation) | `plugin.json`, marketplace entry, `resources/` (templates, rules, conventions), moved docs, `work-items/`, README, licence | First |
| B intake and research | `skills/start`, `skills/research`, `agents/repo-researcher.md`, `agents/outside-researcher.md` | After A, from A's branch |
| C plan and spec | `skills/plan`, `skills/spec`, `agents/spec-writer.md` | After A, from A's branch |
| D validation | `skills/validate`, `agents/spec-validator.md` | After A, from A's branch |
| E approval, state, tracker | `skills/approve`, `skills/status`, `skills/mirror`, `agents/tracker-jira.md` | After A, from A's branch |
| F evals | `evals/`, `docs/research/evals.md` | Research now; writes evals after B–E |
| G integration review | A fresh review of the whole plugin against the design, plus the dry runs | After B–E are merged |

## Read first

1. `docs/design/pre-implementation-stages.md` (this folder). It is binding. Sections 2, 5, 6, 7, 9, 10 and 12 matter most.
2. `research/planning-comparison.md` for why the base is superpowers brainstorming.
3. The installed plugins as structure examples (read only):
   - superpowers brainstorming: `~/.claude/plugins/cache/superpowers-marketplace/superpowers/<version>/skills/brainstorming/` (`SKILL.md`, `builder-check-prompt.md`). This is the base to fork. MIT licence.
   - The owner's own plugins: `~/git/turbiv-claude-plugins/plugins/planner` and `plugins/jira-guard`.
   - EGM agents (`omitClaudeMd`, read-only tools): `~/.claude/plugins/cache/egm/`.

## Build

1. **Create the plugin** at `~/git/turbiv-claude-plugins/plugins/flow/`, with the layout of design section 12. Add it to `.claude-plugin/marketplace.json`.
2. **Move the design and research** from `~/git/turbiv-agentic-workflow/` into `plugins/flow/docs/design/` and `plugins/flow/docs/research/`. Fix the relative links. Leave the old folder in place; the owner decides when to delete it.
3. **Create `work-items/`** at the repo root, with a short README.
4. **Skills** (all user-invocable; each one works alone with an item ID): `start`, `research`, `plan`, `spec`, `validate`, `approve`, `status`, `mirror`.
   - `start` forks superpowers brainstorming: keep what design section 2.2 keeps, change what it changes, drop what it drops.
   - Shared rules and templates go in `resources/`. Skills point to them and never copy them.
   - Keep each skill short. Plain words, reasons next to rules, no CAPS-lock "MUST" style.
5. **Agents:** `repo-researcher`, `outside-researcher`, `spec-writer`, `spec-validator`, `tracker-jira`, with the tool lists of design section 9.
6. **Version 1 scope:** all stages with local files, plus a Jira **read** at intake. No Jira writes in version 1. `mirror push` exists only as a stub that says "version 2".
7. **No new hooks.** `jira-guard` stays as it is.
8. **The work store path** is one setting with the default `~/git/turbiv-claude-plugins/work-items`. Never write to the plugin cache.

## Rules for this session

- Work on a branch in `~/git/turbiv-claude-plugins`. The repo has uncommitted changes in `plugins/jira-guard/` that are not yours: do not touch, stash or commit them.
- Commit your own files only. Do not push or open a PR until the owner says so.
- Do not write to Jira.
- Evals are **not** your task. A separate session researches and writes them in `plugins/flow/evals/`. Do not create that folder.
- When a design rule is unclear or wrong in practice, ask the owner. Do not change the design silently.

## Done when

- `claude --plugin-dir ~/git/turbiv-claude-plugins/plugins/flow` (or the local marketplace) loads the plugin, and `/flow:start`, `/flow:validate` and `/flow:status` show up. [person checks]
- Every skill and agent of design section 12 exists. `plugin.json` lists the agents.
- `/flow:validate <path>` runs on a sample spec and returns `READY` or `NOT READY` with findings in the format of design section 5.4.
- One dry run of `/flow:start` on a small goal reaches the approval message with a plan summary of 10 lines or fewer and one decision table. [person checks]
- Design and research files are moved, and their links work.
- An end note in the session lists what was built, what was skipped, and every place where the build had to decide something the design did not say.
