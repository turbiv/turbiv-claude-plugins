# HumanLayer riptide-rpi (QRSPI / "CRISPY") as a base for planning and spec

2026-11-18. Scope: stages before implementation only. Rubric: `research/planning-rubric.md`.

Path abbreviations used in citations:

- `P/` = `apps/riptide-rpi-claude-plugin/skills/` (the plugin)
- `D/` = `apps/riptide-daemon/src/` (HumanLayer daemon, not part of the plugin)
- `L/` = legacy `.claude/commands/` at commit `99abe67` (2026-06-19), now deleted

Tags: `[implemented]` = in prompt or code, `[claimed]` = docs or essay only, `[secondary]` = third party.

## 1. Identity

| Item | Value |
|---|---|
| Repo | https://github.com/humanlayer/humanlayer, path `apps/riptide-rpi-claude-plugin/` |
| Commit read | `2f5b58d3dfd18b13f4456b67ab0787df44233231` (repo head, 2026-11-15) |
| Plugin last changed | 2026-10-22, commit `d8197bab` "HumanLayer: the desktop app, daemon, CLI, web UI, API, and plugins". It replaced the earlier open-source code (kept on the `legacy` branch). |
| Plugin version | 0.50.0 (`.claude-plugin/plugin.json`) |
| Licence | Apache-2.0 (plugin `LICENSE`; repo `LICENSE` + `NOTICE`, © QueryTale Inc. d/b/a HumanLayer) |
| Popularity | Monorepo: 12.9k stars, 1.1k forks, pushed 2026-11-16. ACE essay repo: 2.8k stars, **no licence**. |
| Install target in README | `humanlayer/riptide-rpi` (`README.md:8`): 8 stars, last push 2025-12-29, holds one stale skill only. `humanlayer/humanlayer-claude` (named in `apps/riptide-claude-code-plugin/README.md:10`): HTTP 404. |
| Maintenance | **At risk.** PR #1167 says "HumanLayer Cloud is shutting down as HumanLayer joins Factory" and points users to self-host `[implemented]`. Factory acquired HumanLayer on 2026-11-04, with at least 30 days of hosted access `[secondary]`. |

The plugin has skills only. It has no `agents/` folder. The seven subagents (four research, two implementer, one reviewer) are TypeScript objects in the daemon (`D/agents/claudecode/agents/*.ts`). The daemon writes them into its own sessions.

## 2. Stages before implementation

The default ("RPI") chain is Questions → Research → Design → Structure outline → Plan. Each stage is a separate skill and a separate session. Each skill is manual-invoke only (`description: Only use when the user explicitly invokes this skill by name`, e.g. `P/create-plan/SKILL.md:3`).

| Stage | Input | Output file | Subagents | Human gate |
|---|---|---|---|---|
| create-research-questions | `ticket.md`/`task.md` + user text (`P/create-research-questions/SKILL.md:18-24`) | `NN-research-questions-*.md` (`:80-87`) | locator, analyzer, pattern-finder, web (light pass) (`:26-44`) | User may edit; "You do not need to answer these questions" (`references/research_questions_final_answer.md:7`) |
| create-research | research-questions doc only (`P/create-research/SKILL.md:21,30`) | `NN-research-*.md` (`:85-100`) | 2–6 parallel agents (`:50-72`), plus one extra pass for open questions (`:102-105`) | User reviews open questions (`:267-279`) |
| create-design-discussion | ticket + research; not the questions doc (`P/create-design-discussion/SKILL.md:12-23`) | `NN-design-discussion-*.md` (`:59-66`) | optional (`:25-47`) | **Yes.** All questions open; only the user resolves (`:78-83`) |
| create-structure-outline | all task files except questions (`P/create-structure-outline/SKILL.md:17-26`) | `NN-structure-outline-*.md` (`:96-103`) | optional, foreground only (`:28-36`) | User reviews phases and verification (`references/structure_outline_final_answer.md:5-8`) |
| create-plan | all task files except questions (`P/create-plan/SKILL.md:12-16`) | `NN-plan-*.md` (`:27-28`) | none named | No explicit gate; next step is the worktree (`references/plan_final_answer.md:3-6`) |

