# GitHub Spec Kit: planning and spec stages

2026-11-18. Scope: stages before implementation only. All `path:line` citations refer to the commit below. Paths are relative to the repo root.

Short cite forms: `specify.md`, `clarify.md`, `plan.md`, `tasks.md`, `analyze.md`, `checklist.md`, `implement.md`, `constitution.md`, `converge.md` = `templates/commands/<name>`. `spec-template.md`, `plan-template.md` = `templates/<name>`. `claude/__init__.py` = `src/specify_cli/integrations/claude/__init__.py`. `taskstoissues.md` = `extensions/github/commands/speckit.github.taskstoissues.md`. `agentic-sdd.md` = `docs/reference/agentic-sdd.md`. `workflow.yml` = `workflows/speckit/workflow.yml`. `customization.md` = `docs/how-to/customization.md`. A bare `:N` refers to the last file named.

Tags: `[implemented]` = in a prompt or code. `[claimed]` = docs only. `[secondary]` = third party.

## 1. Identity

| Item | Value |
|---|---|
| Repo | https://github.com/github/spec-kit |
| Commit read | `59d61c59630c3bd5a294f4c23e43a60d8ab98d02` (2026-11-17), package version `1.4.3.dev0` (`pyproject.toml:3`), last release v1.4.2 on 2026-11-17 |
| Licence | MIT (`LICENSE:1`) |
| Popularity | About 150k stars, 13.5k forks, 223 open issues, about 350 contributors (GitHub API, 2026-11-18) |
| Last push | 2026-11-17 |
| Maintenance | Very active. Three releases in 7 days (v1.4.0 to v1.4.2). The project has CI, CodeQL and Dependabot (`docs/guides/agentic-sdlc.md:264-272`). |

Spec Kit is a Python CLI (`specify`). It installs Markdown command prompts into an agent. For Claude Code, it installs them as skills in `.claude/skills/speckit-<command>/SKILL.md` (`docs/integrations/claude.md:22-24`) [implemented].

## 2. Stages before implementation

The documented order is constitution → specify → clarify → plan → checklist → tasks → analyze → implement → converge (`docs/reference/agentic-sdd.md:15`). Only `specify` is required before `plan`. Clarify, checklist and analyze are optional quality gates (`docs/reference/agentic-sdd.md:5`) [claimed].

| Stage | Input | Output file | Subagents | Human gate |
|---|---|---|---|---|
| constitution | Principles text, repo context | `.specify/memory/constitution.md`, semver-bumped (`templates/commands/constitution.md:77-127`, `:100-103`) | None | None. It asks only when the version bump is ambiguous (`:104`). |
| specify | Free text after the command (`templates/commands/specify.md:62`) | `specs/NNN-short-name/spec.md`, `checklists/requirements.md`, `.specify/feature.json` (`:84-110`, `:150`) | None | Up to 3 batched questions, only if `[NEEDS CLARIFICATION]` markers remain (`:203-236`) |
| clarify | `spec.md` | `spec.md` updated in place, with a `## Clarifications` section (`templates/commands/clarify.md:182-196`) | None | Up to 5 questions, one at a time (`:129-141`) |
| plan | `spec.md`, constitution, tech-stack text | `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` (`templates/commands/plan.md:62-72`, `:159`) | Prompt says "dispatch research agents" (`:121-128`) | A constitution gate that stops with ERROR if a violation has no justification (`:69`, `:164`) |
| checklist | Focus text, spec, plan, tasks | `checklists/<domain>.md` (`templates/commands/checklist.md:139-148`) | None | Up to 3 questions, then 2 more (`:90-120`). A human ticks the items (`:30-36`). |
| tasks | `plan.md`, `spec.md`, optional design docs | `tasks.md` (`templates/commands/tasks.md:65-94`) | None | None |
| analyze | `spec.md`, `plan.md`, `tasks.md` | Report in chat only, no file (`templates/commands/analyze.md:58`, `:177`) | None | Remediation edits need approval (`:222`) |

The implement command reads checklist state as a gate. It stops and asks if any item is unchecked (`templates/commands/implement.md:56-86`) [implemented].

