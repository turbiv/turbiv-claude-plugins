# Other agentic coding workflows: landscape survey

**As of:** 2026-11-18
**Scope:** Workflows and methodologies for Claude Code and similar harnesses, other than the two already under analysis: the Elephant-Goldfish Model (EGM) and obra/superpowers.

**How this was verified**
- Stars, last push, archived flag and renames come from the public GitHub repo metadata API, read on 2026-11-18.
- Current shape comes from READMEs and docs fetched on the same day.
- Anything that rests only on secondary sources, or that a current primary page did not confirm, is marked **[unverified]**.
- "Last push" is the date of the most recent commit on any branch. It shows activity, not release cadence.

**What I checked about EGM**

I read the locally installed `egm` agents. This is a snapshot, so please confirm it against your working copy.

The synthesizer deduplicates findings and groups them by severity (Blocker, Major, Nit). It has **no per-finding confidence score or drop threshold**.

Everything below that names a gap in EGM rests on this reading.

---

## 1. Landscape table

Phase key: **Req** = requirements and interview, **Des** = design, **Plan**, **Build**, **Ver** = verify and review, **Ship**, **Learn** = feeds lessons forward, **Mem** = cross-session state.

| Name | Link | One-line idea | Phases covered | Maturity (verified 2026-11-18) | Distinctive mechanism |
|---|---|---|---|---|---|
| GitHub Spec Kit | https://github.com/github/spec-kit | Spec-driven development toolkit: constitution, specify, plan, tasks, implement | Req, Des, Plan, Build, Ver | 150.4k stars. Last push 2026-11-17. Very active. | Project **constitution**. An implement/**converge** loop. Extensions, presets, workflows and hooks. A separate "assess" process can end in a go/kill verdict. |
| BMAD Method | https://github.com/bmad-code-org/BMAD-METHOD | Agile-style, role-based planning and delivery that scales with the size of the change | Req, Des, Plan, Build, Ver, Learn | 55.5k stars. Last push 2026-11-18. Stable v6.12.4 released 2026-10-14. v7 in alpha, targeted for mid-Nov 2026. | Scale-adaptive planning depth. Named persona agents. Epic and story files carry context to the build **[unverified on current official docs]**. Correct-course and retrospective steps **[secondary source]**. |
| Compound Engineering plugin | https://github.com/EveryInc/compound-engineering-plugin | Plan, work, review, **compound**: each unit of work should make the next one easier | Req, Plan, Build, Ver, Ship, **Learn** | 26.1k stars. Last push 2026-11-18. Runs on 14 hosts. | `/ce-compound` writes lessons to `docs/solutions/`, which later `/ce-plan` and `/ce-brainstorm` runs read. Multi-agent review against the plan. |
| HumanLayer RPI → CRISPY/QRSPI | https://github.com/humanlayer/humanlayer (`apps/riptide-rpi-claude-plugin`); https://github.com/humanlayer/advanced-context-engineering-for-coding-agents | Research, plan, implement with deliberate compaction. Since 2026 it has more stages and small, focused artefacts. | Req, Des, Plan, Build, Ver | Product monorepo: 12.9k stars, last push 2026-11-16. ACE essay repo: 2.8k stars, last push 2026-10-16. | Research questions are written first. Research is **blind to the ticket**. A short design-discussion doc and a structure outline (vertical slices) come before the full plan. |
| 12-factor agents | https://github.com/humanlayer/12-factor-agents | Principles for production LLM agents. Not a coding workflow as such. | (principles) | 27.3k stars. Last push 2025-09-21. **Static essay.** | Own your context window and control flow. Contact humans with tool calls. Small, focused agents. |
| Matt Pocock's skills | https://github.com/mattpocock/skills | Small, composable engineering skills: align before building, shared language, tight loops | Req, Des, Plan, Build, Ver, Learn | 327k stars. Last push 2026-11-17. In the official Claude plugin marketplace. | `grill-with-docs` updates `GLOSSARY.md` and ADRs while it interviews. `to-tickets` produces tracer-bullet slices. `wayfinder` handles multi-session work. `retro` improves the agent's environment. |
| Get Shit Done (GSD) → GSD Core | https://github.com/open-gsd/gsd-core (old: https://github.com/gsd-build/get-shit-done) | Meta-prompting plus spec-driven phases that run in fresh-context subagents | Req, Plan, Build, Ver, Ship, Mem | **Original archived on 2026-06-26 and moved** (64.1k stars stay on the archived repo). gsd-2 also archived. Successor gsd-core: 11.7k stars, last push 2026-11-18, v1.7.0. | Discuss, plan, execute, verify, ship per phase. Plans are checked to fit a fresh context. Executors run in parallel waves. `STATE.md` and `CONTEXT.md` persist state. |
| Agent OS | https://github.com/buildermethods/agent-os | Discover your codebase standards and inject them, then shape specs | Req, Plan (standards) | 5.6k stars. Last push 2026-10-07. Currently v3. | Standards are **discovered** from the existing code, then injected according to the task. Spec shaping runs inside plan mode. |
| Kiro (spec flow) | https://kiro.dev/docs/specs/ | IDE and CLI with requirements, design and tasks specs | Req, Des, Plan, Build, Ver | **Proprietary product.** The public repo `kirodotdev/Kiro` (4.5k stars, last push 2026-11-05) holds issues and docs, not product source, so its stars do not measure adoption. | Requirements in **EARS** notation. Bugfix specs record current, expected and *unchanged* behaviour. Analyze Requirements. Quick Spec has no gates. Tasks run in parallel waves by dependency. Property-based "Correctness" checks. |
| cc-sdd | https://github.com/gotalab/cc-sdd | Kiro-style spec-driven flow for Claude Code, Codex and others | Req, Des, Plan, Build, Ver | 3.8k stars. Last push 2026-10-22. v3.0. | `validate-gap` checks existing code before design. Each task gets a fresh TDD implementer plus an independent reviewer. |
| Claude Task Master | https://github.com/eyaltoledano/claude-task-master | Parse a PRD into a dependency-aware task list, served over MCP | Plan, Build (task tracking) | 28.4k stars. **Dormant: last push 2026-04-28**, 52 open PRs. README now points to a commercial product (Hamster). | PRD to tasks, `next`, `expand`, complexity analysis. MCP tool tiers (7/15/36 tools) to save context. |
| OpenSpec | https://github.com/Fission-AI/OpenSpec | Lightweight spec layer for brownfield code. Specs stay **alive** after ship. | Req, Des, Plan, Build, Ver | 75.1k stars. Last push 2026-11-18. 2.x (the `/opsx:*` commands were 1.x). | `openspec/specs/` is the current-behaviour source of truth. Each change folder holds **delta specs** (ADDED/MODIFIED/REMOVED), which are merged in on archive. |
| Tessl | https://tessl.io/ | Started as "spec-as-source". Now a skills registry plus skill evals and agent "loops". | (platform) | Closed commercial platform. No core public repo found. **Pivoted:** the current homepage no longer leads with spec-driven development. | Versioned skill registry with security scores. Before/after **evals of skill changes**. Benchmarking of models and harnesses. |
| ruflo (formerly claude-flow) | https://github.com/ruvnet/ruflo | Swarm "meta-harness" for Claude Code and Codex | Build (orchestration), Mem | **Renamed.** 82.0k stars. Last push 2026-11-18. | Queen-led swarms with consensus protocols. AgentDB vector memory. Very large tool surface (claims 400+ MCP tools). |
| oh-my-claudecode (OMC) | https://github.com/Yeachan-Heo/oh-my-claudecode | Teams-first multi-agent orchestration layer for Claude Code | Req, Plan, Build, Ver | 40.9k stars. Last push 2026-11-18. v4.x. | `/team` staged pipeline (plan, PRD, exec, verify, fix) on Claude Code's native agent teams. Ralph and verify loops. Deep-interview. Multi-model advisor. |
| oh-my-openagent (formerly oh-my-opencode) | https://github.com/code-yeongyu/oh-my-openagent | "ultrawork" orchestration, now on its own pi-fork harness | Plan, Build, Ver | **Renamed.** 71.0k stars. Last push 2026-11-18. Approx. v5. | `ulw` keyword. "mass ulw" splits a task into a graph of parallel agents. A cheap "Kibitzer" model nudges the main agent away from repeat mistakes. |
| Ralph Wiggum loop | https://ghuntley.com/ralph/ ; https://github.com/anthropics/claude-plugins-official/tree/main/plugins/ralph-loop | Feed the same prompt to the agent in a loop until done, with tests as backpressure | Build, Ver | Technique dates from 2025-07. **Reference repos are static** (snarktank/ralph 22.3k stars, last push 2026-02-02). The official `ralph-loop` plugin is maintained. ralph-orchestrator: 3.2k stars, last push 2026-11-13. | A Stop hook re-injects the prompt until a completion promise appears. One item per loop. `fix_plan.md`. Operator adds "signs" to tune it. |
| Cline Memory Bank | https://docs.cline.bot/features/memory-bank | Structured markdown memory files read at the start of every session | Mem | Still in the current Cline docs. It is a **custom-instruction pattern, not a built-in feature**. | `projectbrief`, `productContext`, `activeContext`, `systemPatterns`, `techContext` and `progress` files form a hierarchy. |
| Anthropic first-party guidance | https://code.claude.com/docs/en/best-practices ; https://github.com/anthropics/claude-plugins-official ; engineering posts (section 2) | Official practice: tell Claude what it can't see, give it a check, enforce hard rules in the harness | All | Docs are current. The official plugin repo has 47.6k stars, last push 2026-11-18. **The old "explore, plan, code, commit" engineering post now 308-redirects to the docs page, which no longer frames that sequence.** | Deterministic (hooks, deny rules) versus non-deterministic (CLAUDE.md, skills) instructions. Stop hook and `/goal`. Fresh-context `/code-review`. `feature-dev` 7-phase plugin. Long-running harness pattern. |
| Beads | https://github.com/gastownhall/beads | Graph issue tracker that serves as agent memory | Plan, Mem | 28.8k stars. Last push 2026-11-18. Moved from its creator's personal account. | `bd ready` lists unblocked work. Atomic claim. Dependency types. `bd prime` and `bd remember` inject memory. Old closed items are compacted ("memory decay"). |
| Gas Town | https://github.com/gastownhall/gastown | Workspace manager for 20-30 parallel agents | Build, Ver, Ship | 18.8k stars. Last push 2026-11-14. Heavy prerequisites. | Mayor, polecat, witness and refinery roles. Bisecting merge queue. Work state lives in git-worktree "hooks". Built on Beads. |
| addyosmani/agent-skills | https://github.com/addyosmani/agent-skills | Senior-engineer lifecycle skills: define, plan, build, verify, review, ship | Req, Plan, Build, Ver, Ship | 118.8k stars. Last push 2026-11-14. | Skills with exit criteria and **anti-rationalization tables**. `doubt-driven` and `source-driven` development. 4 reviewer personas. |
| CCPM | https://github.com/automazeio/ccpm | PRD to epic to GitHub Issues to parallel agents in worktrees | Req, Plan, Build, Mem | 8.5k stars. Last push 2026-11-04. Now packaged as an Agent Skill. | GitHub Issues are the source of truth. Tasks carry parallel/conflict metadata. About 15 deterministic bash scripts for status. |
| Conductor | https://github.com/gemini-cli-extensions/conductor | "Context-driven development": persistent product and tech context, plus tracks | Req, Plan, Build, Ver, Mem | 3.8k stars. Last push 2026-09-01. Supports Antigravity and Claude Code. | `product.md`, `tech-stack.md` and `workflow.md`. Per-track `spec.md`, `plan.md` and metadata. **Git-aware revert** by track, phase or task. |
| Harness engineering (concept) | https://martinfowler.com/articles/harness-engineering.html | Frame everything around the model as guides (feedforward) and sensors (feedback) | (framework) | Article dated 2026-04-02. The term is new and its origin is disputed. | Computational versus inferential controls. A steering loop that fixes the harness whenever an issue recurs. |
| SuperClaude Framework | https://github.com/SuperClaude-Org/SuperClaude_Framework | Commands, personas and methodologies config for Claude Code | **[unverified]** | 23.9k stars. Last push 2026-09-27. | **[unverified]**: only the metadata was checked. |
| wshobson/agents | https://github.com/wshobson/agents | Large multi-harness catalogue of plugins, agents and skills | **[unverified]** | 42.6k stars. Last push 2026-11-16. | A catalogue, not a methodology. **[unverified]**: only the metadata was checked. |
| PRP (Product Requirement Prompts) | https://github.com/Wirasm/prp (renamed from PRPs-agentic-eng) | Prompts and workflows for "agentic engineering" | **[unverified]** | 2.3k stars. Last push 2026-10-02. | **[unverified]** |
| context-engineering-intro | https://github.com/coleam00/context-engineering-intro | Introductory INITIAL.md → PRP template for context engineering | **[unverified]** | 13.9k stars. **Last push 2026-03-16 (stale).** | **[unverified]** |

