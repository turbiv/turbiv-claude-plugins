# Pre-implementation stages: design

- **Status:** agreed with the owner on 2026-11-18 ("the decisions are good"). Ready for implementation. See [section 10](#10-decision-log).
- **Date:** 2026-11-18.
- **Scope:** the stages from a goal to an approved spec. The implementation stages come later.
- **Base:** a fork of the superpowers `brainstorming` skill (v7.0.2, MIT), tailored. The parts come from four other workflows. See [section 2](#2-base-and-what-changes).
- **Inputs:** the research in [`../research/`](../research/planning-comparison.md) and web research from 2026-11-18 (sources in [section 13](#13-sources)).

## 1. Summary

1. The owner gives a goal: a few words or a long explanation. The workflow sizes the task as S, M or L from what the goal asks for, not from its length.
2. When the goal is unclear, Claude asks open questions, one at a time, in normal chat. The owner can discuss them. There are no picker dialogs. A clear goal gets no questions.
3. The owner can choose the research depth: none, quick or deep. Each size has a default.
4. The plan is free-form. The owner sees a summary of 10 lines or fewer. The full plan stays in a file.
5. A fresh subagent writes the spec. The spec is binding. It names areas, not function names or file paths. Its core is the **Done when** list: pass or fail lines, each with a command that only reads.
6. A validator subagent always checks the spec: is it correct, and can an implementation agent use it without guessing?
7. All design decisions go into **one decision table**, which the owner can discuss in free text. Every row has a recommendation. A row that changes the request or the scope has a **⚠ warning** and needs a named answer.
8. There is one stop for approval. There is an earlier stop only when the plan has a ⚠ row.
9. Local files in this repo are the source of truth. Jira is a mirror behind a tracker connector.
10. The superpowers plugin is not used in these sessions. This workflow's own skill replaces it.

## 2. Base and what changes

### 2.1 Why superpowers brainstorming

Five workflows were scored against the owner's 12 requirements ([planning-comparison.md](../research/planning-comparison.md)). Superpowers ranked first (4 fit, 7 partly, 1 no). The ranking is approximate: different agents scored the five workflows, and the margin over cc-sdd (2 / 9 / 1) is small. The owner's clarification on questions (Q8) moved superpowers closer still.

The criticism of superpowers is about the always-on bootstrap, token cost, ceremony on small tasks and the implementation skills: writing-plans, TDD and subagent-driven execution. Reviewers rate brainstorming and the plan sketch as its best parts. This design takes only those parts, as a fork. It does not depend on the plugin. [secondary; see section 13.]

### 2.2 Keep, change, drop, add

| Superpowers brainstorming | Here | Source of the change |
|---|---|---|
| Private check: "everything that matters is in the request" → do it, no questions (`SKILL.md:17-24`) | **Keep** | — |
| Look before you ask; never ask what the project already answers (`:42-50`) | **Keep** | — |
| Ask only when the answer changes what gets built; one at a time; open questions with no example answers until the why is known (`:101-116`) | **Keep**, for the goal and the why | Owner, 2026-11-18 |
| Play-back of about 200 words, then chunks of 200–300 words (`:56-57`, `:190-200`) | **Change**: 3 lines or fewer | Owner prefers short text |
| Opt-out: "if you'd rather I just dive in, say so" ends the skill (`:90-95`) | **Keep** ("skip", "no questions") | — |
| Process steps are the agent's calls: do them and say so; a default the owner never heard is one they couldn't reject (`:104-105`, `:290`) | **Keep**: the rows "made by me" | — |
| Two sizes, small change or project, which the owner can override; step up a size if it grows (`:209-224`) | **Change**: S, M, L with defaults | Owner (Q11) |
| Several independent projects: agree an order, one at a time (`:226-227`) | **Keep**: one item per run | — |
| Lay out 2–3 approaches with trade-offs, recommend one, in a message of its own (`:156-167`) | **Change**: they become rows in one decision table | Owner (Q8) |
| One design doc, written by the main session | **Change**: a free-form `plan.md`, then a binding `spec.md` written by a subagent | Owner (Q5, Q6); superpowers' own "the spec is binding, the plan is its argument" |
| Builder check, for projects only; a small change skips it (`:241-267`) | **Change**: it becomes the validator, always on, with more checks | Owner (Q7); EGM comprehension reader; Spec Kit `/analyze` |
| Hard gate: nothing is built before approval (`:269-283`) | **Keep**. A hook can enforce it later (open question 2) | — |
| Visual companion (browser server) | **Drop** | Not needed; it sends a version ping by default |
| Automatic hand-off to writing-plans (`:32`, `:281-282`) | **Drop**. The implementation stages are designed later | Owner |
| `using-superpowers` bootstrap ("1% → MUST") | **Drop**. The plugin is not used in these sessions | Owner, 2026-11-18 |
| — | **Add**: a research step with depth none, quick, deep | HumanLayer research blinded to the goal |
| — | **Add**: a Done-when format | The owner's rules from the first build; Anthropic red-first; Kiro Unchanged behaviour |
| — | **Add**: local item folders and a tracker connector | Owner (Q10) |

## 3. Flow

```
goal ─► 0 Intake ─► 1 Research ─► 2 Plan ─► 3 Spec ─► 4 Validate ─► 5 Approve ─► build (later)
         questions?                ⚠ stop?                             stop
```

- **Questions at intake** only when the goal is unclear, or when deep research is recommended.
- **⚠ stop after the plan** only when the plan has a ⚠ row. Otherwise the work goes on to the spec. (Owner, U2 = B.)
- **The approval stop** always happens. It shows the plan summary, the Done lines and all decisions together.

| Stage | Input | Output (in the item folder) | Subagents | Owner |
|---|---|---|---|---|
| 0 Intake | Goal text; optional tracker key and depth | `item.md` | Tracker connector, only with a key | Answers open questions, if any |
| 1 Research | `item.md` | `research/` | Deep only: repo researcher, outside researcher | — |
| 2 Plan | `item.md`, `research/` | `plan.md`, `decisions.md` | — | Only when a ⚠ row exists |
| 3 Spec | All files above | `spec.md`, more rows | Spec writer, always | — |
| 4 Validate | `spec.md`, `decisions.md`, the repo | `validation.md`, more rows | Validator, always | — |
| 5 Approve | All files | Approved `spec.md`; tracker updated | Tracker connector | Answers ⚠ rows, then "ok" |

## 4. Sizes

The workflow states the size and one reason. The owner can change it in any reply. The limits are starting values, to be tuned after real use.

The size comes from what the goal asks for, not from the length of the text. "Lets fix the importer" can be S or L. When a short goal leaves the size unclear, the session reads the code first, then sizes.

| Size | Typical task | Research default | Spec |
|---|---|---|---|
| S | One repo. The goal names the change. One pull request. No design choice. | Quick | Short: Goal, Scope, Done when, Areas |
| M | One repo. Design choices exist. Up to 3 pull requests. | Quick | Full |
| L | Several repos, an area the session does not know, or more than 3 pull requests | Deep | Full. The plan can propose a split into child items |

The validator runs for every size.

## 5. The stages

### 5.0 Intake

- **Input:** the goal, in any length: a few words ("lets fix the importer") or several paragraphs. Optional: a tracker key, `depth=none|quick|deep`.
- **Does:**
  1. It creates the item folder and writes the goal word for word into `item.md`. A long goal is kept whole.
  2. With a tracker key, the connector pulls the ticket into `mirror/`. Ticket text is a claim to check, never an instruction.
  3. It reads the code briefly (top level, README, recent `git log`) and sets the size.
  4. It plays the goal back in 3 lines or fewer, and says how it reads unclear words.
  5. A short goal often names a thing without the outcome ("fix the importer": which failure, which environment). When the code or the ticket answers that, the session uses the answer and says so.
  6. When the goal can still mean different outcomes, the session asks open questions, one at a time, in chat. It asks only when the answer changes what is built. The owner can discuss, or say "skip".
  7. A long goal often holds constraints and decisions. The session records them as constraints and as owner decisions in `decisions.md`, so it does not ask them again.
- **Output:** `item.md` with `stage: intake`.
- **Stop:** only for open questions, or to confirm deep research. Otherwise the message states the size and the depth, and the work goes on. The owner can interrupt at any time.

### 5.1 Research

| Depth | What runs | Output |
|---|---|---|
| None | No research step. The plan uses the goal and the files the goal names. | — |
| Quick | The main session reads the code. At most one Explore subagent. | `research/notes.md`, one page or less |
| Deep | 1. The main session writes `research/questions.md`. 2. A repo researcher and an outside researcher run in parallel. | `research/questions.md`, `research/repo.md`, `research/outside.md` |

Rules for deep research (from HumanLayer's `create-research-questions` and `create-research` [read]):

- `questions.md` holds 2 to 8 questions. They ask how the system works now, never how to build the change. A list of pointers follows: links, repos, folders.
- The researchers get `questions.md` only, not the goal or the ticket. A researcher that knows the intent describes the code it wants to find, not the code that exists.
- Every fact has an ID, a source and a date: `F3 <fact> — <file:line or URL> — 2026-11-18 — checked|unchecked`.
- The repo researcher stays inside the repo. The outside researcher stays outside it.

### 5.2 Plan and plan summary

- **Input:** `item.md`, `research/`.
- **Does:** the main session writes `plan.md` in any form and at any length. It writes every design decision as a row in `decisions.md` (section 7).
- **Output:** `plan.md`, `decisions.md`, `stage: planned`.
- **What the owner sees:** the first block of `plan.md`, 10 lines or fewer:

```
Goal: <one sentence>
Size: <S|M|L> — <reason>
Approach:
1. <step>
2. <step>
Key facts: <F2>, <F5>
Risk: <one line>
More: plan.md
```

- **More detail:** only when the owner asks, for example "show plan" or "explain D2".
- **⚠ stop:** when `decisions.md` has a ⚠ row, the session shows the summary and the table now, before the spec is written. Otherwise it goes on to the spec.

### 5.3 Spec

- **Input:** `item.md`, `research/`, `plan.md`, `decisions.md`. Not the conversation.
- **Subagent:** the spec writer, a fresh subagent. It runs for every size.
- **Does:**
  1. It writes `spec.md` in the format of section 6.
  2. It returns a list of guesses: each place where the files did not tell it what to write.
  3. The main session adds each guess as a row in `decisions.md`.
- **Why a fresh writer:** the owner asked for subagents. A writer that sees only the files also finds gaps in the files. A gap shows as a guess.
- **Runs no commands.** The spec writer has no Bash. Done commands first run at the build start (decision R2).
- **Output:** `spec.md` (`status: draft`), `stage: specified`.

### 5.4 Validation (always)

- **Purpose:** is the spec correct? Can an implementation agent use it without guessing?
- **Subagent:** the validator. It is fresh, with no conversation and no `CLAUDE.md` (`omitClaudeMd`). Its tools are Read, Glob and Grep. It runs no commands and needs no tracker access, because the files are the source of truth.
- **Gets:** `spec.md`, `decisions.md`, the repo paths. Not `plan.md`, because the spec must stand alone.
- **Does, in this order:**
  1. It restates the goal and the Done list in its own words before it judges. A wrong restatement is a finding. (EGM comprehension reviewer.)
  2. **Handoff check.** It reads the spec as an implementation agent that cannot ask the author. It lists each question that agent must still guess, where a wrong guess matters. Missing function names or file paths are not findings: the implementation agent chooses those. (superpowers builder check; owner: keep the spec loose.)
  3. It checks that each section required for the size is present and filled.
  4. It checks each Done line against the rules in section 6.3. (Spec Kit `/analyze`: coverage and consistency.)
  5. It checks each fact `F#` against the code.
  6. It checks each row of `decisions.md` for a missing ⚠ (section 7.2), and each "In" line of the spec for a trace to the goal or a `D#`.
- **Result line:** `READY` (no high-severity finding), or `NOT READY` with the findings. `READY` does not cover rules 3 and 4 of section 6.3 (baseline and red first): those need the commands to run, and they run at the build start.
- **Output:** `validation.md`. Each finding: `V# — severity — where — problem — evidence — proposed row or fix`.
- **After:** the main session applies small fixes and records each as a row "made by me". Other findings become rows. A finding never starts a separate round of questions.
- **One round.** A second full round runs only when the owner asks.
- **After `NOT READY`:** the main session fixes the high findings. A fresh validator then re-checks only those findings. A finding that is still open becomes a ⚠ row, so the owner sees it at approval. (Proposal; see open question 16.)

### 5.5 Approval

- **Message:** the plan summary, the Done lines, the decision table, and what the tracker push will change.
- **Reply:** "ok" approves when no ⚠ row is open (section 7.4).
- **When an answer changes the spec:**
  - An answer that picks an option from the table changes the spec as that option says. Approval happens in the same step.
  - A free-text answer that changes the spec: the session shows the changed lines and asks for "ok" one more time.
- **On approval:**
  1. `spec.md` gets `status: approved`, the date and the SHA-256 of its body.
  2. The connector pushes to the tracker, if the item has one.
  3. The session writes an end note to `log.md`.
  4. Last, `item.md` gets `stage: approved`. It is written last, so a half-done step never looks done.

## 6. Spec format and definition of done

### 6.1 How other workflows define done

| Source | Pattern | Taken | Reason |
|---|---|---|---|
| Owner's planning guide (a separate workflow; lessons only) | Two lists: the session checks, a person checks. Every line passes or fails with a command that only reads. Baseline first. Four rules from the first build. | Yes, as the base of the Done format | Tested on a real build. Each rule names the failure it prevents. |
| Anthropic long-running harness [read, summarized] | A feature list where every item starts as failing. The agent may only flip `passes`. | Yes: rules 4 and 11 | The builder cannot weaken its own criteria. |
| Anthropic harness, same post | Unit tests and curl missed failures; end-to-end checks found them | Yes: rule 12 | A check on what the user sees proves more. |
| Kiro bugfix spec [read] | Current, Expected and Unchanged behaviour | Yes: rule 7, Behaviour section | Regressions are named next to the fix. |
| cc-sdd EARS rules [read] | When, While, If, Where and plain "shall" lines | Only in Behaviour, only when behaviour changes | A line maps to a test. Full EARS is too much for build and infra goals; one review saw a small bug turned into 16 acceptance criteria [secondary]. |
| HumanLayer `create-plan` [read] | Automated and Manual verification per phase | Same as the two lists | It confirms the split. |
| superpowers | The spec is binding, the plan is its argument; Global Constraints copied word for word | Yes: Constraints section, precedence | Constraints reach the reviewer unchanged. |
| EGM | Zero-Decision rule; exact file list | No | The owner wants a loose spec. The implementation agent chooses functions and files. |
| Spec Kit [read] | Given/When/Then; numbered measurable success criteria | No | Behaviour and Done when cover it. |
| OpenSpec [read] | Delta specs merged into a living spec | Not now | Open question 8. |

### 6.2 The spec template

```markdown
---
item: <item id>
revision: 1
status: draft            # draft | approved
approved: null           # <date> sha256:<hash of the body>
---
# <repo> — <outcome>

## Goal
One sentence. The outcome, not the method.

## Why
One to three sentences.

## Scope
In:
- <part> (goal) | (D3)
Out:
- <part>

## Constraints
Copied word for word from the goal, the owner's replies and the decisions. Binding.

## Behaviour
Only when behaviour changes. Leave it out for build, CI and infra goals.
Feature:  B1 When <event>, <system> shall <response>.
Bugfix:   Current: When <condition>, <system> <wrong result>.
          Expected: When <condition>, <system> shall <right result>.
          Unchanged: When <condition>, <system> shall continue to <result>.

## Done when — the session checks
| ID | Check | Command (reads only) | Passes when | Proves |
|----|-------|----------------------|-------------|--------|
| S1 | ...   | `...`                | ...         | goal / B1 |
| N1 | Unchanged: ... | `...`       | same result as the baseline | Unchanged |

## Done when — a person checks
| ID | Check | How | When |
|----|-------|-----|------|
| P1 | The owner approves the pull request | The GitHub review shows "Approved" by the owner, or the owner writes "ok" on it | before merge |
| P2 | <step after merge> | automatic on merge / the owner runs `<command>` | after merge |

## Areas
The repos, folders or stacks the work may change. Exact paths only when a decision fixes them.
New files follow the repo's layout.

## Facts
F1 <fact> — <file:line or URL> — <date checked>

## Decisions
D1 <decision> — owner | AI — details in decisions.md

## Needs from a person
Approvals, values and runs, each with its exact command.
```

**Loose, not vague.** The spec states the outcome, the constraints and the checks. It does not name functions, classes or file paths, unless a decision fixes them. The implementation agent chooses those. (Owner, 2026-11-18. Superpowers v6.4.2 moved its plans from full code to decisions for the same reason.)

**Precedence after approval:** `spec.md` > `decisions.md` > `plan.md` > `research/` > tracker text. A conflict between them is a finding, not a free choice.

### 6.3 Rules for Done lines

1. Every line passes or fails. "Works well" or "is clean" is not a line.
2. A session line uses a command that only reads. A command that can write (a deploy, a change set, a migration) is not a check. Use its read-only form, or make it a person line. *(Owner's rule from the first build: in a trial, a `make check` target also pushed a build; its read-only form only lists the changes.)* A test run that starts only local, throw-away resources (for example a local Docker container that the run removes) counts as reads only, when it changes nothing in the repo and nothing outside the machine. *(Owner, 2026-11-19, after review G-18.)*
3. A diff or count check states a change against a baseline from the untouched branch. It never says "empty". *(Same rule: an untouched branch already showed 11 differences.)*
4. **Red first.** A line for new behaviour must fail at the baseline. If it passes before any work, it proves nothing; rewrite it. An Unchanged line (`N#`) must pass at the baseline; if it fails, record it as "already broken", not as work. *(Anthropic: every feature starts failing. TDD: a new test fails first.)*
5. **Trace.** Every goal part and every Behaviour line has at least one Done line. Every Done line names what it proves.
6. If no Done line can be written for a goal part, the spec is underspecified. That part becomes a ⚠ row.
7. A bugfix spec has at least one Unchanged line. *(Kiro.)*
8. A step after the merge is a person line. It says "automatic on merge" or gives the command the person runs. *(Owner's rule: "the merge deploys" was read as a manual deploy.)*
9. Areas name repos, folders or stacks. New files follow the repo's layout. *(Owner's rule: "one new test file under `tests/`" was followed to the letter, against the repo's layout.)*
10. Goal and Scope state the outcome and the decided constraints. A method appears only as a decision `D#`. *(Owner's rule: a session reads "can" as "do".)*
11. After approval, a later stage changes only the status of a line, never its text. Exception: when the baseline at the build start breaks rule 4 (a new-behaviour line already passes), the build stops. A revised line goes to the owner as a row, and the spec gets a new revision. Status values: PASS, FAIL, PENDING, AFTER-MERGE. A line that was not checked never gets PASS. The status lives outside `spec.md`. *(Anthropic `passes`.)*
12. Prefer the check the user sees: the CI run, the deployed endpoint. A unit test alone is not enough when an end-to-end check exists. *(Anthropic harness.)*
13. A session line uses one short command on one line, or a script that already exists in the repo. No script is written into the spec. When no short command exists, the part becomes a person line that says why. An S spec aims for about one page. *(Owner, 2026-11-19, after review G-4: an S trial spec held a 60-line parser as a Done check.)*

## 7. The decision table

### 7.1 Format

One table per stop, in the chat. It is a markdown table, not a picker dialog. The owner answers in free text and can discuss any row. Evidence stays in `decisions.md`, not in the message.

```
Decisions: 1 to check, 2 recommended, 3 made by me.
Answer the ⚠ rows by name, then reply "ok". Ask "explain D2" for more on any row.

⚠ Check these. They change your request or the scope.
| #  | Decision | Recommended | ⚠ What it changes | Other options |
| D1 | <question> | <choice> — <why> | <what changes against your goal> | B: <option>. You get <x>. Fails when <y>. |

Recommended. "ok" accepts these.
| #  | Decision | Recommended | Why | Other option |
| D2 | <question> | <choice> | <one line> | <option>: <effect> |

Made by me. Give the number to change one.
| #  | Decision | Why | Cost if wrong |
| D4 | <what I decided> | <one line> | <one line> |
```

- Every row has a recommendation. (Owner, 2026-11-18.)
- A ⚠ row says in one line what it changes against the goal, so that the owner thinks twice before accepting. Each option says what the owner gets and when it fails. (EGM: options with failure conditions.)
- Recommended rows say why, and what the other option does.
- Rows "made by me" use the superpowers ruling form: what, why, cost if wrong.
- A row that accepts a limitation says how broadly it bites, not only that it exists.
- Each row explains enough for the owner to choose. "I don't know what to pick" is a sign that the row is too thin. (Owner, 2026-11-18, on picker dialogs.)
- **Folding** (owner, 2026-11-19, after review G-3). The chat shows every ⚠ row and every open row about what gets built, in full. It folds two kinds of open rows into one line: rows about only how a Done line checks (`About: check`) and small validator fixes ("made by me", `Source: validator V#`). The line: `Also <n> check details and <m> small validator fixes. "ok" accepts them. Say "show" to list them.` A ⚠ row is never folded. `decisions.md` keeps every row in full. Reason: in the trials, 13 of 14 (S) and 17 of 18 (M) approval rows were not ⚠, and most were about check mechanics.

### 7.2 When a row gets ⚠

The session asks two questions for every row and writes the answers in `decisions.md`:

| # | Question |
|---|---|
| K1 | Does an option change the request, so that the owner gets a different outcome than the goal says? This includes doing only part of the goal, and going against a decision the owner already gave. |
| K2 | Does an option go outside the scope: work, repos, systems, people or dependencies that the goal does not name? |

- "Yes" to either: the row gets ⚠ and the line "⚠ changes the request" or "⚠ changes the scope".
- Not sure: the row gets "⚠ may change the scope", with the reason. A recommendation is still given. (Owner, U1, 2026-11-18.)

### 7.3 Guards against a missing ⚠

1. Every row in `decisions.md` has its K1 and K2 answers. A row without them is invalid.
2. Every "In" line and every Areas entry in the spec traces to the goal or to a `D#`. A line with no trace is a hidden decision. The validator flags it.
3. The validator checks the rows again. A row it finds should have ⚠ gets one.
4. During the build (later stages), a decision that would get ⚠ by this test stops the session.

### 7.4 Reply rules

- "ok" accepts the recommended rows and the rows "made by me". It does not accept a ⚠ row.
- "ok" with open ⚠ rows: the session names them in one line and waits.
- A ⚠ row is answered by name: "D1 ok" accepts the recommendation; "D1 B" picks option B.
- "D4: <text>" changes a row "made by me".
- "Explain D2", or any question about a row, starts a short discussion. The table stays open.
- "You choose" on a ⚠ row takes the recommendation and records "delegated by owner".
- An answer that creates a new ⚠ row adds it to the next table.

### 7.5 Example (illustration only; no facts about the real repo)

```
Goal: make the backend builds. I read this as "make the failing CI builds pass".
Size: M (assumption: one repo; the cause is not known yet). Research: quick.

⚠ Check these.
| D1 | Fix the cause, or pin the old tool version? | Fix the cause — a pin breaks again at the next upgrade
|    | ⚠ changes the scope: the fix touches the shared build image, which the goal does not name.
|    | Other: B: pin the tool version. Builds pass today. Fails at the next upgrade. |
```

One Done line could read: `S1 — The CI build on the branch passes — gh run list --branch <branch> --workflow <name> --limit 1 --json conclusion — conclusion is "success" — goal`. The baseline shows "failure", so the line is red first.

## 8. Local files and the tracker mirror

### 8.1 Layout

The work store is `~/git/turbiv-claude-plugins/work-items/` (decisions 15–16).

```
turbiv-claude-plugins/
  work-items/
    <id>/                          # <yyyymmdd>-<slug>; never renamed
      item.md                      # front matter: id, title, stage, size, repos, depth, tracker links
                                   # body: the goal, word for word
      research/                    # notes.md | questions.md, repo.md, outside.md
      plan.md                      # free-form; the first block is the summary
      decisions.md                 # all rows, with K1/K2 answers and evidence
      spec.md                      # binding after approval
      validation.md
      log.md                       # end notes: Progress, Surprises, Decisions, Next
      mirror/
        jira.json                  # key, issue type, status map, hash of the last push, times. No pull hash: pull compares
                                   # the ticket text with jira-pull.md and checks Jira's `updated` time (owner, M3, 2026-11-18)
        jira-pull.md               # the last pulled ticket text and new comments
```

- The ID does not depend on a tracker. A tracker key is a link in `item.md`. The folder never changes its name.
- Each stage commits its files.

### 8.2 State and resume

- `stage` in `item.md`: `intake`, `researched`, `planned`, `specified`, `validated`, `approved`. The session writes it last, after the stage's files are complete.
- A new session resumes from `item.md`, then the file of the current stage, then the last end note in `log.md`.

### 8.3 The connector boundary

The stage skills never call tracker tools. They call one connector. One connector exists per tracker: `tracker-jira` now, others later.

| Operation | Direction | Does |
|---|---|---|
| `pull(item)` | tracker → local | Writes the ticket text, status and new comments to `mirror/`. It changes no other file. |
| `render(item)` | local | Makes the tracker text from `spec.md` and `decisions.md`. No tracker call. |
| `push(item)` | local → tracker | Runs `pull` first. Stops if the tracker text changed since the last push. Else it creates or updates the ticket and sets the status. |
| `note(item, text)` | local → tracker | Adds a comment: an end note or a decision summary. |
| `link(item, key)` | local | Writes an existing key into `item.md`. |

- **Issue type and status depend on the item.** (Owner, 2026-11-18.) A linked ticket keeps its own type. For a new ticket, the first `push` asks the owner for the type and the parent, as a row in the approval table. The status map is stored per item in `mirror/jira.json`.
- **Writes:** only the connector writes to a tracker. The owner's `jira-guard` hooks stay as the enforcement.
- **Reads:** a researcher may read a tracker (past tickets, Confluence).
- **A second tracker** needs a new connector with the same five operations. The stage skills do not change.

### 8.4 Jira mirror rules

- **What the team sees:**
  - The description: the rendered spec (Goal, Why, Needs from a person, Areas, Done when as two checklists, Facts, Decisions, Out of scope).
  - A last line: "Written from the owner's local files on <date>. Comment here; the owner takes edits in."
  - A comment at approval: the plan summary and the resolved decision table.
  - End notes as comments.
- **What the team does not see:** `research/`, the full `plan.md`, `validation.md` (open question 7).
- **When it pushes:** at approval, and when an end note is written. Never a draft. The approval message says what the push changes, and the owner's "ok" covers that push.
- **Edits by a person in Jira:** `pull` finds that the text differs from the last push. The push stops. The change becomes a row in the next table: "Take the Jira change into the spec?". Nothing overwrites a person's edit without the owner's answer.
- **Comments by a person:** `pull` collects them. The next message lists them under "New from Jira".

## 9. Subagents

| Agent | Stage | Tools | Model | Gets | Does not get | Output |
|---|---|---|---|---|---|---|
| Repo researcher | 1, deep | Read, Glob, Grep | sonnet | `questions.md`, repo paths | The goal, the ticket, the conversation | `research/repo.md` |
| Outside researcher | 1, deep | WebSearch, WebFetch, tracker read tools | sonnet | `questions.md` | Repo tools, write tools, the goal | `research/outside.md` |
| Spec writer | 3, always | Read, Glob, Grep; Write in the item folder only | sonnet | The item files | The conversation | `spec.md`, a list of guesses |
| Validator | 4, always | Read, Glob, Grep; `omitClaudeMd` | inherit (Opus) | `spec.md`, `decisions.md`, repo paths | The conversation, `plan.md`, tracker tools | `validation.md` |
| Tracker connector | 0 and 5 | The tracker's tools; Read in the item folder; Write in `mirror/` | sonnet | The item files | Repo tools | `mirror/`, the ticket |

**Model routing** (owner, 2026-11-19): a well-scoped task goes to a smaller model; open-ended judgment
stays on Opus. The researchers, the spec writer and the tracker connector do well-scoped work, so they
run on sonnet. The validator judges, so it inherits the main session's model. The stage skills run on the
main session's model. The table is also in `resources/conventions.md`.

Count per size: S and M run 2 or 3 subagents. L runs about 4. The connector adds 1 when a tracker key exists.

## 10. Decision log

All by the owner on 2026-11-18, unless marked "default" (the recommendation, not objected to).

| # | Decision |
|---|---|
| 1 | The goal can be a few words or a long explanation. Size comes from content, not length. |
| 2 | The validator always runs. It checks correctness and whether an implementation agent can use the spec. |
| 3 | The planning guide is a separate workflow. This design borrows lessons from it and does not change it. |
| 4 | U2 = B: one stop at approval; an earlier stop only when the plan has a ⚠ row. |
| 5 | R1: the work store is this repo, in `items/`. The folder name `items/` is a default. |
| 6 | Start from a popular, tested workflow and tailor it. Base: a fork of superpowers brainstorming (default, after the research and the criticism check). |
| 7 | Open questions one at a time in chat are fine. Picker dialogs are not. Decisions go in one table that the owner can discuss. |
| 8 | U1 (confirmed): every row gets a recommendation. A row that changes the request or the scope gets ⚠ and a line on what it changes. "Not sure" also gets ⚠. |
| 9 | Do not use the superpowers plugin in these sessions. This workflow's skill replaces it. |
| 10 | The Jira issue type and the status per stage depend on the item. |
| 11 | The spec is loose: areas, not function names or paths (default, after the owner's remark on Opus). |
| 12 | R2: Done commands first run at the build start (default). |
| 13 | One work item per run. Splitting a large goal into child items is a later design (default). |
| 14 | "ok" does not accept a ⚠ row; ⚠ rows are answered by name (default). |
| 15 | P1: everything in one place, in the marketplace repo `turbiv/turbiv-claude-plugins` (local checkout `~/git/turbiv-claude-plugins`), under this plugin's folder: skills, agents, design, research. This replaces R1. |
| 16 | P1b: work items go in the same repo at the root, `work-items/`, outside the plugin folder, so an install does not copy them. |
| 17 | P2: plugin name `flow` (skills `/flow:start` …), folder `plugins/flow/`. |
| 18 | P4: superpowers stays on while the plugin is built. Turn it off per repo at the first trial run; everywhere once the trials pass and the planning-guide workflow is no longer needed. |
| 19 | P5: version 1 = all stages with local files, plus a Jira read at intake. Jira writes come in version 2. |
| 20 | P6: no new hooks in version 1; `jira-guard` stays. A gate hook after the first trial. |
| 21 | P7 and evals: dry runs on one S and one M goal. A separate session researches how to write good evals for skills and agents, then writes them. |

## 11. Open questions for the implementation stage

1. **Packaging.** One skill per stage, or one skill with a reference file per stage. HumanLayer reportedly keeps each stage under about 40 instructions [secondary, unverified].
2. **Gates in the harness, not in prompt text.** A hook that blocks code edits before approval. A check of the spec hash at the build start. The `jira-guard` hooks for tracker writes.
3. **Turning off superpowers** in these sessions: disable the plugin per project in `.claude/settings.json`, or another method. Check that its SessionStart hook no longer runs.
4. **The status file for Done lines.** JSON (Anthropic: models change JSON less than markdown) or a markdown table. Which agent writes it.
5. **Jira text.** Editing a description replaces all of it, so `push` sends the full text every time. Checklist items must be plain text: bold, backticks or double underscores turn them into ordinary bullets. The render must put commands outside the checklist items.
6. **Spec changes during the build.** A new revision with a delta of rows. Who approves it.
7. **Reach of the files.** Other machines, cloud sessions and teammates cannot read local files. Push this repo to a private remote? Attach research to the ticket?
8. **A living spec.** OpenSpec merges delta specs into a current-behaviour spec. Later.
9. **Learning loop.** A lessons file that the plan stage reads (Compound Engineering's feed-forward).
10. **Models and cost** per subagent and per size.
11. **Tests of the workflow.** Pressure scenarios (superpowers `writing-skills`) and tracker write mocks that fail when a gate breaks.
12. **Git.** Settled: one repo, `turbiv-claude-plugins` (decisions 15–16). Open: does each stage commit and push, or only commit? Pushed work items would be visible to anyone who can read the repo.
13. **`omitClaudeMd`** needs a recent Claude Code version (EGM: 2.1.271 or later). Check the installed version.
14. **The ID scheme** and the folder name.
15. **Licence note.** The fork keeps superpowers' MIT licence text for the copied parts.
16. **Re-check after `NOT READY`.** Is a scoped re-check of the high findings enough, or must the full validator run again?

## 12. Package layout (proposal, 2026-11-18)

Modelled on the installed plugins: superpowers (prompt files next to `SKILL.md`, `hooks/`, `tests/`), EGM (`resources/` for shared standards), and the owner's own `planner` and `jira-guard` plugins in `turbiv-claude-plugins`.

```
<plugin>/                              # name: decision P2 ("flow" below)
  .claude-plugin/plugin.json           # name, version, skills dir, agents list
  README.md
  LICENSE-superpowers                  # MIT text for the forked parts
  skills/
    start/SKILL.md                     # /flow:start <goal>  — entry: intake, then runs the next stages
    research/SKILL.md                  # /flow:research <item> [depth]
    plan/SKILL.md                      # /flow:plan <item>
    spec/SKILL.md                      # /flow:spec <item>   — dispatches spec-writer
    validate/SKILL.md                  # /flow:validate <item|path to a spec> — dispatches spec-validator
    approve/SKILL.md                   # /flow:approve <item> — decision table, approval, push
    status/SKILL.md                    # /flow:status [item] — stage, open rows, next step; resume
    mirror/SKILL.md                    # /flow:mirror <item> pull|push — runs the tracker connector
  agents/
    repo-researcher.md                 # Read, Glob, Grep
    outside-researcher.md              # WebSearch, WebFetch, tracker read tools
    spec-writer.md                     # Read, Glob, Grep, Write (item folder)
    spec-validator.md                  # Read, Glob, Grep; omitClaudeMd
    tracker-jira.md                    # Jira tools; Read item; Write mirror/
  resources/                           # shared; skills point here, never copy
    templates/item.md, plan-summary.md, decisions.md, spec.md, validation.md, log.md
    rules/done-rules.md                # section 6.3
    rules/decision-table.md            # section 7
    rules/sizes.md                     # section 4
  hooks/                               # later (open question 2)
  evals/                               # later (open question 11)
```

- **Every stage is its own skill**, and the owner can call it alone with an item ID. Each skill checks that the files of the stage before it exist, and says what is missing. (Owner, 2026-11-18. The stage skills stay user-invocable.)
- **`start` is the entry.** It runs intake, then calls the next stage skills in order, and stops only at the stops of section 3. (Like the owner's `planner` plugin.)
- **`validate` also takes a path to any spec file,** so it works outside the flow.
- **Shared rules live once, in `resources/`.** Each stage skill stays short. (EGM `resources/document_standards/`; HumanLayer's instruction budget [secondary].)
- **The work store path** comes from one setting, with the default `~/git/turbiv-claude-plugins/work-items`, so the skills work from any repo or worktree. Never the plugin cache.
- **Repo layout** (decisions 15–17):

```
~/git/turbiv-claude-plugins/
  plugins/flow/            # the layout above, plus docs/design/ and docs/research/
  work-items/              # <id>/ folders (section 8.1)
```

## 13. Sources

Research files in [`../research/`](../research/), 2026-11-18:

- Main session: [synthesis](../research/synthesis.md), [elephant-goldfish-model](../research/elephant-goldfish-model.md), [superpowers](../research/superpowers.md), [other-workflows](../research/other-workflows.md).
- This session: [planning-rubric](../research/planning-rubric.md), [planning-comparison](../research/planning-comparison.md), [spec-kit](../research/spec-kit.md), [cc-sdd-kiro](../research/cc-sdd-kiro.md), [humanlayer-rpi](../research/humanlayer-rpi.md).

Source files read for this design:

- EGM `resources/document_standards/implementation-readiness-standard.md:12-33`, `skills/egm-draft/SKILL.md:60-71`.
- superpowers v7.0.2 `skills/brainstorming/SKILL.md` (read in full; line numbers in section 2.2), `skills/brainstorming/builder-check-prompt.md`, `skills/subagent-driven-development/SKILL.md:17-31`.

Web, 2026-11-18. [read] = fetched directly. [read, summarized] = through a summarizing fetch tool. [secondary] = a third-party summary.

- Kiro feature specs [read]: https://kiro.dev/docs/specs/feature-specs/
- Kiro bugfix specs [read]: https://kiro.dev/docs/specs/bugfix-specs/
- cc-sdd [read]: https://github.com/gotalab/cc-sdd
- Anthropic, Effective harnesses for long-running agents [read, summarized]: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Claude Code best practices [read]: https://code.claude.com/docs/en/best-practices
- HumanLayer riptide-rpi skills [read]: https://github.com/humanlayer/humanlayer/tree/main/apps/riptide-rpi-claude-plugin/skills
- HumanLayer instruction budget [secondary, unverified]: https://www.zenml.io/llmops-database/evolving-ai-coding-agent-workflows-from-research-plan-implement-to-crispy
- OpenSpec concepts [read]: https://github.com/fission-ai/openspec/blob/main/docs/concepts.md
- Spec Kit spec template [read]: https://github.com/github/spec-kit/blob/main/templates/spec-template.md
- Superpowers criticism [secondary]: https://news.ycombinator.com/item?id=47623101 ; https://mcp.directory/blog/superpowers-skill-worth-it-2026 ; https://newreleases.io/project/github/obra/superpowers/release/v6.4.2
- Full web notes: `web-research-done-patterns.md` in the session notes folder.