An optional YAML workflow runs specify → gate → plan → gate → tasks → implement. It skips clarify, checklist and analyze (`workflows/speckit/workflow.yml:43-80`) [implemented]. Each workflow step runs as a separate `claude -p` process (`docs/integrations/claude.md:73-75`).

## 3. Questions

Spec Kit has two separate question mechanisms. Their behaviour is different.

**specify** [implemented]:
- The agent makes "informed guesses" and records them under Assumptions (`specify.md:126-138`, `:301-302`).
- It adds a `[NEEDS CLARIFICATION]` marker only when the choice changes scope or UX, has several reasonable readings, and has no default. The maximum is 3 markers (`:128-132`). Priority is scope > security > UX > technical (`:133`).
- It shows all questions together and waits for one reply, for example "Q1: A, Q2: Custom, Q3: B" (`:233-234`).
- Each question has a table with options A–C plus Custom and their implications (`:215-222`). It gives **no recommended option**.
- It lists defaults that it must not ask about, for example retention, performance and auth method (`:314-320`).

**clarify** [implemented]:
- It scans a 10-category taxonomy for ambiguity (`clarify.md:73-123`).
- It keeps a private queue of at most 5 questions (`:129-138`).
- It asks **exactly one question at a time** and never shows the next questions in advance (`:141`, `:179`).
- Every multiple-choice question has a **recommended option** with 1–2 sentences of reasoning (`:148-155`). The user can reply "yes" to accept it (`:165`, `:171`). Short-answer questions have a "Suggested" answer (`:167-169`).
- There is no exception for critical or scope-changing questions. These also get a recommendation.
- It saves the spec after each answer (`:196`).
- It can ask zero questions (`:180`, `:231`). Items over the limit go to "Deferred" (`:237`). Skipping clarify gives a rework-risk warning (`:60`).

**checklist** asks up to 3 questions about scope, depth and audience, then up to 2 more (`checklist.md:90-120`).

## 4. Research

- Research has no depth setting.
  - `/plan` Phase 0 always runs. It makes one research task for each NEEDS CLARIFICATION item, each dependency and each integration (`plan.md:116-119`).
  - It consolidates the results in `research.md` as Decision / Rationale / Alternatives considered (`:130-133`).
- The prompt tells the agent to "dispatch research agents" (`plan.md:121-128`). Claude Code may spawn them, but Spec Kit defines no agent and does not require one. For Claude Code, no command runs in a forked context. `FORK_CONTEXT_COMMANDS` is empty on purpose. The comment says the long `/analyze` report bloated the main context and froze long sessions (`claude/__init__.py:36-47`) [implemented].
- Research is not blinded. Each task text carries the feature context (`plan.md:124-127`). The plan command itself runs with the full spec and the user's intent.
- The bundled `assess` extension has a separate research stage before specify. It collects evidence for and against an idea (`extensions/assess/README.md:42`; bundled per `extensions/catalog.json:22-27`). It is for product discovery, not technical research.

## 5. Plan and spec

**Order and binding.**
- In Spec Kit, the spec comes first and the plan comes second.
- `spec.md` is the "what and why". It must contain no tech stack or code structure and is "written for business stakeholders" (`specify.md:286-288`).
- `plan.md` is the "how".
- The spec is binding. `/analyze` treats spec requirements as the reference for coverage checks (`analyze.md:116`, `:148-152`).
- The plan is also templated and gated. It is not free-form.
- Mapping to the owner's terms: Spec Kit's spec is a binding requirements document. It has no technical spec with a definition of done after a free-form plan.

**`spec.md` headings** (`templates/spec-template.md`):
- `# Feature Specification` (`:1`)
- `## User Scenarios & Testing` (mandatory). It contains `### User Story N - [Title] (Priority: Pn)` with "Why this priority", "Independent Test" and Given/When/Then "Acceptance Scenarios" (`:11-37`).
- `### Edge Cases` (`:71`)
- `## Requirements` (mandatory), with `### Functional Requirements` (FR-001…) and `### Key Entities` (`:81-104`)
- `## Success Criteria` (mandatory), with `### Measurable Outcomes` (SC-001…) (`:106-118`)
- `## Assumptions` (`:120-131`)
- `/clarify` adds `## Clarifications`.