Companions: `iterate-research-questions`, `iterate-research`, `iterate-design-discussion`, `iterate-structure-outline` and `iterate-plan` update the same file in place. They must verify user corrections before they accept them (`P/iterate-plan/SKILL.md:20-24`, `P/iterate-structure-outline/SKILL.md:41-45`). `iterate-prd` and `iterate-tdd` keep the one-question interview (`P/iterate-prd/SKILL.md:14`, `P/iterate-tdd/SKILL.md:14`). `review-artifact-comments` needs the HumanLayer MCP comment tools (`P/review-artifact-comments/SKILL.md:10-15`).

Alternative chain ("prd_tdd"): Research → `create-prd` → `create-tdd`. The daemon routes it (`D/agents/claudecode/hooks/workflow-routing-hook.ts:85-112`). "outline_only" skips `create-plan`, and implementation runs from the outline (`:13-56,84`).

## 3. Questions

- **Research questions are for an agent, not the user.** The skill writes 2–8 questions, scaled to the task (`P/create-research-questions/SKILL.md:64,76`). The user does not answer them.
- **Design discussion batches all decisions in one document.** Each question has options, pros and cons, and a recommendation (`P/create-design-discussion/SKILL.md:73-75`; template `references/design_discussion_template.md:34-46`). The user answers in free text, in any order. "Any clear indication of a decision counts" (`SKILL.md:86-87`).
- **PRD and TDD ask one question at a time.** "Exactly one question per message" (`P/create-prd/SKILL.md:14`; `P/create-tdd/SKILL.md:19,102,177`). Each question has a recommendation.
- **Skipping is not possible.** The design skill never skips the question list. Only the product's "oneshot" workflow skips stages (§10).
- Legacy `create_plan` asked chat questions only when code could not answer them (`L/create_plan.md:74-89`).

## 4. Research

- **Depth.** No none/quick/deep switch exists. Depth is set by the number of questions (`P/create-research-questions/SKILL.md:64`) and by agent fan-out (`P/create-research/SKILL.md:67`). Web research runs "only if needed" (`P/create-research-questions/SKILL.md:42-44`). `iterate-research` runs web research only if the user asks (`P/iterate-research/SKILL.md:55`).
- **Blinding `[implemented]`.** The questions must not leak the task: "ONLY 'HOW DOES IT WORK'" (`P/create-research-questions/SKILL.md:68`). The research skill "may NEVER read `ticket.md`/`task.md`" (`P/create-research/SKILL.md:30,40`; again in `P/iterate-research/SKILL.md:21,29`). The only input is the questions document. Research is descriptive only: no critique and no recommendations (`P/create-research/SKILL.md:10-17`). The research-questions author is **not** blinded, because it reads the ticket. The legacy `research_codebase` was not blinded: it read ticket files first (`L/research_codebase.md:31`).
- **Subagents** (all from `D/agents/claudecode/agents/`). The plugin forbids `general-purpose`, `Explore` and `Plan` (`P/create-research/SKILL.md:52`).

| Agent | Tools | Model |
|---|---|---|
| codebase-locator | Grep, Glob, Bash, Skill (`codebase-locator.ts:6-7`) | sonnet |
| codebase-analyzer | Read, Grep, Glob, Bash, Skill (`codebase-analyzer.ts:6-7`) | sonnet |
| codebase-pattern-finder | Grep, Glob, Read, Bash, Skill (`codebase-pattern-finder.ts:6-7`) | sonnet |
| web-search-researcher | WebSearch, WebFetch, TodoWrite, Read, Grep, Glob, Bash, Skill (`web-search-researcher.ts:6-7`) | sonnet |

The agents see only the orchestrator's prompt. The agent prompts repeat the "document what exists, no critique" rule (`codebase-analyzer.ts:10-17`).

- **Output style.** Headers state the takeaway, not the topic. The document uses tables, mermaid diagrams, call trees and testing patterns for each section (`P/create-research/SKILL.md:124-239`).

## 5. Plan and spec

There is no artifact called "spec". The functional equivalents:

