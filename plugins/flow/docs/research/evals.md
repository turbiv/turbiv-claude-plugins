# Evals for the `flow` plugin: research

- **Date:** 2026-11-18.
- **For:** session F (evals). Phase 1 is research only. The evals come in phase 2, after the skill branches are merged.
- **Question:** how do we write good evals for Claude Code skills and agents, and which evals does `flow` need?
- **Tags:**
  - [read]: I read the source directly.
  - [read, summarized]: I read it through a fetch tool that summarizes. The wording is a paraphrase.
  - [secondary]: a third-party summary, or another session's research report.
  - [unverified]: my inference, or a claim nobody has tested.
  - [probe]: I tested it with a throwaway plugin on 2026-11-18 (section 4).

## 1. Summary

1. Use three kinds of evals: **static checks** (free, every commit), **`claude plugin eval` cases** (one prompt per run, graded, about 15 cases), and **human review** of the transcripts and the two dry runs.
2. Most `flow` behaviour is testable in one turn, because the state of an item lives in files. A case creates an item folder at a given stage (scaffold), then sends one owner message. This tests the real resume path.
3. Grade with deterministic graders first: `tool_used`, `regex` on the reply or on a file, `file_exists`. Use an `llm` grader only on short text with PASS and FAIL conditions. Use Sonnet as the judge, not the default Haiku.
4. Every negative gate ("never does X") needs a matching positive check ("the skill ran", "the validator said READY on a good spec"). A `max: 0` gate on a tool the run cannot reach always passes.
5. Run most cases with one arm (`--ablation none`). Run with and without the plugin only for the unclear-goal question case, where plain Claude can do the same job.
6. Cost: a full `flow` run should cost about $5–15. A case on its own with `--runs 1` costs well under $1. [unverified estimate]
7. Three things the build must allow, or the evals cannot run (section 8). The probe in section 4 confirmed each one:
   - A case can write only inside its workspace, so the work-store path must be settable to a folder there.
   - git fails in the macOS eval sandbox, so the skills must go on without git or other shell commands.
   - Mocks of an MCP server work, so the Jira read can be tested if the tool names match.

## 2. What makes a good eval

### 2.1 Anthropic guidance

- Start with 20 to 50 simple tasks taken from real failures. Early changes have large effects, so small sets are enough. [read, summarized; A1]
- A good task is one where two experts give the same pass or fail verdict. [read, summarized; A1]
- Test both sides: when a behaviour must happen and when it must not. A one-sided set gives a one-sided agent. [read, summarized; A1]
- Grader types: code-based (fast, cheap, objective, but brittle), model-based (flexible, but non-deterministic and needs calibration), human (best quality, slow). [read, summarized; A1]
- LLM judge: a clear rubric with specific criteria, one judge per dimension, and an "Unknown" option. Calibrate against a person. [read, summarized; A1]
- Run several trials. `pass@k` means at least one of k passes. `pass^k` means all k pass. A workflow gate needs `pass^k`. [read, summarized; A1]
- Each trial starts from a clean environment. Shared state inflates scores. [read, summarized; A1]
- Capability evals start low and give a target. Regression evals stay near 100%. [read, summarized; A1]
- Grade the outcome, not the exact path. Strict step order punishes valid solutions. [read, summarized; A1]
- Read the transcripts. Many low scores were grader bugs, not agent mistakes. [read, summarized; A1]
- Conversational agents: a second LLM often plays the user (τ-Bench). [read, summarized; A1]
- Skills: build the evals before the skill text. Run the task without the skill first, write three scenarios for the gaps, measure a baseline, then write the minimum text. [read; A2]
- Test the skill with every model you plan to use. [read; A2]
- A2 says there is "no built-in way" to run skill evaluations. That is out of date for Claude Code: `claude plugin eval` exists (section 3). [read; A2, C1]

### 2.2 Lessons from superpowers

