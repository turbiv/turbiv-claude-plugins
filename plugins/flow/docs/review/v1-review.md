# `flow` version 1: review (session G)

- **Date:** 2026-11-19.
- **Reviewed:** `plugins/flow/` at `8df7ac0` (branch `claude/flow-plugin-v1-22b082`). Not `evals/`.
- **Against:** `docs/design/pre-implementation-stages.md` (binding) and `docs/design/implementation-brief.md`.
- **Method:** a full read of every skill, agent and resource; `claude plugin validate`; session D's two
  samples; two trial runs of `/flow:start` (size S and size M) with stream-json traces; a Jira pull probe;
  a resume probe. Session F's eval findings (`F-evals-findings.md`) are folded in and marked "(F)".
- **Claude Code:** 2.1.327. Main model `claude-opus-5-5`, effort xhigh (the owner's defaults).
- **Code under test in the runs:** `8df7ac0` plus the three fixes of section 3. G-1 was in place before
  the first trial. G-10 and G-15 went in during S turn 1, before any trial reached the spec stage.
- **`claude plugin validate plugins/flow`:** passed. Advice only: the README has no install line.
- **Traces and item folders:** `G-review-runs/` in the shared notes folder of this session group.

## 1. Summary

The plugin works end to end. Both trials went from a goal to an approved spec. All hand-offs worked, and
every stop happened where the design puts it. The key rules held in every run: no picker dialogs, no Jira
call, no write outside the item folder, and a plain "ok" never accepted a ⚠ row. The spec writer and the
validator saw only their fixed inputs. The validator found real defects in the M spec.

Three problems matter most:

1. **The work-store lookup could not be allowed** (fixed). Its shell variables make Claude Code ask or
   deny every time. When denied, the skills ignore `FLOW_WORK_ITEMS`.
2. **Cost and time are high for the size** (G-2). S: $9.68 and 29 minutes. M: $15.67 and 45 minutes.
3. **The approval table is long, and an S spec is heavy.** S: 14 rows; M: 18 rows. Most rows are about how
   to check, not what to build. The S spec has a 60-line Python script as a Done check. Session F saw
   the same (7 guess rows from a two-step plan).

| Owner requirement | S | M |
|---|---|---|
| No picker dialogs (0 `AskUserQuestion` calls) | yes | yes |
| Open questions only when needed | 1 question, needed | 0 questions. "Visible" was unclear and became ⚠ rows D2 and D3 (G-6) |
| Plan summary of 10 lines or fewer | 10 lines | 9 lines |
| One table, a recommendation in every row, ⚠ rows say what they change | yes | yes |
| ⚠ rows need a named answer | "ok" refused; "D3 ok" accepted | answered by name |
| Spec written by the spec-writer subagent | yes | yes |
| Validator always runs, READY or NOT READY | READY | NOT READY, scoped re-check, open finding became ⚠ row D17 |
| Nothing written outside the item folder before approval | yes (git status unchanged) | yes |
| No Jira write | yes (0 Atlassian calls) | yes |

## 2. Findings

Severity: **high** = a stage does not work as designed, or an owner rule breaks. **medium** = a gap a run
can hit. **low** = a small gap or a doc mismatch. "Fixed" = fixed in this review (section 3). Everything
else is a proposal for the owner.

| # | Sev. | Where | Problem | Evidence | Proposed fix |
|---|---|---|---|---|---|
| G-1 | high | `resources/conventions.md`, Work store | The lookup command holds shell variables. Claude Code says "A variable in this command can't be checked before it runs", so no permission rule can allow it. Interactive: a prompt in every session. Headless or denied: the skill falls back to Glob and `~/git/turbiv-claude-plugins/work-items`, and ignores `FLOW_WORK_ITEMS`. | `runs/probe-status.jsonl` | **Fixed.** `printenv FLOW_WORK_ITEMS`, then Glob for the other two steps. It can be allowed with `Bash(printenv FLOW_WORK_ITEMS)`. Verified with the variable set (`probe-status2`, all trials) and unset (`probe-unset`: exit 1, default path, no denial). |
| G-2 | medium | whole flow | Cost and time are high for the size. Most of it is the spec → validate → approve turn (S: 23 min; M: 34 min). 37–42 % of the cost is billed to `claude-fable-5-2`, the owner's global `advisorModel`, so the trial sessions called the advisor. Other factors: effort xhigh, two runs at the same time, and 13 denied tool calls (a small factor). | Section 5; `modelUsage` in `s5`, `m3` | Design open question 10. Try: `model: sonnet` for the spec writer; fewer guess rows (G-3, G-4); and check whether the advisor should run in flow sessions. Measure again after G-3. |
| G-3 | medium | `skills/spec`, `skills/validate`, `rules/decision-table.md` | The approval table is long. S: 1 ⚠ + 7 recommended + 6 made by me. M: 1 ⚠ + 7 + 10. Every spec-writer guess becomes a row (S: 8, M: 9), and so does every small validator fix (S: 5, M: 10). Most of these rows are about how a Done line checks, not about what gets built. The owner wants short text. (F: 7 guess rows from a two-step plan.) | `store-s/.../decisions.md` D9–D22; `store-m/.../decisions.md` D11–D29 | Keep every row in `decisions.md`. In the chat, show ⚠ rows and real design choices in full. Show guesses about check mechanics and small validator fixes as one line ("8 check details and 5 small fixes made by me; say `show` to list them"). This changes design 7.1. |
| G-4 | medium | `rules/done-rules.md`, `agents/spec-writer.md` | Done rules 1–4 push the writer to build checks. For a layout move (S), it wrote two Python scripts (one is 60 lines) inside `spec.md`. The S spec has 137 lines. This goes against "loose, not vague" and against little ceremony on S. | `store-s/.../spec.md` lines 31–110 | A session line uses a one-line command. When no short command exists, use a person line (`P#`) and say so. For size S, aim for a spec of about one page. This changes design 6.3. |
| G-5 | medium | `skills/approve` step 5.2, `skills/status` | The hash recipe `awk 'n>=2{print} /^---$/{n++}' … \| shasum -a 256` needs approval even with `Bash(awk:*)` allowed: Claude Code does not trust a prefix rule for an awk program. Both trials wrote `sha256:unavailable`. The fallback worked. | `runs/s5.jsonl`, `runs/m3.jsonl` (permission_denials) | Same body, a command that can be allowed: find the line number of the second `---` with Read, then `tail -n +<n+1> spec.md \| shasum -a 256` (not tested here; the S run tried `tail` once, and the allowlist denied it). Put the recipe once in `conventions.md`; `approve` and `status` point to it. F's evals do not match the awk text. |
| G-6 | medium | `skills/start`, Intake steps 6 and 8 | M's goal "make the hit rate visible" can mean different outcomes (logs, metrics, an API). Intake asked nothing. It wrote D2 ("where it shows up") and D3 ("what pays off means") as ⚠ rows from intake. Design 5.0 step 6 says to ask when the goal can mean different outcomes. Step 8 of the skill offers a ⚠ row as an alternative, so the model takes that path. | `runs/m1.jsonl`; `store-m/.../decisions.md` D2, D3 | A reading that would become a ⚠ row with `Source: intake` is a question to ask, one at a time, unless the owner said "skip". |
| G-7 | medium | `skills/start`, Questions (F) | Intake lists possible readings before it asks why ("'Better' could mean real content, a nicer look or more structure"). This happened in 8 of 10 eval runs. The skill says: "Until you know why the owner wants it, give no example answers." Many questions also join two asks with "and". In the S trial the question was clean. | F case 02, grader `no-example-answers` | Move the rule into the play-back step too: the play-back states one reading, never a list. Add "one ask per question; no 'and'" to Questions. Rerun F case 02. |
| G-8 | medium | `skills/start`, End of intake | When intake asks no question, the owner never sees the play-back or the depth before the plan. In M, the first owner-facing message was the plan stop. The design says the message states the size and the depth (5.0 Stop). | `runs/m1.jsonl` (main-session text lines) | Put the 3-line play-back and `Size … Research …` at the top of the next stop message, or send them before `flow:research` starts. |
| G-9 | medium | resources, work store step 2 | `work-items/` is tracked at the root of `turbiv-claude-plugins`. A session in any worktree of that repo finds `./work-items/` and writes items onto that worktree's branch, not the main checkout. | `conventions.md` step 2; `work-items/README.md` is tracked on the flow branch | Read an eval-only variable instead of step 2 (for example `EVAL_FLOW_WORK_ITEMS`, relative to the working folder), or skip step 2 when the folder is the plugin repo. The owner decides; F's needs are in `F-evals-build-asks.md`. |
| G-10 | medium | `skills/validate`, step 1 | By item, `validate` checked only that the files exist, not `stage`. After a new plan (`planned`), a stale `spec.md` could reach `validated`. The skill also had no `Stop:` last line on a stop. | static | **Fixed.** Stage check (`specified`, `validated`; `approved` = check only), a `Stop:` line, and `validate` added to the empty-stage sentence in `conventions.md`. Tested: the S item copied with `stage: planned` stopped with `Stop: … run /flow:spec … first` and wrote nothing (`runs/g10.jsonl`). |
| G-11 | medium | `agents/tracker-jira`, intake Jira read | Not tested live. Headless, no Atlassian server was connected (claude.ai connector `needs-auth`), so the agent replied `FAILED … no Jira tools in this session`. It wrote nothing and committed nothing, as designed. F proved the mocked path. | `runs/jira-pull.jsonl` | The owner runs `/flow:mirror <id> pull` once, interactively, on a real key. |
| G-12 | low | `skills/plan` step 6, `skills/approve` | S showed the plan summary reworded (bold, "Key facts" and "More: plan.md" left out) at both stops. The skill says "as it is in plan.md". M showed it word for word in a code block. | `runs/s2.jsonl`, `runs/s4.jsonl` | Say "in a code block, word for word". |
| G-13 | low | `skills/mirror` step 5 (F) | Rewords the agent's reply ("Pulled TEST-1 from Jira." instead of `PULLED TEST-1`). | F case 03 | "Show the agent's first line word for word". |
| G-14 | low | `skills/research`, `skills/plan` | Stage skills ran shell reads beyond git (`python3 -c "import iterm2"`, `cat`, `find`) and, in M, the AWS docs MCP tools. All were denied by the trial allowlist. Interactive use gets a prompt each time. Nothing wrote. | `permission_denials` in `s2`, `m1` | Read the code with Read, Glob and Grep; use the shell only for `git log`. |
| G-15 | low | `resources/templates/spec.md` | The Facts line had no `checked\|unchecked`, unlike `conventions.md`. | static | **Fixed.** |
| G-16 | low | design 6.2 | The design's P1 line ("The owner reads the draft pull request") differs from the template's pass-or-fail P1 (A's change in `8df7ac0`, after D's note). | static | Update design 6.2 to the template text. |
| G-17 | low | `agents/tracker-jira.md` | `model: sonnet` is in no hand-over note or design row. | static | Record it as a decision (design open question 10). |
| G-18 | low | `rules/done-rules.md` rule 2 | M's Done lines run `./run-tests.sh`, which starts a Docker container. Rule 2 names repo writes, deploys and installs, not side effects such as containers. The validator did not flag it. | `store-m/.../spec.md` S1–S8 | Decide whether a test run that starts a local container counts as "reads only", and write it into rule 2. |
| G-20 | low | `skills/start`, run loop | In chained turns, `research`, `spec` and `validate` emitted no closing `Next:` line and no one-line report. `start` went on because `stage` moved, so the hand-off worked. But the owner saw no progress line between stops (see G-8). | `runs/s2`, `s4`, `m2`: only `plan` printed its `Next:` / `Stop:` line | `start`: after each stage skill, print that skill's one-line report and its last line. |
| G-21 | low | `skills/validate` step 6, `skills/approve` | After `READY`, the small fixes changed the S spec (3 new Scope lines, P1–P5 and N1 text) with no re-check. The approval message did not mark those lines. `approve` marks only lines changed at approval. | `store-s` git diff `97063d6..970928c` on `spec.md` | In the approval message, mark Done and Scope lines changed after the validator ran: "the validator has not checked this line". |
| G-19 | info | environment | Superpowers stayed on in the trials: the owner's guard hook blocks `--settings`, so it could not be turned off per session. No superpowers skill ran in any trial. Design open question 3 stays open. | init events; 0 `superpowers:*` Skill calls | Turn it off per repo in `.claude/settings.json` (decision 18). |

## 3. Fixes made in this review

| File | Fix | Finding |
|---|---|---|
| `resources/conventions.md` | Work-store lookup: `printenv FLOW_WORK_ITEMS`, then Glob; reason and the permission rule next to it | G-1 |
| `skills/validate/SKILL.md` | Stage check by item; `Stop: <reason>` as the last line on a stop | G-10 |
| `resources/templates/spec.md` | Facts line: `<date> — checked\|unchecked` | G-15 |

Nothing else changed. The other findings change behaviour or the design, so they are proposals. Effect on
F's evals (branch `claude/flow-evals-2afc1c`, `5051789`): none expected. The evals call `validate` by path
only, run without a shell (Glob path, unchanged), and no grader matches the old lookup command.

Static checks that passed:

- Every skill and agent of design section 12 exists. `plugin.json` lists the 5 agents.
- Tool lists match design section 9: researchers, spec writer, validator (`omitClaudeMd: true`), and
  `tracker-jira` (Jira read tools only, under 2 fixed prefixes; Read and Write).
- Every `${CLAUDE_PLUGIN_ROOT}/resources/…` path in the skills exists. Skills point to `resources/` and do
  not copy the rules. Exceptions: the hash recipe (G-5) and the fact format in the researchers (B9).
- No skill or agent names `AskUserQuestion` (except to forbid it) or a Jira write tool.
- The `Next:` / `Stop:` contract is the same in `start`, `research`, `plan`, `spec`, `approve` and now
  `validate`. An empty `stage` is handled in every stage skill and in `status`.
- The decision-table format, K1/K2, ⚠ lines and reply rules in `rules/decision-table.md` match design 7.

## 4. Samples (session D), re-run

`/flow:validate <path>`, from the worktree, after A's edits to the samples.

| Sample | Expected | Result | Cost, time |
|---|---|---|---|
| `deploy-done-line` | NOT READY | `NOT READY — 2 high findings: V1, V2`. V1: S3 `make live-check` deploys (rule 2; the validator opened the Makefile). V2: nothing says who makes the page live. 1 low. | $1.12, 2.7 min |
| `deploy-done-line-clean` | READY | `READY`, no findings shown. The new P1 got no rule-1 finding. | $1.23, 3.6 min |

In both runs the validator used only Read and Glob. The `Agent` input held only the fixed fields, with the
resources path substituted. Nothing was written.

## 5. Trial runs

Both runs: `claude -p --plugin-dir <worktree>/plugins/flow`, a narrow allowlist (section 7), turns
driven with `--resume`. Costs are the cumulative `total_cost_usd` of the session. Times are the sum of the
turns' wall times.

### S: `spotify-iterm2`

Goal: "Show the elapsed and total time (m:ss) next to the progress bar in the Spotify panel."
Store: a git repo (commit path).

| Turn | Owner said | What happened | Wall |
|---|---|---|---|
| 1 | the goal | Read the code. Found that the times already show, on a row under the bar. Asked one open question: what should be different? | 95 s |
| 2 | "Put them on the same row as the bar … one row shorter. Nothing else changes." | Intake finished (D1, D2 owner rows), quick research (12 facts), plan. ⚠ stop: D3 (art size changes against "nothing else changes") and 5 rows made by me. | 193 s |
| 3 | "ok" | Accepted D4–D8. Refused D3: "ok doesn't count as an answer to it". | 27 s |
| 4 | "D3 ok" | Spec writer (8 guesses → D9–D16), validator `READY` with 6 findings (1 became ⚠ D17, 5 fixed as rows), approval message. | 1373 s |
| 5 | "D17 ok, ok" | Approved. `sha256:unavailable` (G-5). `log.md`, `stage: approved`, commit. | 79 s |

Total: **$9.68** (Opus $6.14, advisor $3.55), **29.5 min**, 4 owner replies. One commit per stage, 7 in all.

### M: `shop-price-tools`

Goal: "Make the price cache hit rate visible, so service owners can tell whether the cache layer pays off."
Store: a plain folder (skip-commit path).

| Turn | Owner said | What happened | Wall |
|---|---|---|---|
| 1 | the goal | No question (G-6). Quick research, plan. ⚠ stop: D2 (where the rate shows), D3 (what "pays off" means), D5 (on by default), 1 recommended, 5 made by me. | 583 s |
| 2 | "D2 ok, D3 ok. D5 B … ok for the rest." | `plan.md` changed to match D5 B. Spec writer (9 guesses → D11–D19). Validator `NOT READY`: V1 `make test` writes (`npm ci`), V2 a wrong fact about publishing. Fixes, scoped re-check: V1 closed, V2 open → ⚠ D17 (version bump). Approval message. | 2053 s |
| 3 | "D17 ok, ok" | Changed 4 spec lines for D17, marked the new S10 "not checked by the validator", approved. `sha256:unavailable`. | 57 s |

Total: **$15.67** (Opus $9.07, advisor $6.61), **44.9 min**, 3 owner replies. The validator's two high
findings were real defects. Without it the spec would have had a writing Done command and a wrong publish step.

### Checks from the traces (both runs)

- `AskUserQuestion` calls: 0. Atlassian calls: 0. `superpowers:*` skill calls: 0.
- Spec writer: read only the item folder and the resources; wrote only `spec.md`.
- Validator: read only `spec.md`, `decisions.md`, `validation.md` (re-check), the rule files and repo files.
  Its `Agent` input had the fixed fields only.
- `git status` of `spotify-iterm2`, `shop-price-tools` and the main `turbiv-claude-plugins` checkout: the same
  before and after.
- Hand-offs: `start` went on after each stage and ended the turn at each stop, as the contract says. In
  chained turns only `plan` and `approve` printed their last line; `start` read `stage` (G-20).
- Bash: every command was a read (`git log`, `git show`, `printenv`, `cat`, `find`, `ls`, `python3 -c
  "import iterm2"`). 13 calls were denied in all, each a read. No Write or Edit outside the stores, in the
  main session or a subagent.
- Resume probe: worked (section 8).

## 6. Hand-over decisions of sessions A to E

Verdict: **accept** = keep as built. **owner** = needs the owner's word. Most are sound.

| Session, # | Decision | Verdict |
|---|---|---|
| A1 | Work store is the env var `FLOW_WORK_ITEMS`, not `userConfig` | Accept. Lookup command fixed (G-1) |
| A2 | Added `resources/conventions.md` | Accept |
| A3 | Item ID `<yyyymmdd>-<slug>`, `-2` on a clash, unique part accepted | Accept |
| A4 | Commit `-- <id>` only, never push, skip when not git | Accept. Both paths worked in the trials |
| A5 | Fourth row kind "owner" | Accept. Used well in both trials |
| A6 | "After" part in `validation.md` | Accept |
| A7 | No `license` field in `plugin.json` | owner |
| A, `8df7ac0` | P1 rewritten as pass-or-fail | Accept; update design 6.2 (G-16) |
| B1 | Empty `stage` while intake runs | Accept |
| B2 | `start` model-invocable | Superseded: `disable-model-invocation: true` (M4). `/flow:start` typed by the owner works |
| B3 | Dropped the brainstorming spike | Accept |
| B4 | Short traps table | Accept |
| B5 | `start <id>` resumes only for a one-word, date-led argument | Accept |
| B6 | Intake rows get their kind from K1/K2 | Accept, but see G-6: it lets intake skip a needed question |
| B7 | Jira read at intake through `flow:mirror` | Accept |
| B8 | Deep research blinded; N and N+100 fact ranges | Accept. Not run in the trials (no deep item) |
| B9 | Fact format copied into both researchers | Accept (the outside researcher has no Read) |
| B10 | Researchers: no `model:`, no `omitClaudeMd` | Accept |
| B11 | Repo researcher skips `work-items/` | Accept |
| B12 | No internal names in web queries | Accept |
| B13 | A rerun of `research` keeps the later stage | Accept |
| B14 | Ask a yes for deep only when it comes from the size default | Accept |
| B15 | Research formats | Accept; now templates in `resources/` |
| C | `plan` and `spec` never chain; `Next:` / `Stop:` contract | Accept. Worked in every turn |
| C | `U#` rows are always "⚠ changes the request" | Accept |
| C | `plan.md` has no front matter | Accept |
| C | `spec` stops on open ⚠ rows from intake or plan | Accept |
| C | `plan` on `planned` with an open ⚠ row shows the stop again | Accept. Closes E's open point |
| C | Spec writer reads only the item folder and resources | Accept. Verified in traces |
| C | `plan` on an empty `stage` stops; on `intake` with depth `none` it goes on | Accept |
| C | `G#` markers in `spec.md` become `D#` after the rows are added | Accept. Worked in both trials |
| D1 | Two modes: by item, by path (check only) | Accept |
| D2 | Repo paths: arguments, then `repos:`, then the working folder | Accept |
| D3 | Size `unknown` | Accept |
| D4 | The main session compares the restatement | Accept |
| D5 | Closed list of `high` findings | Accept |
| D6 | Small fix = K1 no and K2 no | Accept. But each fix also becomes a row the owner reads (G-3) |
| D7 | Re-check covers all high findings | Accept. M: V2 stayed open and reached the owner as ⚠ |
| D8 | `stage: validated` also on NOT READY | Accept |
| D9 | Layout of `validation.md` after a re-check | Accept |
| D10 | Rule 2: open the make target | Accept. Found `live-check` and `make test` |
| D11 | A URL fact is `low` | Accept |
| D12 | Sample IDs are folder names | Accept |
| E | Two entry points for the pull | Accept |
| E | No pull hash in `jira.json` | Accept (owner's M3, in design 8.1) |
| E | `mirror push` is a one-line stub | Accept |
| E | `approve` makes no tracker call | Accept |
| E | Hash recipe with awk | Change (G-5) |
| E, open | Do agent `tools:` lists reach deferred MCP tools? | Answered by F: yes |
| E, open | Owner answers at `planned` in a new session | Closed by C's `plan` rule |
| E | `tracker-jira` `model: sonnet` | owner (G-17) |

## 7. How the runs were made

- `FLOW_WORK_ITEMS` pointed at scratch stores: `store-s` (git) and `store-m` (plain).
- `--dangerously-skip-permissions` was refused by the auto-mode classifier, and `--settings` by the owner's
  guard hook. The runs used `--permission-mode default` with this allowlist: Read, Glob, Grep, Skill, Agent;
  Write and Edit under the scratch folder only; `Bash(git log:*)`, `Bash(git -C:*)`,
  `Bash(printenv FLOW_WORK_ITEMS)`, `Bash(awk:*)`, `Bash(shasum:*)`, `Bash(ls:*)`. Every other tool call
  was denied and shows in `permission_denials`. This also proves that no write outside the store was
  possible, and the trace shows none was tried.
- Scripts: `run.sh` (one turn) and `summ.py` (trace summary) in `G-review-runs/`.

## 8. Resume probe

`/flow:start 20261119-price-cache-hit-rate` in a new session, on the approved M item: it found the item by
ID, read `item.md`, `spec.md` and `log.md`, changed nothing, and said the item is approved and nothing is
built. It also listed the open gaps (no commits, hash unavailable, unchecked metric format). $0.53, 35 s.
`runs/resume-m.jsonl`.

## 9. Fixes applied after the owner accepted the review

Commit `febf150`, plus the follow-up commit that adds this section.

| Finding | Done | Where |
|---|---|---|
| G-3 | yes | `About: build\|check` on each row; the chat folds open check rows and small validator fixes into one line; a row with no `About:` counts as build. `decision-table.md`, `templates/decisions.md`, `spec`, `validate`, design 7.1 |
| G-4 | yes | Done rule 13 (one-line command, else a person line; S spec about one page). `done-rules.md`, `spec-writer`, `spec-validator`, design 6.3 |
| G-5 | yes | One recipe in `conventions.md` ("Spec hash": Read, then `tail \| shasum`); `approve` and `status` point to it. See the note below |
| G-6, G-7, G-8 | yes | `start`: a reading that would get ⚠ is a question; one reading, never a list; one ask per question; `plan` and `approve` repeat the play-back at the next stop when it was not shown |
| G-9 | yes, with one choice | `EVAL_FLOW_WORK_ITEMS` (relative to the working folder) replaces `./work-items/` on the shell path. Without a shell, Glob for `./work-items/` stays: no variable can be read there, and F's cases grant no Bash. Session F updated its cases (`4d9a32c`) |
| G-12 | yes | Plan summary in a code block, word for word (`plan`, `approve`) |
| G-13 | yes | `mirror` shows the agent's lines word for word |
| G-14 | yes | `research` and `plan` read with Read, Glob, Grep; shell only for `git log` and `git show` |
| G-16 | yes | Design 6.2 P1 = the template's P1 |
| G-17 | yes | Model routing table in `conventions.md` and design 9 |
| G-18 | yes | Rule 2: local, throw-away test resources count as reads only. `done-rules.md`, design 6.3 |
| G-20 | yes | `start` shows each stage's report and last line |
| G-21 | yes | `validate` names the changed lines in "After"; `approve` marks lines the validator did not check |
| Models | yes | `model: sonnet` on both researchers and the spec writer; the validator inherits; `tracker-jira` stays sonnet |
| G-2, G-11, G-19 | no | Measured below (G-2); G-11 needs the owner's interactive pull; G-19 needs a per-repo setting |

**G-5 note.** The new recipe is allowed by `Bash(tail:*)` and `Bash(shasum:*)` only when the work store is
one of the session's working folders. Else Claude Code asks before `tail` reads a file outside them. Tested:
without `--add-dir` it was denied; with it, it ran and gave the hash computed by hand. The README and
`conventions.md` now say to add the store to `permissions.additionalDirectories`.

### S re-run after the fixes

Same goal, same answers, a new git store, `--plugin-dir` at `febf150`. Allowlist as in section 7, with
`awk` replaced by `tail`, plus `git show` and `printenv EVAL_FLOW_WORK_ITEMS`.

| | First S run | Re-run |
|---|---|---|
| Owner replies | 4 (answer, "ok", "D3 ok", "D17 ok, ok") | 2 (answer, "ok") |
| Intake question | 1, clean | 1, clean: one ask, no list of readings |
| ⚠ stop after the plan | yes (D3: art size) | no: the plan kept the art size, as "nothing else changes" says |
| Approval table | 14 rows shown | 6 rows shown + 1 line: "Also 4 check details and 10 small validator fixes" |
| Rows in `decisions.md` | 22 | 23 (spec-writer guesses: 8 → 3) |
| `spec.md` | 137 lines, a 60-line script | 58 lines, every command on one line |
| Validator | READY, 6 findings | NOT READY (2 high: `py_compile` writes; a missing ⚠), fixed, re-check READY |
| Hash | unavailable (awk) | unavailable (store not a working folder; see G-5 note) |
| Cost | $9.68 (Opus 6.14, advisor 3.55) | **$7.02** (Opus 4.37, advisor 2.54, Sonnet 0.12) |
| Time | 29.5 min | **21.5 min** (124 s + 1132 s + 34 s) |

The approval table shows 6 rows instead of 14, the spec is less than half as long, and the cost is 27 %
lower. Time is still high for an S task: the spec → validate → approve turn took 19 minutes. The advisor
is still 36 % of the cost. Traces: `G-review-runs/rerun/`.

Still to run after the merge (session F): eval cases 10 to 12 and the smoke set (about $2, command in
`evals/README.md`). Their approve fixtures write rows with no `About:` line, and those rows count as
`build`.