**`plan.md` headings** (`templates/plan-template.md`):
- Summary (`:9`)
- Technical Context (`:13-37`)
- Constitution Check, a gate (`:39-43`)
- Project Structure (`:45-104`)
- Complexity Tracking (`:106-112`)
- Separate files: research, data model, contracts and quickstart (`plan.md:137-159`).

**Length.**
- The core templates are 131 lines (spec) and 113 lines (plan) before they are filled in.
- One field test produced about 2,000 lines of plan-stage Markdown for one feature and 2,577 lines of Markdown in total [secondary, Eberhardt, see §11].

## 6. Definition of done

The spec defines done in three ways [implemented]:
- Each user story has Given/When/Then acceptance scenarios and an "Independent Test" (`spec-template.md:32-37`).
- Each requirement has an FR-### ID, and each requirement "must be testable" (`specify.md:136-137`).
- Success Criteria SC-### must be measurable, technology-agnostic and user-focused (`specify.md:139-142`, `:322-343`). For example, the prompt rejects an API response-time target in favour of a user-facing one (`:340`).

How done is checked:
- Before build, `/analyze` maps each FR/SC to tasks and reports coverage % (`analyze.md:116`, `:148-152`, `:203-210`). It excludes business-KPI success criteria (`:116`).
- After build, `/converge` checks the code against each FR, SC and acceptance scenario. It appends tasks for the gaps (`templates/commands/converge.md:133-166`).
- In both cases, the same agent that did the work does the check. No separate checker exists.

Gap for the owner: technology-agnostic success criteria are not a technical definition of done. Examples of a technical definition of done: tests pass, an endpoint returns X, a file exists. Test tasks are optional by default (`tasks.md:148`).

## 7. Validation

| Check | Who | Fresh context? | When | Rounds |
|---|---|---|---|---|
| Spec quality checklist (16 items, `specify.md:150-187`) | The same agent that wrote the spec | No | Always, inside `/specify` | Up to 3 fix iterations, then warn (`:197-201`) |
| Re-check of that checklist | The same agent | No | Inside `/clarify` (`clarify.md:210-227`) | 1 |
| `/checklist` "unit tests for English" (`checklist.md:9-28`) | The agent writes questions. A **human** ticks them. The command must not tick items (`:32-36`). | n/a | Optional | Append-only (`:145-147`) |
| `/analyze`: duplication, ambiguity, underspecification, constitution, coverage and inconsistency passes, with severity levels (`analyze.md:123-173`) | The same agent, read-only (`:58`) | No (forked mode was removed, see §4) | Optional. Only **after** `tasks.md` exists (`:54`). | The user re-runs it until clean (`agentic-sdd.md:121`) |
| Workflow gates | Human approve/reject (`workflow.yml:50-68`) | n/a | Only in `specify workflow run` | 1 per gate |

Spec Kit has no subagent validator. No check asks "can an implementation agent use this without guessing?". The nearest is the `tasks.md` rule that each task must be specific enough for an LLM with no extra context (`tasks.md:142`). Nothing checks this rule.

## 8. Decisions

Decisions are spread across several places [implemented]:
- AI defaults go under `## Assumptions` (`spec-template.md:120-131`).
- Human answers go under `## Clarifications` as `- Q: … → A: …` (`clarify.md:187`).
- Technical choices go in `research.md` as Decision/Rationale/Alternatives (`plan.md:130-133`).
- Justified constitution violations go under Complexity Tracking (`plan-template.md:106-112`).

No single table shows "AI decided (reason)" next to "owner must decide".

The `/clarify` coverage table lists categories, not decisions (`clarify.md:282`). Recommendations: see §3.

## 9. State and trackers

**Files.**
- All state is local Markdown in the repo:
  - `specs/NNN-name/` (`specify.md:86-95`)
  - `.specify/memory/constitution.md`
  - `.specify/feature.json`, which points later commands to the active feature (`specify.md:103-110`; `scripts/bash/common.sh:77-97`) [implemented].
- Branch creation is an optional git extension hook (`specify.md:78-82`).

**Resume.**
- Each command reads the files from disk again, so a new session can continue.
- Workflow runs have run IDs, persisted state, and `specify workflow resume` (`docs/workflows/overview.md:27-34`, `:62-65`) [implemented].