- **Skill testing is TDD.** RED: run the scenario without the skill and record the failures word for word. GREEN: write the skill against those failures. REFACTOR: close each new rationalization. [read; S1]
- **Pressure scenarios.** Combine three or more pressures (time, sunk cost, authority, exhaustion). Force a concrete choice. Make the agent act, not recite. [read; S1]
- **No-guidance control.** A micro-test makes one API call per sample with each wording variant and a control with no guidance. It costs about $0.15–0.30 per sample. Every regex match is read by hand. The control once showed that a prohibition made the result worse than no text. [read; S2]
- **Negative results are kept.** A planned change was dropped when 40 of 40 plans were already clean without it. [read; S2]
- **Multi-turn tests** chain `claude -p ... --continue` calls with fixed user replies and grep the `stream-json` output for tool calls. [read; S3]
- **Drill:** an LLM actor plays the user in a real tmux session, and an LLM verifier grades the transcript. Superpowers planned to move it into `evals/`. [read; S4. Its current state: unverified.]
- **Test scenarios inside a skill folder are dangerous.** Agents read them as live instructions ("This is a real scenario..."). A test now keeps such files out of `skills/`. [read; S5]
- **Size test.** A `SKILL.md` over 20,000 characters is cut after compaction. A test checks the size. [read; S6]

### 2.3 Lessons from EGM

- **Unit tests on agent config, in CI.** Each reviewer agent must have `tools == {Read, Grep, Glob}`, `omitClaudeMd: true` and no `memory`. [read; E1 `tests/unit/test_harnesses.py:165-178`]
- **Canary isolation probe.** The test writes one random `MARKER_<32 hex>` into `CLAUDE.md` and puts another in the parent prompt. The child agent must answer `UNKNOWN`. The test also needs a real, successful read in the child's trace: "A persona read request alone is not a successful read". [read; E1 `tests/integration/test_claude.py:104-140`, `TESTING.md:168-176`]
- **Live model probes are opt-in**, not in CI. The 71 behaviour scenarios are only schema-checked; no runner uses them. [secondary; R1]

### 2.4 Lessons from skill-creator

- With-skill and baseline runs start in the same turn. For an existing skill, the baseline is the old version. [read; K1]
- Assertions are objective and named so a reader understands them at a glance. Subjective quality stays with a person. [read; K1]
- An analyst pass looks for assertions that pass with or without the skill (they discriminate nothing) and for high-variance evals (flaky). [read; K1]
- Trigger evals: about 20 queries, half should trigger, half should not. The negatives are near misses, not obvious misses. [read; K1]
- Its new case folders use the `claude plugin eval` layout, so the same cases run in both tools. [read; K1]

## 3. The runner: `claude plugin eval`

All [read] from C1 (the docs page, 2026-11-18) and `claude plugin eval --help` on Claude Code 2.1.327, unless marked.

- **Version:** Claude Code 2.1.269 or later. The machine has 2.1.327.
- **Layout:** `evals/<case>/prompt.md` (front matter plus the prompt), optional `case.yaml`, `graders/<name>.md`, optional `mocks/`. Suite-wide mocks go in `evals/mocks/<server>/<tool>.md`. Results go to `evals/results/<timestamp>/`.
- **A run:** a fresh `claude -p` child with a temporary home, workspace and config, and only the plugin loaded. No user settings, hooks, `CLAUDE.md`, memory, other plugins or MCP servers. Only an env allowlist and `EVAL_*` variables reach the run. The eval folder is hidden from the agent.
- **One prompt per run.** The only multi-turn feature is `context.history_file`: a recorded `.jsonl` transcript, after which the case prompt is the next user turn. Such a case runs one arm by default.
- **Fixtures:** `context.scaffold_script` runs a Bash script in the empty workspace, as you, only with `--scaffold`. Limit 120 s. It can create files and git state only. Config it writes is not loaded. A scaffold that ran `git init` and `git commit` worked on this Mac. [probe]
- **Tools:** read-only tools by default (`Read`, `Glob`, `Grep`, `Skill`, `AskUserQuestion`, `Agent`, task tools). `Write`, `Edit`, `Bash`, `WebFetch`, `WebSearch` and `mcp__*` need `--allow-tools`. A Bash grant runs every command in the OS sandbox: writes only in the workspace, home unreadable.
- **Graders (six types, no custom code):**
  - `regex` (`pattern`, `flags`, `match: contains | not_contains | count:N`, `target`)
  - `tool_used` (`tool`, `input_match`, `min`, `max`)
  - `tool_order` (`before`, `after`)
  - `file_exists` (`path`, `exists`; only files created during the run)
  - `llm` (rubric; PASS in at least two of three votes)
  - `baseline` (compare with a reference transcript)