- **Design discussion.** Headings: Summary of change request, Current State, Desired End State, What we're not doing, Proposed End State Architecture, Design Questions, Resolved Design Questions, Patterns to follow (`references/design_discussion_template.md:9-67`). It is about 200 lines `[secondary]`.
- **Structure outline** ("our 'c header files'", `P/create-structure-outline/SKILL.md:160`). Headings: title + 2–3 sentence summary, Desired End State, Implementation Overview (phase checkboxes), then `## Phase N` → `### Change Outline` → `### Validation` → `#### Automated Verification` / `#### Manual Verification`, and finally `## Open Questions` (`references/structure_outline_template.md:9-105`). Phases must be vertical slices (`SKILL.md:51-76`).
- **Plan.** Headings: Overview, Current State Analysis (Key Discoveries), Desired End State, What We're NOT Doing, Implementation Approach, then `## Phase N` → `### Changes Required` (file + diff code) → `### Success Criteria` → `#### Automated Verification` / optional `#### Manual Verification` (`P/create-plan/references/plan_template.md:9-106`). The plan is long because it holds code for each change (`P/create-plan/SKILL.md:30,36`).
- **Binding.** The latest document wins: "plan > structure outline > design discussion > research > ticket"; "The plan is the final authority" (`P/create-plan/SKILL.md:42-48`). In "outline_only", the outline is the last and binding document.
- **Mapping to Q5.** The design discussion is the short decision document. The outline or plan carries the definition of done and binds the work. So the owner's "free-form plan, binding spec" split corresponds to "design discussion + outline (reviewed)" and "plan (binding, with criteria)". This is the reverse of the owner's naming.

## 6. Definition of done

- **Format.** For each phase, a checkbox list in two parts. *Automated Verification* holds runnable commands. *Manual Verification* holds human steps (`P/create-structure-outline/SKILL.md:163-173`; `P/create-plan/references/plan_template.md:73-88`). Manual steps are optional: "don't put steps for manual validation just to have them" (`P/create-plan/SKILL.md:101-103`). Automated checks are preferred (`P/create-structure-outline/SKILL.md:57,173`).
- **Who checks.** The implementer agent runs the success-criteria checks, ticks the plan boxes, then pauses for the human (`D/agents/claudecode/agents/implementer-agent.ts:46-53`). After each phase, a human confirms the manual checks (`plan_template.md:87`; `P/create-plan/SKILL.md:39`).
- There is no plan-level or feature-level definition of done other than "Desired End State" prose (`plan_template.md:24-26`). PRD has a "business success" metric that it treats "as part of the definition of done" (`P/create-prd/SKILL.md:100`).

## 7. Validation

- **No validator of the spec or plan before build `[implemented]`.** No subagent reviews the outline or plan. The only check is that the main agent verifies user corrections (`P/iterate-plan/SKILL.md:20-24`).
- The **open-questions gate** is an LLM classifier in the product. It counts open versus resolved design questions after each write (`packages/ai/src/agents/design-doc-open-questions/check-if-design-doc-has-open-questions.ts:24-49`; `D/lib/artifact-sync-utils.ts:62-77`). When zero questions remain, it switches the reply to "proceed to outline". It checks completeness only, not correctness.
- `grind-design-discussion` (repo-local `.claude/skills/`, **not shipped** in the plugin) is an autonomous self-review. It mines assumptions, verifies patterns and adds questions, and it must not answer them (`.claude/skills/grind-design-discussion/SKILL.md:18-47`). It runs in the main context, not in a fresh one.
- `implementation-reviewer` compares the plan with the finished code, for PR text (`D/agents/claudecode/agents/implementation-reviewer.ts:4-5`). Legacy `validate_plan` also ran after implementation (`L/validate_plan.md:7`). Both are out of scope for this report.

## 8. Decisions

- Decisions are recorded in the design discussion. Open questions are in "Design Questions" with a recommendation line (`references/design_discussion_template.md:46`). Resolved questions move to "Resolved Design Questions" with the option chosen, the rationale and the rejected options (`:53-59`; `SKILL.md:85-89`).
- **The AI decides nothing** (`P/create-design-discussion/SKILL.md:78-83`). So no "decided by AI, with reason" column exists. Small choices that the AI makes go into the architecture and pattern sections without being labelled as decisions.
- A recommendation is always given and is never the default. There is no class of critical decisions that gets no recommendation.

## 9. State and trackers

