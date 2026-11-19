# `flow`: development notes

For an agent that develops this plugin. How version 1 was designed and built (2026-11-18 to 19), how it
went, and what to apply next time. Facts carry their source. The human overview is
[`overview.md`](overview.md).

## 1. State and where things are

Nothing is pushed. Three heads are not merged into one branch yet:

| Branch | Head | Holds |
|---|---|---|
| `claude/flow-plugin-v1-22b082` | `8df7ac0` | Version 1: A's foundation, B–E merged, A's shared-file fixes |
| `claude/flow-g-review-f5ba47` | `e386a96` | `8df7ac0` + G's review (`docs/review/v1-review.md`) + accepted fixes (`febf150`, `e386a96`). Newest plugin code. Final |
| `claude/flow-evals-2afc1c` | `4d9a32c` | `8df7ac0` + `evals/` + `docs/research/evals.md`. No run against G's head on record. After the merge, run cases 10–12 and the smoke set (review section 9) |
| `claude/flow-notes-56547d` | — | These notes (based on `8df7ac0`) |

To get one current branch: merge G's branch, then the evals branch, into the plugin branch. Then run
`plugins/flow/evals/static/check.sh` and the smoke set (`evals/README.md`).

| What | Where |
|---|---|
| Binding design | `docs/design/pre-implementation-stages.md` (sections 2, 5–7, 9, 10, 12 matter most) |
| Build brief, session split | `docs/design/implementation-brief.md`, `docs/design/evals-brief.md` |
| Research (workflows) | `docs/research/`; base choice: `planning-comparison.md`, rubric: `planning-rubric.md` |
| Research (evals) | `docs/research/evals.md` on the evals branch |
| Review, findings G-1 to G-21 | `docs/review/v1-review.md` on G's branch |
| Evals: cases, commands, last results | `evals/README.md` on the evals branch |
| Shared contract for skills | `resources/conventions.md`, `resources/rules/`, `resources/templates/` |
| Session notes A–F, G's traces and trial stores | `~/Library/Application Support/Claude/side-session-notes/local_c3e0e0c8-f22e-4839-8b92-634e19959697/` (`session-*.md`, `F-*.md`, `F-probe/`, `G-review-runs/`) |
| Coordinator's process history | `~/Library/Application Support/Claude/side-session-notes/local_67364072-6933-4c8c-bbfd-60833f471ca7/process-history-design-session.md` |
| Old pre-move folder | `~/git/turbiv-agentic-workflow/` (the owner decides when to delete it) |

## 2. Process, with the key decisions

1. **Research.** 2 workflows in depth (Elephant-Goldfish Model, superpowers)
   and a survey of 28 others. Source: process history, step 1.
2. **First design, from scratch.** Stages intake → research → plan → spec → validate → approve, one
   decision table, local files as the source, Jira as a mirror.
3. **Owner corrections** (design section 10 has the full log):
   - Size comes from what the goal asks, not its length (decision 1).
   - The validator always runs (decision 2). It was optional.
   - "Start from popular, tested workflows." → 3 more deep dives (Spec Kit, cc-sdd/Kiro, HumanLayer), a
     12-requirement rubric, a scored comparison. Superpowers brainstorming ranked first (4 fit / 7 partly /
     1 no). The design became a fork of it (decision 6). Reason: tested against pressure scenarios, known
     to the owner, best fit. Criticism of superpowers targets the bootstrap and the implementation skills,
     not brainstorming (`planning-comparison.md`, "Criticism").
   - Open questions one at a time in chat are fine; picker dialogs are not (decision 7).
   - Every row gets a recommendation; a row that changes the request or scope gets ⚠ and needs a named
     answer (decision 8, 14).
   - One stop at approval, plus a stop after the plan only for a ⚠ row (decision 4).
   - The spec is loose: areas, not function names or paths (decision 11).
   - Everything in `turbiv-claude-plugins`; work items at the repo root `work-items/`, because an install
     copies the plugin folder into the cache (decisions 15, 16).
   - Version 1: local files plus a Jira read; no Jira writes; no hooks (decisions 19, 20).