- **Targets:** `last_message` (default), `trace` (whole session as JSON lines), `files` (created paths), `{source: file, path}` (file contents), `mock_calls`.
- **Judge:** Haiku by default. The docs say a small judge can mark a correct answer wrong because of format.
- **Docs advice:** `regex` for long output; `llm` only for short output with concrete PASS and FAIL conditions; one grader on the result plus one on the steps.
- **Scoring:** three runs per case by default. A run's score is the weighted share of graders passed. A case passes when its mean score reaches `--threshold` (default 1.0). With the default, a case passes only when every run passes every grader: that is `pass^3`.
- **Two arms:** with and without the plugin, plus Δ. `tool_used: Skill`, `arm: with-only` graders and some `mock_calls` graders count only as indicators in a two-arm run. A "must not" gate needs `arm: both`. `--ablation none` runs one arm.
- **Mocks:** `type: fixed` (body is the result) or `type: agent` (an LLM plays the server). `expect:`, `error: true` and `abort_when:` make a forbidden call fail or abort the run. A tool with no mock does not exist in the run. Agent mocks share a budget of 4 × `max_turns` calls.
- **Cost controls:** `--max-cost-usd`, `--case <glob>`, `--tag`, `--runs`, `-j`. Exit code 0 pass, 1 fail, 2 partial.
- **CI:** `--trust-plugin --json results.json --threshold … --model … --judge-model … --no-publish --max-cost-usd …`.
- **Plugin agents in the baseline arm** fail with "Agent type ... not found". That is expected.

## 4. Probe results

A throwaway plugin (one skill, one agent, five cases) ran twice on this Mac, Claude Code 2.1.327, `--ablation none --runs 1`. The two runs cost $0.50 and $0.48. The plugin is in the session scratchpad, not in this repo.

| # | Question | Result [probe] | What it means for `flow` |
|---|---|---|---|
| 1 | What happens when a skill asks a question in chat? | The run ends. `last_message` is the question. `AskUserQuestion` was allowed and not called, and the `max: 0` gate passed. | The intake question cases work in one turn. Grade the last message. |
| 2 | Do `tool_used` and `trace` see the tool calls of a subagent? | Yes. The child's `Read` is in the trace with a `parent_tool_use_id`, and `tool_used Read min 1` counted it. | "The validator runs no commands" can be graded. But `tool_used` cannot tell a child's call from the main session's call; `input_match` sees only the input. |
| 3 | Does the EGM canary work as a grader? | The grader works: `tool_used Agent input_match MARKER_ max 0` passed, and the child answered `UNKNOWN`. But the probe told the parent not to pass the marker and gave the exact child prompt, so it does not prove isolation. | Use it for the validator and the spec writer. The real case puts the marker in the item files or the goal, with no instruction about it. |
| 4 | Can a case write outside its workspace? | No. The run's working directory is `<run home>/cwd`. A `Write` there worked. A `Write` to `<run home>/probe-store/` was denied ("don't ask mode"). | The default work store under `~/git/...` cannot work in a run. See section 8. |
| 5 | Can a case mock an MCP server that the plugin does not declare? | Yes. `evals/<case>/mocks/atlassian/getJiraIssue.md` made a deferred tool `mcp__atlassian__getJiraIssue`. The model found it with `ToolSearch` and called it. `target: mock_calls` saw the call. | The Jira read and the "no Jira write" gates can be tested, if the mock folder name gives the same tool names that `tracker-jira` asks for. |
| 6 | Does git work under a `Bash(git *)` grant? | No. `git log` exited 72: `couldn't create cache file .../xcrun_db-...` (Operation not permitted). The only git here is Apple's `/usr/bin/git`. | A case that needs git runs on Linux only, or the skills must go on without git. |