- **Files.** `.humanlayer/tasks/<TASK>/NN-<type>-<slug>.md`, with chronological `NN-` prefixes (`P/create-research-questions/SKILL.md:80-87`). In the product, this folder is a symlink to `~/.humanlayer/riptide/artifacts/`, and files sync to the cloud (`apps/riptide-claude-code-plugin/README.md:51`). The skills therefore require `ls -La` and forbid Grep/Glob on it (`P/create-design-discussion/SKILL.md:13,22`). Front matter records `type`, repo, branch and sha (`references/design_discussion_template.md:1-7`).
- **Trackers.** The skills contain no tracker calls. The manifest claims "Linear and Jira" (`.claude-plugin/plugin.json:3`) `[claimed]`. In the product, the API writes the Linear ticket as a `ticket.md` artifact (`apps/riptide-api/src/lib/linear-ticket-artifacts.ts:184-197`); a Jira formatter also exists (`format-jira-ticket.ts`, not read). The legacy `/linear` command managed tickets through a Linear MCP server (`L/linear.md:7-13`). The daemon hook attaches each artifact's cloud URL back to the Linear issue or Jira remote link (`D/agents/claudecode/hooks/artifact-sync-hook.ts:176-200`) `[implemented]`. The tracker is the source of the ticket, and the artifacts are linked back to it. Without the product, there is no tracker integration.
- **Resume.** Each stage is a fresh session that rediscovers state with `ls -La` of the task folder (e.g. `P/create-plan/SKILL.md:14-15`). The product can auto-advance between stages. The flags default to off (`apps/riptide-humanlayer-claude-plugin/skills/orchestrate/references/auto-advance.md:3-24`).

## 10. Sizing

- **In the plugin, almost none.** Research question count scales with the task (`P/create-research-questions/SKILL.md:64,76`). Manual verification is optional. The design skill always runs in full.
- **In the product.** Each task has a workflow type: `rpi`, `outline_only`, `prd_tdd`, `oneshot` or `freeform` (`D/agents/claudecode/hooks/workflow-routing-hook.ts:58-115`; `D/effects/services/claude-sessions/prepare-claude-session.ts:68`). The docs say oneshot is for "a clear and small change" and "The workflow does not require every phase for every task" (docs.humanlayer.com/explanation/workflow-phases) `[claimed]`. A search summary of HumanLayer material says oneshot covers about 40% of tasks `[claimed]`, unverified. The type is set per task; auto-advance defaults are proposed per workflow type (`auto-advance.md:13-22`). A classifier exists, but it classifies intent (research / design / implementation), not size (`packages/ai/src/agents/classify-task-intent/classify-task-intent.ts:10-17`). Nothing picks the workflow type from task size.

## 11. Evidence it works

- `[implemented]` An eval for the open-question counter runs on Sonnet 4.6 and GPT-5 (`packages/ai/eval/design-doc-open-questions/design-doc-open-questions.test.ts:8-11`). No eval of plan or spec quality was found.
- `[claimed]` ACE essay: a BAML bug fix in a 300k LOC Rust codebase was approved overnight. 35k LOC (cancellation and WASM) were drafted in 7 hours. The intended context use is 40–60% (`ace-fca.md:56-60,218,294`). The essay also reports a failure: the parquet-java Hadoop removal failed because the research "didn't go deep enough" (`ace-fca.md:314`). It states that expert human engagement is required (`:304,316`).
- `[secondary]` The QRSPI/CRISPY talk (2026, as summarised by Lavaee and search summaries) says the old `create_plan` had 85+ instructions and needed "magic words" to be interactive. It says reviewing long plans gave false confidence, so HumanLayer split the work into stages of fewer than 40 instructions each and added the design discussion as the "brain surgery" point. Horthy reversed his earlier "read plans, not code" advice.
- `[secondary]` Criticism: going from 3 to 8 stages adds ceremony, and people may skip steps. Reviewers became attached to plans that they had invested in. Independent critiques are few. Most sources are HumanLayer describing its own changes.
- `[implemented]` Defects found while reading:
  - `show-me.md` is a symlink into another plugin, and it breaks in a sparse or standalone copy (`P/create-design-discussion/references/show-me.md` → `../../../../riptide-humanlayer-claude-plugin/...`).
  - The `create-plan` output condition starts with `" OR git-dir …"`, so the clause is empty (`P/create-plan/SKILL.md:62`).
  - The legacy commands that the ACE essay links (`ace-fca.md:230-246`) are 404 at `main`.

## 12. Fit score

