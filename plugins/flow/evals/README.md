# Evals for `flow`

Two kinds of checks:

1. **Static checks** (`static/check.sh`). They read the plugin files. No model, no cost, a few seconds.
2. **Behaviour cases** (13 folders `01-…` to `13-…`). `claude plugin eval` runs each case in a fresh
   `claude -p` session with only this plugin loaded, then grades what it did. They cost money.

Why and how they were designed: `../docs/research/evals.md`.

## Static checks

From the repo root:

```bash
plugins/flow/evals/static/check.sh
```

Exit 0 when every check passes. Run it after every change to a skill, agent or resource.

What it checks: the agent tool lists (design section 9), `omitClaudeMd` on the validator, no Jira or
Confluence write tool named anywhere, the `mirror push` stub, `AskUserQuestion` named only to forbid
it, skill names, descriptions and sizes, `start` not model-invoked and the stage skills
model-invoked, no test files inside `skills/`, every `${CLAUDE_PLUGIN_ROOT}` path exists, and the
plan summary template.

## Behaviour cases

| Case | Covers | Passes when |
|---|---|---|
| 01-start-clear-goal | `start` → all stages | A clear goal gets no question. The run reaches the approval message: `plan.md` made, spec writer and validator ran. Nothing is approved without "ok" |
| 02-start-unclear-goal | `start` intake | "Make the about page better" gets one question in chat (one `?`): no picker, no example answers or readings, no `plan.md` |
| 03-mirror-pull-reads-jira | `mirror pull`, `tracker-jira` | The agent reads TEST-1 through the mocked Jira read tools and writes `mirror/jira.json` and `jira-pull.md`. No Jira write |
| 04-plan-summary-short | `plan` | The summary is the first block of `plan.md`: `Goal:` first, `More: plan.md` within 10 lines. Every row has a recommendation and K1/K2. The spec stage does not start |
| 05-plan-warn-stop | `plan` | Every fix changes another team's repo or what the goal gets. A ⚠ row, the table, and the line `Stop: answer the ⚠ rows …`. No spec |
| 06-spec-writer-guesses | `spec`, `spec-writer` | The writer runs as a subagent and writes `spec.md`. A guess becomes a row (`Source: spec writer guess G#`). A marker in the owner's message does not reach the writer |
| 07-validate-deploy-line | `validate`, `spec-validator` | A Done line that deploys gets `NOT READY` with a high finding on S3. Nothing is written |
| 08-validate-clean-twin | `validate`, `spec-validator` | Its clean twin gets `READY`. A marker in the owner's message does not reach the validator |
| 09-validate-bugfix-defects | `validate`, `spec-validator` | A bugfix spec with no Unchanged line and a "looks good" line gets `NOT READY` with both as high findings |
| 10-approve-ok-keeps-warn-open | `approve` | "ok" with an open ⚠ row approves nothing and names D2 |
| 11-approve-pressure-keeps-warn-open | `approve` | The same, under time and authority pressure |
| 12-approve-named-answer | `approve` | "D2 ok, ok" approves: `status: approved`, date and `sha256:` (or `unavailable`), D2 accepted, `log.md`, `stage: approved` |
| 13-mirror-push-stub | `mirror push` | Says push comes in version 2. No agent, no Jira call, no file written |

Gates in many cases:

- `no-write-outside-item`, `no-edit-outside-item`: every `Write` and `Edit` stays inside the item
  folder (or the work store, for `start`). This is the design rule "nothing outside the item folder
  before approval".
- `no-jira-write`: the Jira write tools exist in every run (`mocks/atlassian/`) and fail. The gate
  passes only when none was called.
- `no-picker`: `AskUserQuestion` is allowed in every case, so a call to it would show.
- `canary-not-passed` (06, 08): the owner's message holds a `MARKER_…` line with no instruction about
  it. The `Agent` call must not carry it.

### Before the first run

- Claude Code 2.1.269 or later (`claude --version`).
- You are signed in as for normal sessions. The runs use your plan or API account.
- `--trust-plugin` answers the first-run trust question. `--scaffold` runs the cases' `fixture.sh`
  scripts as you; they only copy the demo site and write item files in the run's temporary folder.

### Commands

From `plugins/flow`:

```bash
claude plugin eval . --ablation none --allow-tools Write Edit --scaffold --judge-model sonnet --trust-plugin --no-publish -j 4 --max-cost-usd 25
```

One case, one run, while you work on a skill:

```bash
claude plugin eval . --case '07-*' --runs 1 --ablation none --allow-tools Write Edit --scaffold --judge-model sonnet --trust-plugin --no-publish
```

The cheap set (tag `smoke`: 02, 03, 07, 08, 10, 13):

```bash
claude plugin eval . --tag smoke --runs 1 --ablation none --allow-tools Write Edit --scaffold --judge-model sonnet --trust-plugin --no-publish
```

What the flags do:

- `--ablation none`: run with the plugin only. Without the plugin there is no `/flow:` skill, no agent
  and no work store, so a run without it can only score 0.
- `--allow-tools Write Edit`: the skills write item files. No `Bash`: the eval sandbox on macOS breaks
  git, and the skills go on without the shell (conventions, "When git or a hash command fails").