**Trackers.**
- GitHub Issues is first-party: the bundled `github` extension, `/speckit-github-taskstoissues` (`extensions/catalog.json:68-73`) [implemented].
  - It is one-way. It creates one issue for each task, titled `T001: …`, through the GitHub MCP server (`taskstoissues.md:3`, `:68`).
  - It deduplicates by task ID (`:67`).
  - It refuses to run if the git remote is not GitHub (`:58-65`, `:73`).
  - It does not sync status back and does not mirror the spec.
- Jira and Linear support exists only as community extensions, for example `"verified": false` at `extensions/catalog.community.json:3381`. Maintainers do not review community code (`extensions/README.md:28`). Jira entries in `extensions/catalog.community.json`: "Jira Integration" (`:3355-3357`), "Spec Kit lifecycle for Jira" (`:3388-3390`), "Jira Mirror" (`:3438-3440`), and "Jira Integration (Sync Engine)", one Story per spec (`:3478-3480`). All are [claimed]. I did not read their code.
- The model "local files are truth, tracker is a mirror" matches Spec Kit's design.

## 10. Sizing

Spec Kit has no automatic per-task sizing.

What exists:
- clarify, checklist and analyze are optional (`agentic-sdd.md:5`). Clarify can end with no questions (`clarify.md:231`).
- The bundled `lean` preset replaces specify, plan and tasks with prompts of about 20 lines each (`presets/lean/README.md:7`; `presets/lean/commands/speckit.specify.md:1-23`) [implemented].
  - A preset is installed **per project** (`specify preset add lean`). Commands are copied into the agent folder at install time (`docs/how-to/customization.md:87-91`). So you cannot pick lean or full for each task.
  - Lean `/specify` first asks the user for a directory path and waits (`presets/lean/commands/speckit.specify.md:13`).
- Implement guidance: run once for a small feature, in stages for a large one (`agentic-sdd.md:129-139`). This applies to build only.
- The project's own practice: "A small change can stay in an issue and PR" (`docs/guides/agentic-sdlc.md:284`). That means Spec Kit is not used for small changes. [claimed]
- `/specify` fails with an error when it cannot find a user flow (`specify.md:134-135`). Technical chores such as "fix the importer" fit the user-story template badly.

## 11. Evidence it works

**Tests.** The repo has 68 test entries. They cover the CLI, scripts, catalogs and template text.
- Prompt tests only check for strings. Example: `tests/test_clarify_stage_gate.py:1-24` checks that a sentence is present in `clarify.md`.
- One test says directly that it does "not execute an LLM or assert how an LLM will respond" (`tests/test_converge_template_scaffold.py:5-6`).
- I found no behavioural evals of the prompts. [implemented: none]

**Claims.**
- Specs become "executable" and the "source of truth" (`spec-driven.md:51`, `:71`). [claimed]
- The project used SDD to build its own bundler feature (`docs/guides/agentic-sdlc.md:269`). [claimed]

**Real-world reports.**
- Birgitta Böckeler (martinfowler.com, 15 Oct 2025) [secondary]:
  - Spec Kit felt like too much process for a 3–5 point feature.
  - It produced many repetitive Markdown files.
  - She preferred to review code over these files.
  - The agent took research notes about existing classes as new requirements and generated duplicates.
  - It sometimes followed constitution articles too eagerly.
- Colin Eberhardt (Scott Logic, 26 Nov 2025) built two features with Spec Kit [secondary]. They produced 2,577 and 2,262 lines of Markdown and needed about 3.5 and 2 hours of review. Iterative prompting on the same features needed about 8 minutes of agent time and 15 minutes of review. He calls Spec Kit about ten times slower with no visible quality gain.
- Other blogs and HN comments praise traceability. They report token cost, review load and spec drift. [secondary]
- Both critiques are from late 2025, before v1.4.x. The volume complaint still applies to the core templates.

## 12. Fit score