| ID | Score | Reason | Citation |
|---|---|---|---|
| Q1 | partly | Reads a ticket file or user text. No rule for a few-word goal. PRD says "a couple of sentences" is enough. | `P/create-research-questions/SKILL.md:18-24`; `P/create-prd/SKILL.md:43` |
| Q2 | partly | The design document always lists questions. Only the product's oneshot workflow skips them. | `P/create-design-discussion/SKILL.md:78-83`; `workflow-routing-hook.ts:113` |
| Q3 | partly | Depth scales by question count and fan-out. No none/quick/deep choice for the owner. | `P/create-research-questions/SKILL.md:64,76`; `P/create-research/SKILL.md:67` |
| Q4 | partly | Outline is concise ("c header files"). The plan is long, with code. No summary-first view. | `P/create-structure-outline/SKILL.md:159-160`; `P/create-plan/SKILL.md:30,36` |
| Q5 | partly | The plan is binding and has per-phase success criteria. No separate spec, and no feature-level definition of done. | `P/create-plan/SKILL.md:42-48`; `plan_template.md:73-88` |
| Q6 | no | The main agent writes the outline and plan. Subagents only research. | `P/create-plan/SKILL.md:12-31` |
| Q7 | no | No validator subagent. The open-questions gate checks completeness only. | `check-if-design-doc-has-open-questions.ts:24-49` |
| Q8 | partly | All design questions are in one document, which is good. No AI-decided list. PRD/TDD ask one question at a time. | `P/create-design-discussion/SKILL.md:78-83`; `P/create-prd/SKILL.md:14` |
| Q9 | no | A recommendation is shown but is never the default. There is no critical class. | `design_discussion_template.md:46`; `P/create-design-discussion/SKILL.md:80-83` |
| Q10 | partly | Files are local. In the product, they are cloud-synced and the tracker is the ticket source. | `artifact-sync-hook.ts:176-200`; `apps/riptide-claude-code-plugin/README.md:51` |
| Q11 | partly | Sizing exists only as product workflow types (oneshot … prd_tdd). No size classifier. | `workflow-routing-hook.ts:58-115` |
| Q12 | partly | The skills are Claude Code skills. The agents are TypeScript in the daemon. Gates, permalinks and auto-advance are product hooks. | `D/agents/claudecode/agents/*.ts`; `D/lib/artifact-sync-utils.ts:62-77` |

## 13. Tailoring cost

**Replace (largest first):**

1. **Rebuild the missing runtime.** This is the biggest cost.
   - Port the four research agents from TypeScript to `.claude/agents/*.md`. The daemon has a renderer that shows the shape (`D/agents/claudecode/agents/markdown.ts:10-23`).
   - Replace the system-prompt task folder, the open-questions LLM gate, permalinks, auto-advance, comment MCP tools and workflow routing. Each is product-only.
   - Resolve the `show-me` symlink.
   - Do not depend on HumanLayer Cloud, which is shutting down.
2. **Rework decisions for Q8/Q9.**
   - Replace "all questions open, only the user resolves" (`P/create-design-discussion/SKILL.md:78-83`) with ONE table that has three groups: decided by AI (with reason), recommended (default if the owner is silent), and critical (no recommendation).
   - Drop one-at-a-time interviewing from PRD/TDD, or do not use those stages.
3. **Add the spec and validator layer (Q4–Q7).**
   - Add a short summary-first view.
   - Add a binding spec with a feature-level definition of done, generated by subagents from the outline or plan.
   - Add a fresh-context validator subagent that checks correctness and "can an implementer act without guessing".
   - Add a sizing router (skip stages; research none/quick/deep) as a small entry skill.
4. **Tracker as mirror (Q10).** Replace the API-side ticket import with a connector that only mirrors local files.

**Keep as is:**

- Research blinded to the ticket (§4).
- Descriptive-only research with takeaway headers.
- Vertical-slice phases with Automated and Manual Verification sections, with automated checks preferred.
- The outline as "header file" before any detailed plan.
- Chronological `NN-` artifacts in one task folder.
- The document-precedence chain.
- The "verify the user's correction before accepting it" rule in iterate-* skills.
- The rule that the AI never resolves a question. It suits Q9's critical class.

Licence allows reuse (Apache-2.0, keep `NOTICE`). The ACE essay has no licence, so cite it but do not copy it.

## Sources (web)

- PR #1167, Cloud shutdown message: https://github.com/humanlayer/humanlayer/pull/1167
- Factory acquisition (secondary): https://runtimewire.com/article/factory-acquires-humanlayer-multiplayer-coding-agents
- QRSPI summary (secondary): https://alexlavaee.me/blog/from-rpi-to-qrspi/
- HumanLayer docs, workflow phases: https://docs.humanlayer.com/explanation/workflow-phases
- ACE essay: https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/ace-fca.md