Star counts in the hundreds of thousands for markdown-only skill repos (mattpocock/skills, addyosmani/agent-skills, superpowers) are real per the API. Treat them as a signal of attention, not quality.

---

## 2. Per-workflow notes

### GitHub Spec Kit
- **Mechanism**
  - Core loop: `/speckit-constitution`, then `-specify`, `-plan`, `-tasks`, `-implement` and `-converge`.
  - Implement and converge repeat until converge reports *Converged*.
  - Spec Kit now describes itself as a toolkit of *independent processes*, not mandatory phases. Bundled extensions add a bug process (assess, fix, test, with verified/partial/failed verdicts) and an idea-assessment process (verdict go, needs-clarification or kill).
  - Extensions add gates and hooks. Presets swap templates and terminology. Workflows automate command chains.
- **Best at**: Teams that want every feature to leave the same, Git-resident artefacts that people outside the agent can read.
- **Criticisms**
  - Verbose, repetitive markdown that is slower to review than the code. One test found agents ignoring its research notes and duplicating existing classes ([Böckeler, 2025-10-15](https://www.martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)).
  - A branch per spec means specs live only for one change ("spec-first", not "spec-anchored").
  - A 2026-10 hands-on comparison found it the most expensive run. It enforces order but not approval ([comparison](https://felipefontoura.com/articles/spec-driven-development-tools-compared/)).
  - Whether `clarify`, `analyze` and `checklist` are still separate commands is **[unverified]**: the current README only links to a walkthrough.
- **Steal**
  1. A **constitution**: project-level non-negotiables that the plan is checked against.
  2. **Converge**: an explicit "keep implementing until the spec and code agree" loop with a named terminal verdict.
  3. **Kill as a legitimate outcome** of an assessment process. Stopping with a documented reason counts as success.
- Source: https://github.com/github/spec-kit

### BMAD Method
- **Mechanism (v6, stable, per secondary sources)**
  - Four phases: Analysis (optional), Planning (required, scale-adaptive: PRD or tech-spec), Solutioning (architecture, depending on track) and Implementation (story-centric). This comes from a search-engine summary of the official workflow map and community v6 ports. The map page itself returned 404 when fetched today **[unverified]**.
  - The same summary lists create-epics-and-stories, sprint-planning, build or build-auto, code-review, **correct-course** and **retrospective**. The `build` naming may already reflect v7 **[unverified]**.
  - Story files carry just-in-time context to the build **[unverified]** against current official docs.
- **Mechanism (v7)**: The README and docs now describe a Clarify, Plan, Build-and-verify, Learn-and-adjust loop. Work enters at the stage that fits its size.
  - Named personas on the current docs: Sofia (PO) and John (PM). The full v6 roster (Analyst, Architect, SM, Dev, UX) is **[unverified]** on current official pages.
  - Add-on modules include BMad Loop (unattended epic builds plus retros) and Test Architect.
  - Whether v7 has shipped today is **[unverified]**: the latest GitHub release is v6.12.4 (2026-10-14).
- **Best at**: Larger multi-role work, where product, architecture and delivery thinking should be split across perspectives.
- **Criticisms**
  - The most role-heavy option.
  - In one probe, a single sentence of pre-approval skipped both approval stops, because the gates live in the prompt ([comparison](https://felipefontoura.com/articles/spec-driven-development-tools-compared/)).
  - Its own community reported v6 architecture docs as weaker than v4's ([discussion #979](https://github.com/bmad-code-org/BMAD-METHOD/discussions/979)).
  - It is in the middle of a v6 to v7 reshape.
- **Steal**
  1. **Scale-adaptive routing**: decide planning depth from the change size up front.
  2. **Correct-course** as a named mid-flight re-plan step.
  3. A **retrospective** as a formal phase output.
- Source: https://github.com/bmad-code-org/BMAD-METHOD ; https://docs.bmad-method.org/

### Compound Engineering (plugin)
- **Mechanism**
  - Brainstorm, plan, work, simplify, review, **compound**.
  - `/ce-compound` writes the lesson from a finished change into `docs/solutions/`. `/ce-brainstorm` and `/ce-plan` read that folder as grounding.
  - Experimental "Compound Packs" are folders of prescriptive rules: planning draws on them and review enforces them.
  - `/ce-code-review` runs a multi-agent review against the plan. The guide describes 14+ specialist reviewers with findings ranked P1 to P3.
  - `lfg` runs the whole pipeline hands-off.
  - 38 skills across 14 harnesses.
- **Best at**: Making a team's codebase knowledge **accumulate** instead of evaporating between sessions.
- **Criticisms**
  - Productivity claims are self-reported by the team that sells the tools ([guide](https://every.to/guides/compound-engineering)).
  - *(My assessment)* A fan-out of 14+ reviewers costs many tokens.
  - The guide itself says "permission-skipping" belongs only in isolated environments.
- **Steal**
  1. A **learnings store written at the end of every unit and read automatically at the start of planning**.
  2. "Packs": rules that planning *and* review both consume, so the same guide is used in both directions.
  3. Time budget heuristic: about 80% planning plus review, about 20% execution.
- Source: https://github.com/EveryInc/compound-engineering-plugin ; https://every.to/guides/compound-engineering

### HumanLayer: Advanced Context Engineering, RPI, and its 2026 successor (CRISPY/QRSPI)
- **Mechanism (ACE/RPI, 2025)**
  - Frequent intentional compaction into markdown artefacts. Keep context utilisation around 40-60%.
  - Research, then plan, then implement, with subagents used for search.
  - Humans review research and plans rather than every line.
  - Source: [ace-fca.md](https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/ace-fca.md).
- **Mechanism (2026)**: The current `riptide-rpi` plugin in the product monorepo ships skills that confirm a longer pipeline:
  - `create-research-questions` → `create-research` → `create-design-discussion` → `create-structure-outline` → `create-plan` → `implement-plan`.
  - Each step has an `iterate-*` companion, plus `review-artifact-comments`.
  - The `create-research` skill explicitly forbids reading the ticket: research must describe the codebase as it is, not what the ticket wants. This is the "objective research" change ([skills dir](https://github.com/humanlayer/humanlayer/tree/main/apps/riptide-rpi-claude-plugin/skills)).
- **Lessons from a 2026 talk (secondary summary, [ZenML](https://www.zenml.io/llmops-database/evolving-ai-coding-agent-workflows-from-research-plan-implement-to-crispy))** **[unverified beyond that summary]**
  - About 1,000-line plans were as costly to review as the code, and implementations diverged from them.
  - Monolithic prompts with 85+ instructions were followed unreliably. Stages are now kept under about 40 instructions each, with control flow in code.
  - A roughly 200-line design discussion gives the human leverage before any code exists.
  - Vertical-slice outlines.
  - The team **reversed** "plans are enough": engineers must read the code again.
  - The naming varies between CRISPY and QRSPI depending on the source.
- **Best at**: Hard problems in large brownfield codebases, with an engaged human.
- **Criticisms**
  - The authors' own failures: a 7-hour parquet-java attempt failed, and research needed steering.
  - Evidence is anecdotal.
  - QRSPI is not formally open-sourced as such. A third-party npm package calls itself a "reconstruction" **[unverified]**.
- **Steal**
  1. **Blind the researcher to the ticket**: generate research questions first, then research without seeing the intent.
  2. A **design-discussion doc** (current state, desired state, patterns, decisions, open questions) as the primary human-review artefact, *before* a long plan.
  3. An **instruction budget per stage prompt**, with control flow moved into code or harness.
- Sources: links above; https://github.com/humanlayer/humanlayer

### 12-factor agents
- **Mechanism**: Twelve principles for production agents, plus a "factor 13: pre-fetch context". Highlights: own your prompts, own your context window, own your control flow, contact humans with tool calls, small focused agents, and the agent as a stateless reducer.
- **Best at**: Vocabulary for *why* a pipeline should keep control flow in code.
- **Criticisms**: Aimed at building agent products, not at coding workflows. Last pushed 2025-09.
- **Steal**: "Contact humans with tool calls", meaning human approval as a first-class structured step. "Own your control flow".
- Source: https://github.com/humanlayer/12-factor-agents

### Matt Pocock's skills
- **Mechanism**
  - About 25 small skills, split into user-invoked and model-invoked.
  - Alignment: `grill-me`, `grill-with-docs` (updates `GLOSSARY.md` and ADRs during the interview), and `domain-modeling`.
  - Specs and tickets: `to-spec`, and `to-tickets` (tracer-bullet tickets with blocking links).
  - Implementation: `implement` (TDD at agreed seams, then code review) and `implement-spec` (parallel subagents across ready tickets).
  - Multi-session work: `wayfinder` (a map of decision tickets for work too big for one session).
  - Feedback: `retro` (after a session, proposes fixes to the agent environment) and `improve-codebase-architecture`.
  - The stated philosophy is explicitly *not* to own the process. These are editable building blocks.
- **Best at**: Shared language and design hygiene. Lightweight composition with other frameworks.
- **Criticisms**
  - *(My assessment)* No enforcement layer: everything is prompt-level.
  - `grill-me` overlaps heavily with superpowers' brainstorming.
  - Popularity outruns published evidence: I found no evals in the repo **[unverified]**.
- **Steal**
  1. A **glossary plus ADRs updated as a side effect of grilling**, so decisions become durable project memory.
  2. **Tracer-bullet tickets**: thin vertical slices with explicit blocking links.
  3. A **retro skill that edits the harness**, not the code.
- Source: https://github.com/mattpocock/skills

### GSD → GSD Core
- **Mechanism**
  - Milestone, then phases. Each phase runs discuss, plan, execute, verify, ship.
  - Heavy work runs in fresh-context subagents, keeping the orchestrator lean.
  - Plans are checked to fit a fresh context window.
  - Executors run in parallel waves.
  - `STATE.md` and `CONTEXT.md` carry state across sessions.
  - Supports about 10 runtimes.
- **Status**
  - The original `gsd-build/get-shit-done` README says GSD has moved. The repo was archived on 2026-06-26.
  - `gsd-build/gsd-2` is also archived. Active development is at `open-gsd/gsd-core`.
  - The reason for the move is **[unverified]**: the README gives none.
- **Best at**: Long solo builds where context rot is the main failure mode.
- **Criticisms**
  - The ecosystem churned: a fork, a rename, a successor and community forks. Stars mostly sit on the archived repo.
  - The process overhead is high for small changes, per community comparisons **[unverified]**.
- **Steal**
  1. **A plan-fits-in-a-fresh-context check** as a planning gate.
  2. **Wave execution** from a dependency graph.
  3. A single `STATE.md` resume point.
- Source: https://github.com/open-gsd/gsd-core ; https://github.com/gsd-build/get-shit-done

### Agent OS (v3)
- **Mechanism**
  - Discover standards (extract the conventions the code already follows), index them, then deploy or inject the relevant ones by task.
  - Product planning, then spec shaping. The shaping questions run inside Claude Code's plan mode.
  - Whether v3 dropped the earlier full create-tasks/implement pipeline is **[unverified]**: the current pages describe only the standards and shaping stages.
- **Best at**: Brownfield repos whose conventions are unwritten.
- **Criticisms**: Small adoption (5.6k stars). Thin public docs on the current command set.
- **Steal**: **Standards discovery from code**: mine conventions into short, indexed standards files and inject only the relevant ones per task. This is the feedforward counterpart to EGM's reviewers.
- Source: https://github.com/buildermethods/agent-os ; https://buildermethods.com/agent-os

### Kiro (spec flow), and cc-sdd as its Claude Code port
- **Mechanism (Kiro)**
  - `requirements.md` in EARS form ("WHEN … THE SYSTEM SHALL …"), then `design.md`, then `tasks.md`.
  - Requirements-first or design-first variants.
  - **Bugfix specs** capture current, expected and **unchanged** behaviour.
  - *Analyze Requirements* checks for gaps and ambiguity before design.
  - *Quick Spec* skips the gates.
  - Tasks run in dependency **waves**, parallel within a wave.
  - A "Correctness" feature uses property-based testing (IDE only; details **[unverified]**).
- **Mechanism (cc-sdd)**: Kiro-style commands for Claude Code and Codex. `kiro-validate-gap` checks the existing code before design. `kiro-impl` gives each task a fresh TDD implementer plus an independent reviewer.
- **Best at**: Precise, testable requirements. Bugfixes that must not regress neighbouring behaviour.
- **Criticisms**
  - Kiro is a proprietary IDE/CLI. OpenSpec's README criticises its lock-in.
  - Böckeler saw a small bug blown up into 4 user stories with 16 acceptance criteria.
  - It is mostly spec-first: specs are not maintained after the change.
- **Steal**
  1. **EARS-style requirement lines** that map one-to-one to tests.
  2. **"Unchanged behaviour" as a required bugfix-spec section.**
  3. **Requirement properties checked by property-based tests**, as a behaviour sensor.
- Sources: https://kiro.dev/docs/specs/ ; https://kiro.dev/docs/specs/feature-specs/ ; https://github.com/gotalab/cc-sdd

### Claude Task Master
- **Mechanism**: Parse a PRD into dependency-linked tasks. `next`, `expand`, complexity analysis and research. Runs as an MCP server with selectable 7/15/36-tool tiers.
- **Status**: **Dormant**. The last push was 2026-04-28 and 52 PRs are open. The README now points to a commercial product. The license is MIT with Commons Clause.
- **Best at**: Turning a PRD into an ordered, dependency-aware task queue for editors that have no planning of their own.
- **Criticisms**: Dormant upstream. The licence restricts hosted use. I found no recent methodological criticism.
- **Steal**: **Tiered tool exposure** to limit context cost from MCP tools.
- Source: https://github.com/eyaltoledano/claude-task-master

### OpenSpec
- **Mechanism**
  - `openspec/specs/` holds the *current-behaviour* specs per domain.
  - Each change is a folder under `openspec/changes/` with `proposal.md`, delta `specs/`, `design.md` and `tasks.md`.
  - Deltas use ADDED, MODIFIED and REMOVED Requirements sections, with WHEN/THEN scenarios.
  - **Archive merges the deltas into the main specs** and moves the change to a dated archive, so specs track the system over time.
  - The default commands are explore, propose, apply-change and archive-change. There is an expanded profile, plus beta "stores" for cross-repo planning.
  - Claims support for 30+ assistants.
- **Best at**: Brownfield code with many small, frequent changes. Long-lived requirement history.
- **Criticisms**: It deliberately has **no phase gates**. In one test it guessed a key requirement and needed a correction round ([comparison](https://felipefontoura.com/articles/spec-driven-development-tools-compared/)).
- **Steal**
  1. **Delta specs merged on archive**, so a per-ticket spec updates a living spec instead of dying with the ticket.
  2. **Parallel change folders** that do not collide until archive.
- Sources: https://github.com/Fission-AI/OpenSpec ; https://github.com/Fission-AI/OpenSpec/blob/main/docs/concepts.md

### Tessl
- **Mechanism (today)**: A registry of versioned skills with security scores. **Before/after evals of skill changes** and activation telemetry. Scheduled "loops" for review, security and test-fix. Model and harness benchmarking.
- **Status**: **Pivoted** away from its 2025 spec-as-source framework. A third-party review dates the repositioning to skills to 2026-01. It says the framework stayed in closed beta, JS-only and non-deterministic **[unverified; single reviewer]**. The `tessl-labs/spec-kit` tile was archived, superseded by an "intent-integrity-kit" **[unverified]**.
- **Best at**: Publishing, versioning and evaluating skills across an organisation.
- **Criticisms**: Böckeler found regenerated code varied between runs from the same spec. It is a closed commercial platform, and its spec-as-source vision is unproven.
- **Steal**: Treat skills as **versioned packages with evals gating changes**. Tessl is a reference for how to publish and score them.
- Sources: https://tessl.io/ ; https://codemyspec.com/blog/tessl-review

### ruflo (formerly claude-flow)
- **Mechanism**: `npx ruflo init` installs agents, hooks, memory and an MCP server into a project. Swarm topologies (hierarchical, mesh, adaptive) with consensus. AgentDB HNSW vector memory. A SPARC plugin.
- **Best at**: Experimenting with swarm topologies and persistent vector memory.
- **Criticisms**
  - The README is marketing-heavy and its counts are internally inconsistent (98 vs 100+ agents).
  - Benchmark claims point to an external gist **[unverified]**.
  - Federation features appear to be design-stage.
  - The mechanism-to-value ratio is hard to assess.
- **Steal**: Little for this developer. At most, the idea of *hooks that write to a shared memory store automatically*.
- Source: https://github.com/ruvnet/ruflo

### oh-my-claudecode (OMC)
- **Mechanism**
  - `/team`: plan, PRD, execute, verify, fix-loop, running on Claude Code's experimental native agent teams.
  - Autopilot, execute and verify loops until build, lint, typecheck and tests pass.
  - Ralph persistence mode. "Ralplan" consensus planning. Deep-interview.
  - A tri-model advisor that asks Codex and other CLIs. Autoresearch with per-iteration eval JSON.
  - Claims 19 agents (not listed).
- **Best at**: Squeezing autonomy out of Claude Code's native teams.
- **Criticisms**
  - *(My assessment)* Token-heavy.
  - Relies on an experimental flag.
  - Its own README warns that `/goal` evaluation is defined by Claude Code, so evidence must be shown in the conversation.
- **Steal**: **Ralplan**, a planner and critic iterating to consensus. It is close to EGM's swarm but applied to plans.
- Source: https://github.com/Yeachan-Heo/oh-my-claudecode

### oh-my-openagent (formerly oh-my-opencode)
- **Mechanism**
  - Now runs on "senpi", a fork of the pi agent, with a migration path from its OpenCode edition.
  - The `ulw` keyword gives read-first, plan, verify-each-step, check-on-real-surface behaviour.
  - "mass ulw" splits work into a graph of parallel, model-matched agents.
  - A cheap "Kibitzer" model reads past work and nudges the main agent. Memory is markdown in git.
  - The named agent roster widely reported in 2025-26 (Sisyphus, Oracle and others) is **not on the current README** **[unverified]**.
- **Best at**: Hands-off, multi-model execution of large tasks, for people willing to adopt its harness.
- **Criticisms**
  - Claude subscription OAuth in third-party harnesses has been blocked since January 2026 under the provider's terms **[unverified: secondary reports only, and their dates differ]**.
  - A search summary says an older README advised against using a Claude subscription **[unverified]**. The current README lists a Claude `/login`.
  - The harness has moved twice.
- **Steal**: **A small "kibitzer" model that watches for repeat mistakes**. This is a cheap inferential sensor.
- Source: https://github.com/code-yeongyu/oh-my-openagent

### Ralph Wiggum loop
- **Mechanism**
  - Originally a bash loop that pipes `PROMPT.md` into the agent, forever.
  - One item per iteration, chosen from `fix_plan.md`, with specs reloaded every loop.
  - Tests, builds and types act as backpressure.
  - When the loop misbehaves, the operator adds "signs" to the prompt ([ghuntley.com/ralph](https://ghuntley.com/ralph/), 2025-07-14).
  - The official `ralph-loop` plugin does this in-session: a Stop hook blocks exit until an exact completion promise appears, with `--max-iterations` as the safety cap.
- **Best at**: Greenfield or mechanically verifiable work left unattended.
- **Criticisms**
  - Results are anecdotal, such as "$50k contract for $297".
  - The author himself says it suits greenfield, not existing codebases.
  - Unbounded cost without a cap.
  - Exact-string completion cannot express "blocked".
- **Steal**
  1. **Fix failures by editing the prompt and harness** ("signs"), not by retrying.
  2. **Only one build/test validator at a time**, even when search fans out.
- Sources: links above; https://github.com/anthropics/claude-plugins-official/tree/main/plugins/ralph-loop

### Cline Memory Bank
- **Mechanism**: A custom-instruction pattern. A hierarchy of markdown files (`projectbrief` as the root, then product, tech and system patterns, then `activeContext` and `progress`) is read at every session start and updated at checkpoints. The docs pair it with Auto Compact, `/newtask` and `/smol`.
- **Best at**: Giving a harness with no memory a simple, readable continuity layer.
- **Criticisms**: The docs warn that every file costs context on every session and should stay concise. *(My assessment)* Without curation the files drift away from the code.
- **Steal**: The **"activeContext versus progress" split**: a volatile current-focus file separated from a stable summary.
- Source: https://docs.cline.bot/features/memory-bank

### Anthropic first-party guidance

**Best practices (current docs)**
- Frames everything as **deterministic versus non-deterministic** instructions:
  - Non-deterministic: CLAUDE.md, skills and prompts. The model decides.
  - Deterministic: hooks, deny rules and managed settings. The harness enforces.
  - If a CLAUDE.md line keeps being missed despite emphasis, it belongs in a hook.
- "Give Claude a check to run". Strictness ranges from the prompt, to `/goal` (a separate model checks a stated condition after each turn), to a **Stop hook** that blocks the end of a turn with exit code 2, to a fresh-context `/code-review`.
- Ask for *evidence* (the command run and its output).
- An "interview me, then write SPEC.md" pattern, then **build from a fresh session**.
- Review against the spec with "skip style". The docs warn that a reviewer told to find problems will always find something, and that fixing everything adds needless abstraction.
- A five-question checklist before going unattended: done-definition, self-check, blast radius, stop condition, sign-off.
- A **"what you can stop doing"** table:
  - Aggressive context management and subagents-to-save-context are now listed as outdated, because of 1M windows plus auto-compaction.
  - "Delegate for a better answer" is a myth. A *fresh reviewer* does help.
- The old `anthropic.com/engineering/claude-code-best-practices` URL (explore, plan, code, commit) now 308-redirects here, and the page no longer presents that named sequence. Plan mode is still documented, as a permission mode and as the "Plan before editing" recipe in [common workflows](https://code.claude.com/docs/en/common-workflows).

**Official plugins** (https://github.com/anthropics/claude-plugins-official)
- `feature-dev`: 7 phases (discovery, exploration with 2-3 parallel `code-explorer` agents, clarifying questions, architecture with 2-3 parallel `code-architect` agents, implementation, review with 3 parallel `code-reviewer` agents, summary). It has 5 explicit approval points.
- `code-review`: 4 parallel agents (2 for CLAUDE.md compliance, 1 for bugs, 1 for git history). Each issue gets a **0-100 confidence score** and anything **below 80 is dropped**. An explicit false-positive exclusion list.
- Others: `ralph-loop`, `pr-review-toolkit`, `code-simplifier`, `hookify`, `claude-md-management` and `session-report`.

**Engineering posts**
- [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (2025-09-29): smallest high-signal token set, context rot, just-in-time retrieval, compaction, structured notes, and subagents returning 1-2k-token summaries.
- [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) (2025-06-13): orchestrator plus workers beat a single agent by 90.2% on research, at about 15x chat tokens.
  - Token spend explained about 80% of the variance in performance.
  - **Most coding tasks are a poor fit**: they need shared context and have too few parallel parts.
  - Evals: start with about 20 real cases, use an LLM judge with a rubric, plus humans.
- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) (2025-11-26):
  - An **initializer agent** creates `init.sh`, a progress log and a **JSON feature list, all initially failing**. JSON was chosen because models tamper with it less than with markdown.
  - Each later **coding agent** does one feature, tests end-to-end in a browser, commits and updates progress.

**Criticisms**: The docs push built-ins (`/goal`, `/code-review`, `/verify`, `/batch`) that are specific to Claude Code. The multi-agent eval numbers are internal.

**Steal**
1. **Move gates and "done" checks into hooks and `/goal`**, out of the prompt.
2. **A confidence threshold plus false-positive exclusion list** for any reviewer swarm, EGM included.
3. **A feature-list JSON that the agent may only flip pass/fail on**, plus `init.sh` and a progress log for unattended builds.

### Beads
- **Mechanism**
  - A Go CLI. Issues form a dependency graph stored in Dolt and synced through a git remote.
  - `bd ready` lists unblocked work. `--claim` claims an item atomically.
  - `bd prime` and `bd remember` inject workflow context and project facts.
  - Old closed items are summarised ("memory decay").
  - Set-up helpers exist for Claude Code, Codex, Cursor and others.
- **Best at**: Agent-discovered sub-work that must survive across sessions and agents, below the granularity of a Jira ticket.
- **Criticisms**: It is another source of truth next to Jira or GitHub Issues. It moved from git/JSONL to Dolt over time (JSONL is now export-only). A "discovered-from" link type is **[unverified]** on the current README.
- **Steal**: **A ready queue computed from dependencies**. The agent asks "what is unblocked?" instead of re-reading a plan.
- Source: https://github.com/gastownhall/beads

### Gas Town
- **Mechanism**
  - A Mayor agent turns goals into "convoys" of beads.
  - Polecat workers have persistent identity but ephemeral sessions.
  - A Witness detects stuck agents. A Deacon patrols across rigs.
  - A Refinery runs a bisecting merge queue with verification gates. Polecats never push to main.
- **Best at**: Running many agents at once on a backlog while keeping main green.
- **Criticisms**: Heavy prerequisites (Go, Dolt-backed Beads, tmux). 395 open issues. The claimed 20-30-agent scale is self-reported.
- **Steal**: A **merge queue with verification gates** as the only path to main for agent work.
- Source: https://github.com/gastownhall/gastown

### addyosmani/agent-skills
- **Mechanism**
  - 25 skills across define, plan, build, verify, review and ship (e.g. `interview-me`, `doubt-driven-development`, `source-driven-development`, `constraint-driven-development`, `deprecation-and-migration`).
  - Every skill has steps, checkpoints and exit criteria, plus **anti-rationalization tables**.
  - 9 commands. `/build auto` needs one approval, then tests and commits each task.
  - 4 reviewer personas.
- **Best at**: A broad, phase-indexed skill pack that covers ship-side concerns as well (CI/CD, deprecation, observability, launch).
- **Criticisms**: *(My assessment)* Overlaps superpowers almost completely in spirit. I found no published criticism.
- **Steal**: **Anti-rationalization tables**: list the excuses the agent will use to skip a step, next to the rebuttal. Also "source-driven development", which grounds claims in primary docs.
- Source: https://github.com/addyosmani/agent-skills

### CCPM
- **Mechanism**: PRD, then epic, then task files with acceptance criteria and parallel/conflict metadata. These sync to GitHub epic and sub-issues, with one worktree per epic. Agents split an issue into parallel streams. About 15 deterministic bash scripts produce status and standup reports. Now packaged as an Agent Skill.
- **Best at**: Teams that already live in GitHub Issues and want parallel agents per epic.
- **Criticisms**: I found no published criticism. *(My assessment)* It is tied to GitHub Issues as the source of truth.
- **Steal**: **Deterministic scripts for status and reporting** instead of asking the model to summarise state.
- Source: https://github.com/automazeio/ccpm

### Conductor
- **Mechanism**
  - A one-time setup writes `product.md`, `product-guidelines.md`, `tech-stack.md`, `workflow.md` and style guides.
  - Each feature or bug is a "track" with `spec.md`, `plan.md` and metadata.
  - `implement` checks off tasks. `review` audits completed work against the guidelines and plan, and may append a "Review Fixes" phase.
  - **`revert` rolls back a track, phase or task using git history.**
- **Best at**: Small teams that want product, tech and workflow context written down once and reused by every feature.
- **Criticisms**: I found no published criticism. Its supported-host list is narrow (Antigravity and Claude Code), and it had no push in the 2.5 months before this survey.
- **Steal**: **Plan-aware revert**: undo at the granularity of a plan phase or task.
- Source: https://github.com/gemini-cli-extensions/conductor

### Harness engineering (concept)
- **Mechanism**
  - Everything except the model is the harness.
  - Guides act before the agent (feedforward). Sensors act after (feedback).
  - Each control is either computational (tests, linters) or inferential (LLM review).
  - Categories: maintainability, architecture fitness and behaviour. Behaviour is the hardest.
  - The human's job is a steering loop: when an issue recurs, improve the harness.
  - Keep quality left.
- **Why it matters**: It gives a neutral vocabulary to place EGM and superpowers on one map.
  - EGM is an inferential sensor on design docs.
  - superpowers is mostly inferential guides, plus TDD and verification-before-completion, which drive computational sensors.
  - The category neither of them targets directly is **behaviour sensors derived from requirements**, such as property-based tests from spec properties.
- Source: https://martinfowler.com/articles/harness-engineering.html (2026-04-02)

---

## 3. Cross-cutting patterns

### Convergence (what almost everyone now does)
1. **Written intent before code.** Spec, plan or tasks files on disk are universal: Spec Kit, OpenSpec, Kiro, cc-sdd, BMAD, GSD, Conductor, CCPM, Compound Engineering, HumanLayer, and even Anthropic's "interview me, then SPEC.md".
2. **Interview first.** Anthropic's "interview me", Pocock's `grill-me`, addyosmani's `interview-me`, OMC's deep-interview, GSD's discuss step, CE's brainstorm and OpenSpec's explore all start with a Socratic interview.
3. **Fresh-context subagents for research and especially for review.** feature-dev explorers and reviewers, the `code-review` plugin, CE's reviewers, cc-sdd's per-task implementer plus reviewer, and GSD's executors. Anthropic's docs now justify subagents mainly as *independent review* and parallelism, not as context saving.
4. **File-based persistent state.** Memory Bank, `STATE.md`, the progress log plus feature JSON, Beads, `docs/solutions/`, `openspec/specs/`, Conductor tracks and `GLOSSARY.md` with ADRs.
5. **Verification as backpressure.** Ralph's tests and builds, Anthropic's "give it a check" and Stop hook, OMC's verify loops, Spec Kit's converge, Kiro's property-based tests and the feature-list JSON.
6. **Learning loops.** CE's compound step, Pocock's `retro`, BMAD's retrospective and BMad Loop retros, Ralph's "signs", harness engineering's steering loop and OmO's Kibitzer.
7. **Dependency-wave parallel execution.** Kiro, GSD, Pocock's `implement-spec`, CCPM and Gas Town.
8. **Packaging as Agent Skills or plugins that run on many harnesses.** CE runs on 14 hosts, OpenSpec on 30+, cc-sdd on 8, CCPM follows the agentskills.io standard, and Pocock's skills target 4 or more harnesses.
9. **Right-sizing.** BMAD's scale-adaptive tracks, Spec Kit's "independent entry points", Kiro's Quick Spec and OpenSpec's profiles. This is a reaction to the "4 user stories for one bug" critique.
10. **Reviewer-noise control.** The `code-review` plugin's confidence of 80 or more, feature-dev reporting only high-confidence issues, and Anthropic's "skip style" warning.

### Real disagreements
1. **Is context still the binding constraint?**
   - *Yes:* HumanLayer keeps utilisation under about 40-60% and prefers its own markdown artefacts over auto-compaction. GSD exists to fight context rot.
   - *No:* Anthropic's current docs list "the context window is your main constraint" and "subagents to protect context" as advice you can **stop** following (1M windows plus auto-compaction). Both camps still agree that a *fresh* context helps review.
2. **What should the human review: the plan or the code?**
   - ACE (2025) said review research and plans, not code.
   - HumanLayer's 2026 talk reversed this: read the code, review a short design doc, spot-check the plan.
   - Böckeler would rather review code than verbose spec markdown.
   - CE puts about 80% of effort into planning plus review.
3. **Where gates live.**
   - Most frameworks put approval gates in prompt text. In a hands-on comparison, BMAD's gates were skipped by a single pre-approval sentence, and Superpowers' brainstorming never ran.
   - Anthropic says anything that must always happen should be a hook or deny rule. HumanLayer moved control flow into code.
   - OpenSpec has *no* gates by design, and Kiro's Quick Spec removes them.
4. **Swarms versus a single thread.**
   - *Swarms:* ruflo, OMC's `/team`, oh-my-openagent's "mass ulw" and Gas Town (20-30 agents).
   - *Single thread:* Anthropic's multi-agent post says most coding parallelises poorly and costs about 15x tokens. Its docs say delegating the same task does not improve the answer. Ralph keeps one item per loop and one validator.
5. **How long a spec lives.**
   - *Spec-first* (one change, then discarded): Spec Kit's branch per spec, and Kiro.
   - *Spec-anchored* (kept alive): OpenSpec's delta merge.
   - *Spec-as-source*: Tessl's original bet, which stalled and pivoted.
6. **Own the process, or offer building blocks.** BMAD, GSD, Spec Kit and ruflo own the process. Pocock's skills say "keep control" and offer editable blocks. Anthropic says that most of the time Claude should decide.
7. **Personas versus functions.** BMAD uses named role personas (PM, PO). HumanLayer uses function-scoped agents (locator, analyzer, pattern-finder). EGM uses review-lens personas. There is no evidence either way on which works better **[unverified]**.
8. **How much autonomy.**
   - *Hands-off:* Ralph, CE's `lfg`, OMC's autopilot, BMad Loop.
   - *Human in the loop:* HumanLayer says don't outsource the thinking. Anthropic says watch the first minute and have a person sign off. Kiro and Spec Kit put a human review between steps.

---

## 4. Recommendation: top 7 to study in depth for an EGM + superpowers combination

Ranked by **what it adds**, not by stars. Claims about EGM come from the installed copy described in the header. Confirm them against your working version.

| Rank | Study | What it adds | What specifically to read |
|---|---|---|---|
| 1 | **HumanLayer RPI → CRISPY (riptide-rpi skills)** | A ticket, research, plan, build pipeline. HumanLayer published what *broke* at scale. Three things to take: (1) **research blinded to the ticket**; (2) **a short design-discussion artefact** (current state, desired state, patterns to follow, decisions) grounded in that objective research and reviewed before the plan; (3) **an explicit per-stage instruction budget**. | `create-research-questions`, `create-research`, `create-design-discussion` and `create-structure-outline` SKILL.md files in `apps/riptide-rpi-claude-plugin/skills`. The ACE essay. The CRISPY talk summary. |
| 2 | **Anthropic first-party guidance** (best practices, long-running-harness post, `code-review` and `feature-dev` plugins) | superpowers' gates are prompt-level. This shows how to make the must-never-skip steps **harness-enforced**: hooks, Stop hook, `/goal`, deny rules. It adds a **pass/fail feature-list JSON plus progress log for unattended builds**. It also adds a **0-100 confidence score with an 80 threshold and a false-positive exclusion list**. EGM's synthesizer groups by severity but has no drop threshold. | best-practices (deterministic vs non-deterministic; Stop hook; "what you can stop doing"). The effective-harnesses post. `plugins/code-review/commands/code-review.md`. |
| 3 | **OpenSpec** | EGM's design doc is per change. It keeps no **living current-behaviour spec**. OpenSpec's **delta specs (ADDED/MODIFIED/REMOVED) merged into `openspec/specs/` on archive** give later tickets a spec to diff against. This is the "spec-anchored" level that Böckeler found missing in other tools. | `docs/concepts.md` (delta and archive semantics). The change-folder layout. |
| 4 | **Compound Engineering** | **Automatic feed-forward of lessons**: `/ce-compound` writes `docs/solutions/`, which `/ce-plan` reads. `ce-compound-refresh` keeps that store from going stale. Skip CE's reviewer swarm, which EGM already covers. | `ce-compound`, `ce-plan`, `ce-compound-refresh` and Compound Packs. The compound-engineering guide. |
| 5 | **Matt Pocock's skills** | Not for grilling, which superpowers already has. For **shared domain language**: `GLOSSARY.md` and ADRs updated *as a side effect of* grilling, so decisions persist beyond one ticket. Also **tracer-bullet ticket slicing**, `wayfinder` for work too big for one ticket, and a **`retro` that edits the agent environment**. | `grill-with-docs`, `domain-modeling`, `to-tickets`, `wayfinder` and `retro`. |
| 6 | **Kiro spec flow via cc-sdd** | **Requirement lines in a test-mappable notation (EARS)**, a mandatory **"unchanged behaviour" section for bugfix specs**, and **property-based tests derived from requirements** as a behaviour sensor. cc-sdd's `validate-gap` is a cheap brownfield pre-design check. | Kiro feature-spec and bugfix-spec docs, and the Correctness page. cc-sdd's `kiro-validate-gap` and `kiro-impl`. |
| 7 | **BMAD Method (v6 stable, v7 in flight)** | **Right-sizing**: BMAD's scale-adaptive tracks show how to send small changes past phases. Its **correct-course** step names the mid-build re-plan **[secondary source]**. Skip the personas. Wait for v7 to settle before studying deeply. | The "Choose a Planning Path" guide. Correct-course and retrospective. The v7 loop description in the README. |

**Next tier (skim only)**
- **Beads**, for a cross-session work graph below Jira granularity.
- **GSD Core**, for its plan-fits-fresh-context gate, wave execution and `STATE.md`.
- **Spec Kit**, for its constitution, converge loop and kill-verdict assessment.
- **Agent OS**, for discovering standards from code.
- **Ralph and `ralph-loop`**, only if a build phase needs to run longer unattended.
- **Tessl**, only as a reference for publishing and scoring skill evals.
- **Not recommended for this combination:** ruflo, oh-my-openagent and Gas Town. They have high orchestration complexity, and their claims are either unverified or contradicted by the evidence on how well coding parallelises.

### Status summary of candidates checked
- **Archived and moved:** GSD (`gsd-build/get-shit-done`, archived 2026-06-26; `gsd-2` also archived), now at `open-gsd/gsd-core`.
- **Dormant:** Claude Task Master (last push 2026-04-28; README now points to a commercial product). context-engineering-intro (last push 2026-03-16).
- **Pivoted:** Tessl (from spec-as-source to a skills registry and eval platform).
- **Renamed:** claude-flow to ruflo. oh-my-opencode to oh-my-openagent, which also changed harness.
- **Static (reference only):** 12-factor-agents (last push 2025-09). Ralph reference repos (last pushes January and February 2026). The official `ralph-loop` plugin is maintained.
- **Changed form:** Anthropic's "explore, plan, code, commit" post now redirects to the current best-practices docs, which no longer use that framing. Cline Memory Bank is a documented pattern, not a feature.