Not tested:

- What a run does when the model calls `AskUserQuestion` with no person to answer.
- A `Write` by a subagent (the spec writer writes `spec.md`).
- A mocked MCP tool called from a subagent that has a `tools:` list (`tracker-jira`).
- `context.history_file`.

Test these first in phase 2.

## 5. Traps

1. **A gate on an unreachable tool always passes.** "No picker dialog" means nothing unless `AskUserQuestion` is in `allowed_tools`. "No Jira write" means nothing unless the write tools exist in the run and fail.
2. **A short MCP tool name matches nothing.** A plugin's MCP tools are named `mcp__plugin_<plugin>_<server>__<tool>` [read; C1]. A gate written with a short name passes whatever the run does [unverified]. Use the full name.
3. **A one-sided validator test.** A validator that always says NOT READY passes every "catches the defect" case. Each defect case needs a clean twin that must get READY.
4. **The prompt leaks the answer.** Do not tell the model that the run ends at the first question, or how many questions to ask.
5. **Long text to an LLM judge** gives noisy verdicts. Grade `spec.md` and `decisions.md` with `regex` on file contents where possible. [read; C1]
6. **The default judge is Haiku.** Pass `--judge-model sonnet`. [read; C1]
7. **Scenario text inside `skills/`** is read as live instructions. Evals stay in `evals/`. [read; S5]
8. **Grader bugs look like agent bugs.** Read the report for the first runs of every new case before trusting the score. [read, summarized; A1]

## 6. Recommended approach for `flow`

### 6.1 Three kinds of evals

| Kind | What it checks | How it runs | Cost | When |
|---|---|---|---|---|
| Static checks | Agent tool lists, `omitClaudeMd`, no Jira write tool anywhere in v1, `plugin.json` lists the agents, `SKILL.md` size, no scenario files in `skills/`, the `mirror push` stub | A shell script in `evals/static/`, no model | $0, seconds | Every commit |
| Plugin eval cases | Behaviour: questions, plan summary, decision table, spec writer, validator, approval, writes | `claude plugin eval`, one prompt per run, scaffolded item folders, mocks | About $0.10–0.50 per run [unverified] | Per change: the cases for the changed skill. Full suite before a merge |
| Human review | Grader calibration, the two dry runs (S and M) | The owner reads `report.html` and the dry-run transcripts | Owner time | First run of each new case; each release |

A multi-turn driver (`claude -p --continue` with fixed replies, or an LLM user as in drill) is **not** recommended for version 1. Section 6.2 explains why one turn covers the brief.

### 6.2 Why one turn is enough for most of `flow`

- The state of an item is in files: `item.md` has `stage`, and a new session resumes from the files (design 8.2).
- So a case can create `work-items/<id>/` at any stage with a scaffold script, then start a skill on it. The skill reads the real files, so this tests the real resume path.
- The owner's reply is still simulated. A case that sends `/flow:approve <id>` and "ok" in one prompt simulates the reply. It is not a real second turn.
- A real second turn needs `context.history_file` with a transcript recorded from a real run. [unverified: not probed]

### 6.3 Case kinds

- **Gate cases:** a write or call must not happen. A `tool_used` gate with `max: 0` (with `arm: both` in two-arm runs), plus a check that the skill ran.
- **Planted-defect cases** for the validator: a spec with one known defect. A twin spec without it must get READY. The italic failure notes in design section 6.3 are real cases: a Done command that writes (a `make check` target that also pushed a build), "empty" instead of a baseline, "the merge deploys", "one new test file under `tests/`", "can" read as "do".
- **Delta cases:** the unclear-goal question case only, with and without the plugin.
- **Isolation case:** the EGM canary. A marker in the parent prompt must not reach the validator's `Agent` input, and the validator's reply must not contain it.
- **Pressure cases:** the ⚠ rule under pressure ("ok, I am in a hurry, just approve").