4. **Build split by category, for fresh context** (owner; `implementation-brief.md`). A = foundation
   (`plugin.json`, `resources/`, docs move, README). B = start, research, 2 researchers. C = plan, spec,
   spec writer. D = validate, validator, samples. E = approve, status, mirror, tracker-jira. F = evals.
   G = fresh review and trial runs. B–E ran in parallel worktrees from A's branch. Each owned only its
   files. A merged B–E, then fixed the shared files in one commit (`8df7ac0`: no-Bash store lookup, empty
   `stage`, research templates, `G#`/`U#` sources, pass-or-fail P1, `start` not model-invoked).
5. **Evals (F).** Research first (`docs/research/evals.md`), with a probe of `claude plugin eval`. Then
   static checks plus 13 cases.
6. **Review (G).** Full read, sample re-runs, one S and one M trial run with stream-json traces, a Jira
   pull probe, a resume probe. 21 findings. Three small fixes in place (`3585dff`); the rest went to the
   owner as proposals.
7. **Fixes (G, `febf150`), accepted by the owner:** compact approval table with `About: build|check`
   (G-3); Done rule 13, one-line commands, else a person line (G-4, G-18); one hash recipe with `tail`
   (G-5); intake asks instead of writing ⚠ rows, one reading, one ask per question (G-6, G-7, G-8, G-20);
   `EVAL_FLOW_WORK_ITEMS` (G-9); word-for-word summary and mirror line, read with Read/Glob/Grep, mark
   lines changed after validation (G-12 to G-16, G-21); model routing. Follow-up `e386a96`: a row with no
   `About:` counts as build; add the work store to `permissions.additionalDirectories` for the hash.
   Then an S re-run with the same goal and answers (review section 9).
8. **Model routing** (owner, 2026-11-19): well-scoped work on Sonnet (researchers, spec writer,
   tracker-jira); judgment on the main model, Opus (stage skills, validator with `model: inherit`). Table:
   `resources/conventions.md`, "Models".

## 3. What worked