| ID | Score | Reason | Citation |
|---|---|---|---|
| Q1 | partly | Takes free text of any length, but forces a user-story spec. It errors if it finds no user flow. | `specify.md:62`, `:134-135` |
| Q2 | fits | Guesses defaults. Asks only on high-impact items (max 3). Clarify is optional and can ask zero. | `specify.md:126-133`; `clarify.md:231` |
| Q3 | no | Plan Phase 0 always researches every unknown. No depth option. | `plan.md:116-128` |
| Q4 | no | Plan always produces five full artifacts. The Summary is one section, not the default view. Field reports show about 2,000 lines. | `plan.md:159`; `plan-template.md:9-11` |
| Q5 | partly | A binding spec with acceptance scenarios and SC IDs exists. But it comes before the plan, is non-technical, and the plan is templated. | `specify.md:286-288`; `spec-template.md:106-118` |
| Q6 | no | The spec is written in the main context. No subagents. Fork mode is disabled. | `claude/__init__.py:36-47` |
| Q7 | partly | An always-on self-checklist exists, but it is not a fresh validator. `/analyze` is optional and runs only after tasks. | `specify.md:189-201`; `analyze.md:54` |
| Q8 | partly | `/specify` batches its questions in one message. `/clarify` asks one at a time. No AI-vs-owner decision table. | `specify.md:233`; `clarify.md:141` |
| Q9 | partly | `/clarify` always recommends, including on critical questions. `/specify` never recommends. | `clarify.md:154-155`; `specify.md:215-224` |
| Q10 | fits | Local `specs/` files are the truth. The GitHub mirror is one-way. Jira exists only through unverified community extensions. | `specify.md:86-110`; `taskstoissues.md:68`; `extensions/README.md:28` |
| Q11 | partly | Gates are optional and a lean preset exists, but it applies per project. No automatic sizing. | `agentic-sdd.md:5`; `customization.md:87-91` |
| Q12 | fits | First-party Claude Code integration. Skills only, no subagent definitions. | `docs/integrations/claude.md:22-24` |

## 13. Tailoring cost

If Spec Kit is the base, these changes are necessary:

1. **Decision handling (Q8, Q9). Cost: high.**
   - Replace the one-at-a-time loop in `/clarify` with one decision table. The table has two parts: decisions the AI made (with reason) and decisions the owner must make.
   - Keep the recommended answer as the default.
   - Remove the recommendation from critical rows (scope change or out of scope).
   - Combine Assumptions, Clarifications and `research.md` decisions into that one table.
2. **Subagents (Q6, Q7). Cost: high.**
   - Add a spec-writer subagent and a fresh-context validator subagent. The validator always runs and checks that an implementer can work "without guessing".
   - Spec Kit has no agent definitions. The Claude adapter turned off forked context because of report bloat (`claude/__init__.py:39-46`). The validator must therefore return a short verdict.
   - `/analyze`'s detection passes and severity levels make a good validator prompt. Run it on the spec before tasks, not after.
3. **Order, size and depth (Q3, Q4, Q5, Q11). Cost: medium to high.**
   - Change the order: a short free-form plan summary first, then a binding spec with a technical definition of done.
   - Merge the five plan artifacts into one short file, with detail only on request.
   - Add a size choice for each task (small / medium / large) and a research depth choice (none / quick / deep). Presets work per project, so this needs a new entry command.
   - Accept non-user-story goals, such as chores and fixes.
4. **Jira mirror (Q10). Cost: low to medium.** Build or vet a one-way mirror. The deduplication by ID in `taskstoissues` is a good pattern.
5. **CLI dependency and boilerplate. Cost: low to medium.** Every core command runs `{SCRIPT}` and the template resolver from the `specify` CLI (`specify.md:11-14`, `:99`; `clarify.md:64`; `plan.md:62`). Keep the CLI, or replace these calls with plain file reads. Remove the extension-hook blocks in every command (for example `specify.md:27-58`, `:240-272`) if you do not use extensions.

**Keep as is:**
- Spec template: FR/SC IDs, Given/When/Then, Independent Test, Assumptions (`spec-template.md`).
- Guess-first, max-3-questions rule and do-not-ask defaults (`specify.md:126-133`, `:314-320`).
- Clarify taxonomy as an internal checklist (`clarify.md:73-123`).
- Decision/Rationale/Alternatives format (`plan.md:130-133`).
- `/analyze` passes and coverage table (`analyze.md:123-210`).
- Checklist "unit tests for requirements" idea (`checklist.md:9-28`).
- `specs/NNN-name/` plus `feature.json` for state.