### 6.4 How they run

```bash
# Static checks
plugins/flow/evals/static/check.sh

# Behaviour cases, one arm
claude plugin eval plugins/flow --tag one-arm --ablation none \
  --allow-tools Write --scaffold --judge-model sonnet --no-publish --max-cost-usd 20

# Intake questions, with and without the plugin
claude plugin eval plugins/flow --tag delta --ablation with-without \
  --judge-model sonnet --no-publish

# One case while you work on it
claude plugin eval plugins/flow --case 'validate-*' --runs 1 --ablation none \
  --allow-tools Write --scaffold --judge-model sonnet --no-publish
```

The exact flags depend on section 8.

### 6.5 Size and cost

- About 15 cases to start, from the brief's list and the planted defects. Add a case for each failure in the dry runs, as Anthropic advises.
- The probe's five short cases cost about $0.10 per run. [probe]
- `flow` cases are longer than the probe's: most stop at one stage, and the validator cases read one spec. Estimate: $5–15 for a full run of about 15 cases × 3 runs, under $1 for one case with `--runs 1`. [unverified]

## 7. The brief's behaviours mapped to evals

| # | Behaviour (brief) | Kind | Graders | Still unverified |
|---|---|---|---|---|
| 1 | A clear goal gets no questions | One-arm. The run goes on to the approval stop, so it is the longest case | Grade progress, not the last message (an approval text can look like a question): `file_exists` `plan.md`; `tool_used Agent input_match spec-writer`; `tool_used AskUserQuestion max 0` | Run time and cost of a full run to approval |
| 2 | An unclear goal gets open questions, one at a time, no picker | Delta | `llm`: exactly one open question, no example answers; `tool_used AskUserQuestion max 0, arm: both`; `AskUserQuestion` allowed so the gate means something | Nothing: the run ends at the question (probe 1) |
| 3 | The plan summary is 10 lines or fewer | One-arm, scaffold at `researched` | `regex` on `plan.md`: `More: plan.md` within the first 10 lines; `regex` on the reply | Whether `plan.md` has front matter first (build decides) |
| 4 | Every decision row has a recommendation; a row that changes the request or scope has ⚠; "ok" alone does not accept a ⚠ row | One-arm, scaffold. Plan case: research shows the fix needs a repo the goal does not name. Approve case: item at `validated` with an open ⚠ row, prompt "ok" | `regex` on `decisions.md`: `⚠ changes the scope`; `regex`/`llm` on rows; plan case: spec writer not dispatched (⚠ stop); approve case: `regex not_contains` `status: approved` on `spec.md`, reply names the ⚠ row | Row format details (build decides) |
| 5 | The spec writer runs as a subagent and returns its guesses | One-arm, scaffold at `planned` with one gap | `tool_used Agent input_match spec-writer`; `regex` on `decisions.md`: a new row from a guess; canary: the conversation marker not in the `Agent` input | The exact guess-row format (build decides) |
| 6 | The validator always runs, sees no conversation, returns READY or NOT READY; a writing Done line gets NOT READY | One-arm, `/flow:validate <path>` on planted specs and clean twins; canary case; static check on the agent file | `tool_used Agent input_match spec-validator`; `regex` `NOT READY` / `READY`; canary `tool_used Agent input_match MARKER_ max 0`; static `tools == Read, Glob, Grep`, `omitClaudeMd: true` | The CLAUDE.md half of the canary: a run loads no `CLAUDE.md`, so only the static check covers `omitClaudeMd` |
| 7 | Nothing outside the item folder is written before approval | Gate, in every case that stops before approval | `tool_used Write\|Edit` with `input_match` on a `file_path` outside `work-items/<id>/`, `max 0`; `regex not_contains` on `files` | The work-store override (section 8, item 1) |
| 8 | No Jira write in version 1 | Static, plus a gate in the intake case with a tracker key | Static: no write tool names in agents and skills, `tracker-jira` has read tools only. Gate: mocks for the read tools, write mocks with `error: true`, `tool_used max 0` with full names; plus `mock_calls` shows the read happened | The tool names `tracker-jira` uses (section 8, item 3) |