| What | Evidence |
|---|---|
| Score candidate workflows against the owner's own requirement list | Base choice took one round; `planning-comparison.md` |
| One decision table, recommendations in every row, free-text replies | The owner answered the design table in one line ("U1 B, ok"; process history). Trial replies were one line too (review section 5) |
| "ok" never accepts a ⚠ row | Held in both trials and in eval cases 10, 11 (also under "my manager agreed") |
| Foundation session first, then sessions that own disjoint files | No merge conflicts in 4 merges (`90333c2`–`6d90691`) |
| Sessions report contract gaps in their notes, not fix others' files | B found 2 mismatches in C and E; C and E fixed their own files (`395d981`, `75e3fad`). Gaps in shared files went to A, fixed after merge (`8df7ac0`) |
| `Next:` / `Stop:` last line as the contract between `start` and stage skills | Hand-offs worked in every trial turn (review section 5) |
| Blinded subagents (fixed prompt fields only) | Canary markers never reached the spec writer or validator (eval cases 06, 08; D's traces) |
| Always-on validator | M trial: 2 real high defects (`make test` writes via `npm ci`; wrong publish fact). D: NOT READY 4/4 on the defect sample, READY 5/5 on the clean twin |
| Evals research and a probe before writing evals | Found 3 environment limits early (`F-evals-build-asks.md`); full run $13.29, 9.5 min, 12 of 13 expected to pass |
| Fresh review with real trial runs | Found what static reading missed: cost, table length, a 60-line Python Done check, a prompt on every lookup (G-1 to G-4) |
| Measure the fixes with the same trial | S re-run, same goal and answers: $9.68 → $7.02, 29.5 → 21.5 min, owner replies 4 → 2, table 14 rows → 6 + 1 folded line, spec 137 → 58 lines, guesses 8 → 3. The validator still found 2 real high findings (review section 9) |
| Work kept in the worktree | A PC restart killed background trial runs; the work in the worktree survived (process history) |

## 4. What failed or cost time

| What | Evidence | Lesson |
|---|---|---|
| Designed from scratch first | Owner: "start from tested workflows"; 3 extra research reports | Ask early: adopt or invent? |
| Misread 2 owner preferences | "Sequential questions" (the pain was picker dialogs); the planning guide treated as a conflict | Restate each preference in one line before designing on it |
| Cost and time high for the size | S $9.68 / 29.5 min; M $15.67 / 44.9 min (G-2). 37–42 % billed to the owner's global advisor model, not the plugin. After the fixes S is $7.02 / 21.5 min, but the spec → approval turn still takes 19 min and the advisor is still 36 % | Measure cost in trial runs; check what global settings add |
| Long approval tables | S 14 rows, M 18 rows; F case 06: 7 guess rows from a 2-step plan (G-3) | Fold rows about check mechanics |
| Over-engineered Done checks | S spec 137 lines, a 60-line Python script as a Done check (G-4) | One-line commands, else a person line |
| Intake wrote ⚠ rows instead of asking | M: "visible" became ⚠ rows D2, D3 (G-6) | A rule with an "or" alternative gets the easy path |
| Intake listed readings before the question | F case 02: 8 of 10 replies (G-7) | A rule placed in one section does not cover the lines around it |
| Shell variables in a command | No permission rule can allow it; prompt every session, or denied (G-1) | Use commands that a prefix rule can allow |
| `awk` programs | Need approval even with `Bash(awk:*)`; both trials wrote `sha256:unavailable` (G-5) | Same |
| `./work-items/` lookup | A worktree of this repo finds the tracked folder and writes items onto that branch (G-9) | Never rely on a folder in the cwd of the plugin's own repo |
| Stage skills ran extra shell reads | `python3 -c "import iterm2"`, `cat`, `find`: 13 denials (G-14) | Say "Read, Glob, Grep; shell only for `git log`" |
| Scope sent late | A session started with full scope before the split arrived; the change went as a message | Send the split before starting sessions |

## 5. Rules for future development

1. **Start from a tested workflow.** Score candidates against the owner's requirement list, fork the
   best, and tailor it. Ask "adopt or invent?" before the first draft.
2. **Restate owner preferences first.** One line each, before designing on them. The owner wants short,
   factual text and little ceremony (`conventions.md`, "Writing style"). Use ASD-STE100-like English.
3. **Foundation session first.** It writes the shared contract (`resources/`), the manifest and the
   README. Then category sessions in parallel worktrees, each owning disjoint files. They record contract
   gaps in their notes; the foundation session fixes shared files after the merge.
4. **Contracts in one place.** Skills point to `resources/`; they never copy rules. Exceptions only with
   a reason (the fact format in the researchers: the outside researcher has no Read).
5. **Fresh review with trial runs.** A session that did not build the code. Real `claude -p` runs on one
   S and one M goal, stream-json traces, a narrow allowlist so every denial shows. Read the traces for
   tool calls, cost (`modelUsage`) and `permission_denials`. Scripts: `G-review-runs/run.sh`, `summ.py`.
6. **Commit early.** Commit each logical step. Background runs die on a restart.
7. **Commands a permission rule can allow.** No shell variables, no `awk` programs. (Inferred from G-1: avoid `$(...)` too.) Use
   `printenv NAME`, `git -C <path> …`, `tail`, `shasum`. Prefer Read, Glob, Grep over the shell. Every
   skill must go on without the shell and say what it skipped in one line.
8. **Model routing.** Well-scoped tasks with fixed input on Sonnet; open-ended judgment on Opus (or
   `inherit`). Record each `model:` choice in `conventions.md` and design section 9 (G-17 was a choice
   with no record).
9. **Keep tables and specs short.** A table shows only what the owner must decide. Fold the rest into
   one line, keep it in the file. A Done line is one short command or a person line. An S spec is about
   one page.
10. **Write rules without an easy alternative.** "Ask, or write a ⚠ row" made the model write rows. Say
    what to do, and when the alternative applies ("only after skip"). Put the reason next to each rule;
    no CAPS "MUST".
11. **Evals.** Research and probe the runner before writing cases. Pair each "never" gate with a
    "the skill ran" check. Give each defect case a clean twin. Make forbidden tools exist and fail
    (mocks), or the gate always passes. Use `--judge-model sonnet`. Read the report of a new case before
    trusting it: in the first full run, 2 of 13 failures were grader bugs. Keep scenario text out of
    `skills/`. Run `static/check.sh` after every change.
12. **No AskUserQuestion, ever.** Questions are open, one at a time, one ask each, no example answers
    until the why is known.

## 6. Claude Code facts (tested on 2.1.327, 2026-11-18/19)

| Fact | Source |
|---|---|
| `${user_config.KEY}` default is not substituted with `--plugin-dir`; use an env var | session A notes |
| `` !`cmd` `` in a plugin `SKILL.md` does not run | session A notes |
| `${CLAUDE_PLUGIN_ROOT}` is substituted in skill text | session A notes |
| `@${CLAUDE_PLUGIN_ROOT}/file` attaches a file to a skill; a plain `@file` does not (read, not tested) | session A notes, from the `planner` README |
| An environment hook blocks any Bash command whose text says `settings.json`; use Write/Edit | session A notes |
| A command with a shell variable cannot match a permission rule | G-1, `runs/probe-status.jsonl` |
| `Bash(awk:*)` does not allow an awk program | G-5 |
| `Bash(tail:*)` allows `tail` only on files in the session's working folders (`--add-dir`, `permissions.additionalDirectories`); else it asks | review section 9, G-5 note |
| Keep `disable-model-invocation: true` off stage skills: `start` calls them with the Skill tool (advice, not tested) | session A notes; only `start` has it |
| Eval runs: write only inside the run's cwd, no user settings, only `EVAL_*` env vars, git fails in the macOS sandbox (exit 72) | `F-evals-build-asks.md`, `evals.md` section 4 |
| Eval mocks: `mocks/atlassian/` gives `mcp__atlassian__<tool>`; a subagent with a `tools:` list calls them without ToolSearch; a subagent's Write works | `F-evals-findings.md` |
| Eval graders see subagent tool calls (`parent_tool_use_id`) | `F-evals-build-asks.md` |
| `--case` braces (`{07,08}`) match nothing; two evals started in the same second share one results folder | `evals/README.md` |
| `--dangerously-skip-permissions` was refused by the auto-mode classifier; `--settings` is blocked by the owner's guard hook | review section 7 |
| Superpowers cannot be turned off per session (guard hook); no superpowers skill ran in the trials | G-19 |

## 7. Claude Desktop coordination limits

- A session cannot start a session in another repo from another session's message. The owner must ask in
  chat.
- A proposal card cannot carry another folder.
- A repo must be trusted before a session can start there.
- Messages to a busy session queue until its next tool round.
- Each session's report reaches the starter cut to about 400 characters (this session group's setup).
  Put the result first; leave long findings in the shared notes folder.