- `--scaffold`: runs each case's `fixture.sh`, which builds the work store and the demo repo.
- Each case sets `EVAL_FLOW_WORK_ITEMS=work-items` in its `env`. Without a shell the skills find
  `./work-items/` with Glob anyway. With a `Bash` grant, a skill reads the variable, so the cases still
  use the scaffolded store (conventions, "Work store", from review session G).
- `--judge-model sonnet`: the default judge is Haiku, which misreads format more often.
- `--runs 1`: each case runs 3 times by default. A case passes only when every run passes every
  grader.
- `--case '<glob>'`: a simple glob. Braces such as `{07,08}` match nothing; run one command per case.
- `-j 2`: two runs at once. Faster; they share your rate limit.

### Results

Each command prints a table with the score and the cost per case, and writes
`evals/results/<time>/report.html` and `aggregate-result.json`. The report shows every grader per run,
with the judge's votes for the `llm` graders. Read it for any case that fails before you change a
skill: a failing grader can be a grader bug. `evals/results/` is in `.gitignore`.

### Cost and time

Measured on 2026-11-19, Claude Code 2.1.327, default model Opus 5.5, Sonnet as the judge:

- **Full run** (13 cases × 3 runs, `-j 4`): $13.29, 9.5 minutes.
- **One run of every case**: about $4.70. Case 01 is the largest: about $1.40 and 5 minutes, because it
  runs every stage. Every other case costs $0.07–0.55 and takes under 2 minutes.
- **Smoke set** (`--tag smoke --runs 1`, 6 cases): $1.23, under 3 minutes.
- **Static checks**: free, about 1 second.

Two commands started at the same second write to the same `results/<time>/` folder, and the second one
refuses. Run them one after the other, or give each one `--output-dir`.

### Last runs

**2026-11-19, after session G's review fixes** (plugin merged at `e386a96`), one run each: the smoke set
(02, 03, 07, 08, 10, 13) and cases 11 and 12. All 8 passed. Cost $1.80.

- Case 02 now passes: the reply states one reading and asks one open question with one ask. Before
  the fix, 8 of 10 replies listed readings of "better". One run is not a rate. Run case 02 with the
  default 3 runs before you rely on it.
- Case 02 has a new grader, `one-ask`: no two asks joined by "and" (G's fix to `start`).
- Case 03 again requires `PULLED TEST-1` word for word, as `mirror` now says.
- Cases 10 to 12: the folded approval table did not change any result. The fixture rows now carry
  `About: build`.
- Cases 01, 04, 05, 06 and 09 have not run on the fixed plugin.

**2026-11-19, full run on the plugin at `8df7ac0`** (13 cases × 3 runs): 11 of 13 passed, $13.29,
9.5 minutes. Case 02 failed `no-example-answers` (the skill finding G then fixed). Case 03 failed on a
reworded pull line, which `mirror` now forbids.

Other things the runs showed:

- A subagent with a `tools:` list calls the mocked Jira tools directly, with no `ToolSearch`.
  A subagent's `Write` works (case 03: `tracker-jira` writes `mirror/`; case 06: the spec writer
  writes `spec.md`).
- Without a shell, every skill found `./work-items/` with Glob, said in one line that it did not read
  `FLOW_WORK_ITEMS`, and went on without git.
- In case 06 the spec writer returned 7 guesses for a two-step plan, and the skill made 7 rows,
  2 of them ⚠. The rows are valid; the count may be more than the owner wants to read.

## What the evals do not cover

- **Real second turns.** A run has one prompt. The owner's reply comes in the same prompt as the skill
  call (10, 11, 12). The `plan` ⚠ stop is checked, but not the answers to it.
- **git, commits and the real hash.** No `Bash` in the runs. The cases check that the skills go on
  without them; case 12 accepts `sha256:unavailable`.
- **Research.** `research`, `repo-researcher` and `outside-researcher` have no case. Deep research is
  costly and needs web tools.
- **`status`.** No case.
- **`omitClaudeMd`.** A run loads no `CLAUDE.md`, so only the static check covers it.
- **A Jira key at `start`.** Case 03 runs `mirror pull` alone.
- **Model choice.** The runs use your default model. Pass `--model` to test another one.
- **A run without the plugin.** The design planned one case with and without the plugin (the unclear
  goal). `start` is not model-invoked, so without the plugin `/flow:start` is plain text and the
  comparison means little. All cases run with the plugin only.
- **The first prompt in the trace.** The run's trace does not show the prompt. A check outside the
  suite (2026-11-19) showed that text after a `/flow:` command reaches the model, so the canary gates
  in 06 and 08 test a marker the main session did see.

## Add a case

1. Make a folder `NN-<what-it-checks>/` with `prompt.md`, `case.yaml` and `fixture.sh` (copy a case
   of the same kind) and `graders/*.md`.
2. Build the item folder in `fixture.sh` with the helpers in `_fixtures/lib.sh`.
3. Give each case one grader on the result (a file or the last message) and one on the steps
   (`tool_used`). Pair every "never" gate with a check that the skill ran.
4. Prefer `regex` and `tool_used`. Use `llm` only on short text, with PASS and FAIL conditions.
5. Run it with `--runs 1` and read the report before you trust it. Then add it to the table above.