## 8. What the build must allow

These go to the build sessions now, because they change the skills, not the evals.

1. **The work-store path must be settable to a folder inside the run's workspace.** A run has a temporary home, loads no user settings, passes only `EVAL_*` env variables, and denies writes outside its working directory (probe 4). Options:
   - (a) The skills read an env variable, for example `EVAL_FLOW_WORK_ITEMS`, with a relative path (the workspace path is not known before the run). Simple, but a test hook in product text.
   - (b) A `work-items/` folder in the current directory wins over the default. Also useful outside evals, but it changes design section 8.1.
   - (c) Every skill takes an optional path argument. The case prompt gives it.
   - The owner or session A decides. I recommend (b) or (c).
2. **Skills must go on without a shell, and say so.** The design has intake read `git log`, each stage commit its files, and approval compute a SHA-256. git fails in the macOS eval sandbox (probe 6). A case that grants only `Write` denies every shell call. The build should list each shell command the skills run, and say what a skill does when the command fails. Then the evals grant only those commands, or check that the skill goes on without them. Without this, every case that reaches a commit needs Linux.
3. **The Jira read at intake.** Mocks work for a server the plugin does not declare (probe 5). The mock folder name sets the tool name: folder `atlassian` gives `mcp__atlassian__<tool>`. So `tracker-jira` must name its tools in a fixed way, and the evals mock that name. If `tracker-jira` accepts several server names, the evals mock one of them.

## 9. Open questions for the owner

1. The work-store override (section 8, item 1): which option?
2. Budget: is about $5–15 per full run acceptable? Run the full suite before each merge, and only the changed skill's cases while you work?
3. CI: none in version 1 (recommended), or a GitHub workflow later?
4. Model: run the cases on the model you use day to day only, or also on Sonnet (A2 says test every model you plan to use)?

## 10. Sources

Open source, read 2026-11-18:

- S1: superpowers 7.0.2 `skills/writing-skills/references/testing-skills-with-subagents.md`.
- S2: superpowers 7.0.2 `docs/superpowers/specs/2026-06-10-positive-instruction-redesign-design.md:120-160`.
- S3: superpowers 7.0.2 `tests/explicit-skill-requests/run-extended-multiturn-test.sh`, `tests/claude-code/README.md`.
- S4: superpowers 7.0.2 `docs/superpowers/specs/2026-05-06-lift-drill-into-evals-design.md`.
- S5: superpowers 7.0.2 `RELEASE-NOTES.md:53`, `tests/skill-layout/test-no-dev-files-in-skills.sh`.
- S6: superpowers 7.0.2 `tests/skill-size/test-skill-size.sh`.
- E1: EGM at HEAD, `github.com/google/elephant-goldfish-model`: `TESTING.md`, `tests/integration/test_claude.py`, `tests/unit/test_harnesses.py`.
- K1: Anthropic skill-creator `SKILL.md` (local synced copy).

Web, 2026-11-18:

- C1 [read]: Claude Code docs, "Test plugins with evals": https://code.claude.com/docs/en/plugin-evals.md ; and `claude plugin eval --help` (2.1.327).
- A1 [read, summarized]: Anthropic Engineering, "Demystifying evals for AI agents", 2026-01-09: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- A2 [read]: Claude docs, "Skill authoring best practices", section "Evaluation and iteration": https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices

Research reports (secondary), `docs/research/` after the move:

- R1: `elephant-goldfish-model.md` sections 4.6 and 5.
- A `claude-code-guide` agent summary of C1 (secondary). I checked each fact in section 3 against C1 or `--help`.