Source: process history, "What went wrong", except the last point.

## 8. Costs (measured)

| Run | Cost, time | Source |
|---|---|---|
| `/flow:validate <path>` on a sample | $1.1–1.4, 2.7–3.6 min | D notes; review section 4 |
| Validate by item (Opus parent) | $3.3–4.3 | D notes |
| Trial S, before the G fixes | $9.68 (advisor $3.55), 29.5 min, 4 owner replies | review section 5 |
| Trial M, before the G fixes | $15.67 (advisor $6.61), 44.9 min, 3 owner replies | review section 5 |
| Trial S, after the G fixes | $7.02 (Opus $4.37, advisor $2.54, Sonnet $0.12), 21.5 min, 2 owner replies | review section 9 |
| Resume probe | $0.53, 35 s | review section 8 |
| Evals: full (13 × 3), one of each, smoke | $13.29 / 9.5 min; about $4.70; $1.23 | `evals/README.md` |

S after the fixes: 27 % cheaper, but the spec → validate → approve turn still takes 19 min, and the
advisor is still 36 % of the cost. M was not re-run.

## 9. Open, and not verified in a run

- **For the owner:**
  - G-11: run one real Jira pull by hand (`/flow:mirror <id> pull` on a real key). The headless runs had
    no Atlassian server.
  - G-19: turn superpowers off per repo.
  - G-2: cost. S is still $7.02 and 21.5 min; M was not re-run.
  - Whether the advisor model should run in flow sessions (36 % of the S re-run cost).
  - `plugin.json` licence (A7).
- The hash recipe (G-5) works with the store in `--add-dir`. Both S trials still wrote
  `sha256:unavailable`, because the store was not a working folder.
- Deep research: no trial, no eval case. Research and `status` have no eval case.
- Eval case 02 (no example answers): rerun after the G-7 fix.
- Design open questions (section 11): a gate hook before approval, the Done-status file, spec changes
  during the build, Jira push (version 2).
