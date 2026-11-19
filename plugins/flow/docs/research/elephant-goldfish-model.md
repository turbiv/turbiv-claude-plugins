# Elephant-Goldfish Model (EGM): workflow analysis

**Sources**
- Primary: GitHub HEAD shallow clone (30 commits, 2026-11-09 to 2026-11-17, untagged), including the "EGM Lite" commit `70406c4`.
- Secondary: the installed v0.1.1 plugin (`~/.claude/plugins/cache/egm/egm/0.1.1`).
- Public write-ups: the Google OSS blog launch post, the research.google abstract of the original essay, and two third-party reviews.

**Citations.** Every `path:line` is relative to the repo root.
- `[implemented]`: enforced by skill or agent prompt text, adapter frontmatter, or a unit test that CI runs.
- `[claimed]`: appears only in README, `docs/`, design docs or external write-ups.
- Many `[implemented]` items are prompt instructions, not host-enforced limits. The text says which is which where it matters.
- `docs/claude.md` and `docs/codex.md` count as prompt text, because every skill tells the agent to read them first (`skills/egm-review/SKILL.md:14-15`). Other `docs/*` files count as `[claimed]`.
- A cited claim with no tag inherits the tag of the file it cites: `skills/`, `agents/`, `resources/`, adapters and tests are `[implemented]`; `docs/designs/`, README and the web are `[claimed]`.
- External write-ups were read through a summarising fetch tool, so their wording is paraphrased, not quoted.

**Version note.** HEAD's manifest still says `0.1.1` (`.claude-plugin/plugin.json:4`). The shallow clone has no tags, so I worked out the HEAD-vs-installed delta by diffing files, not from a git range.

**What HEAD adds over installed v0.1.1.** Adapters and personas are byte-identical. The differences are:
- **The `egm-lite` skill.** Its design doc is still "Proposed" (`docs/designs/lite.md:4`).
- **`.NET` detection in `egm-bootstrap`.**
- **README changes:** a "60-second review on existing code" quickstart and a Lite row (`README.md:56-74, 134`).
- **Doc edits:** `docs/harnesses.md` (commit-vs-gitignore guidance, Windsurf) and `docs/releases.md` (provenance bundle).
- **Manifest author:** "Google" became "Google LLC" (`.claude-plugin/plugin.json:6-8`).

The `TEST.md` and `test_scenarios.yaml` files, `docs/designs/` and `docs/directory.md` are absent from the installed copy because the packager excludes them (`tests/unit/test_packaging.py:77-85`), not because they are new. The other-harness guides (`docs/cursor.md`, `docs/copilot.md`, `docs/muse.md`, `docs/opencode.md`) predate the visible history, so I could not tell whether they are new or packaging-excluded.

---

## 1. TL;DR

- **What it is.** An Apache-2.0 plugin of 8 skills, 9 reviewer/orchestrator personas plus a bootstrap orchestrator, and 5 rubric files. It is "not an officially supported Google product" (`README.md:158`). It runs on Claude Code, Codex and Antigravity, with experimental adapters for Cursor, Copilot, OpenCode and Windsurf.
- **Philosophy** (design-as-code, per the Google OSS blog `[claimed]`): a context-rich **Elephant** writes the spec with the human; fresh, read-only **Goldfish** subagents that never saw that conversation attack it against written rubrics; the **human** decides (`README.md:18`).
- **Lifecycle position.** Upstream of code: idea, then requirements, then design, then implementation-plan review, plus doc maintenance (bootstrap, drift).
- **Out of scope / HEAD-only.** Core EGM has no implement, test or PR skill (`docs/designs/architecture.md:157-159`). HEAD-only **EGM Lite** adds a small-change loop: critique, checklist, exec with tests, fresh diff review (`skills/egm-lite/SKILL.md:19-25`).

---

## 2. Inventory

### Skills

All 8 skills set `disable-model-invocation: true`, so only the user can invoke them (e.g. `skills/egm-review/SKILL.md:4`). In Claude Code they are `/egm:egm-*`.

| Skill | One line | In v0.1.1? |
| --- | --- | --- |
| `egm-brainstorm` | Multi-turn questioning, then a readiness gate, then a 7-lens Goldfish swarm via the synthesizer. Writes `concepts_brief.md` (`skills/egm-brainstorm/SKILL.md:102-210`). | yes |
| `egm-draft` | Section-by-section drafting of `design_draft.md` with an approval gate per section. Reconciles against the brief, then writes `docs/designs/<FEATURE>.md` (`skills/egm-draft/SKILL.md:80-321`). | yes |
| `egm-review` | 5-stage Goldfish pipeline (stages numbered 5 to 9) with 4 presets. Per-stage report files (`skills/egm-review/SKILL.md:121-426`). | yes |
| `egm-review-loop` | Generic "reviewers × standards × target" loop with convergence rules. Also the engine for review stages 7 and 9 (`skills/egm-review-loop/SKILL.md:80-199`). | yes |
| `egm-resolve` | Elephant-side triage into CONTEST / ESCALATE / PROPOSE FIX / DECLINE. Writes `goldfish_review_report.md` and applies approved edits (`skills/egm-resolve/SKILL.md:54-187`). | yes |
| `egm-bootstrap` | "Peanuts and Hay": bottom-up README "contract" generation via partitioned workers and read-only scouts (`skills/egm-bootstrap/SKILL.md:13-24`). | yes (HEAD adds .NET detection) |
| `egm-drift-report` | Single-context comparison of each design doc or README against the code. Writes `{YYYY-MM-DD}_DRIFT_REPORT.md` (`skills/egm-drift-report/SKILL.md:21-67`). | yes |
| **`egm-lite`** | **New at HEAD.** A 5-section state machine driven by typed commands (`checklist`, `exec`, `goldfish`/`review`) for small changes (`skills/egm-lite/SKILL.md:27-78`). | **no** |

### Agents

There are three layers, so nothing is double-counted.

**Layer 1: canonical personas in `agents/` (harness-agnostic).**
- **Reviewers (8).** All share one "Core Mandates" header (read-only, stateless, no chitchat), e.g. `agents/zoom_out.md:7-13`.
  - `zoom_out`: Skeptical Architect, YAGNI and reuse.
  - `comprehension`: naive reader.
  - `design_critic`: architecture and risk.
  - `implementation_readiness`: tech lead / implementer.
  - `codebase_details`: doc-vs-code auditor.
  - `structural`: heading and template conformance.
  - `style`: copy editor and claim calibration.
  - `inventive_catalyst`: TRIZ false-compromise finder.
- **Orchestrators (2).** `synthesizer` (fan-out, dedup, report writer; `agents/synthesizer.md:7-14`) and `bootstrap_orchestrator` (`agents/bootstrap_orchestrator.md:7-30`).

**Layer 2: `.claude-plugin/agents/*.md` (10 files).**
- These are **not duplicates**. They are 17-22-line Claude adapters.
- Their frontmatter sets `tools`, `model: inherit`, `omitClaudeMd: true` for reviewers, and a body that says "Read `${CLAUDE_PLUGIN_ROOT}/agents/<x>.md`" (`.claude-plugin/agents/zoom_out.md:1-17`).
- The manifest lists only the adapters, so the root `agents/` folder is not auto-loaded in Claude (`docs/claude.md:116-127`).
- Adapters and personas are byte-identical between v0.1.1 and HEAD.
- The same pattern repeats for Cursor (`.cursor-plugin/agents/style.md:1-15`, `readonly: true`), Copilot (`com.github.copilot/agents/egm-style.agent.md:1-15`, `tools: [read, search]`, `include-custom-instructions: false`), Windsurf routing rules (`.windsurf/rules/egm.md:1-12`) and an OpenCode installer (`adapters/opencode/install.py`).

**Layer 3: runtime-defined agent.**
- `goldfish-explorer`: a read-only scout that bootstrap registers on the fly and that returns `{"interface","invariants","side_effects"}` JSON (`skills/egm-bootstrap/SKILL.md:208-223`).
- EGM Lite's "Goldfish Specification Reviewer" and "Goldfish Reviewer" are ad-hoc, role-named subagents. They have no persona file (`skills/egm-lite/SKILL.md:202-224, 313-317`).

### Other components

- **Shared resources.**
  - `resources/execution_instructions.md`: design-only scope, one question at a time, contradiction audit.
  - 5 standards in `resources/document_standards/`: feature-spec, Heilmeier, implementation-readiness, re-implementation, zoom-out.
  - Templates: `skills/egm-draft/references/design_doc.md` and `skills/egm-bootstrap/references/templates.md`.
  - Schema: `skills/egm-bootstrap/references/worker-return.schema.json`.
- **Hooks: none, and that is enforced.**
  - A unit test asserts there is no `hooks` key and no `.claude-plugin/hooks/allow_plugin_reads.sh` file (`tests/unit/test_harnesses.py:234-239`).
  - Naming that specific file, plus a leftover mention of "read-hook tests" (`TESTING.md:48`), suggests an auto-approval read hook once existed and was removed. The shallow history cannot confirm this.
  - The packager refuses hooks (`scripts/pack_plugin.py:83-84`).
- **CI workflows (9)** in `.github/workflows/`:
  - `tests.yml`: unit tests, ruff/actionlint, site.
  - `copilot-native.yml`, `cursor-native.yml`, `opencode-native.yml`: adapter checks, path-triggered on PRs.
  - `pr-triage-review.yml`, `pr-scope-advisory.yml`: contributor-PR triage.
  - `release.yml`, `deploy-site.yml`, `scorecard.yml`.
- **Commands.** There are no separate commands; skills are the commands. EGM Lite adds in-chat verbs (`checklist`, `exec`, `goldfish`, `review`; `skills/egm-lite/SKILL.md:39-49`).
- **Scripts.** None run at workflow time.
  - `scripts/pack_plugin.py` and `scripts/prepare_release.py`: packaging and release.
  - `adapters/opencode/install.py`.
  - `.github/scripts/review_pr.py`: the repo's own CI PR triage with a two-pass "hunt then disprove" Gemini review (`.github/scripts/review_pr.py:1081-1215`). It is not shipped.
- **Tests.**
  - `tests/unit/*` are structural.
  - `skills/*/TEST.md` and `skills/*/test_scenarios.yaml`: 71 scenarios, all `eval_type: "deterministic"`.
  - Opt-in live probes live in `tests/integration/*`.

### How the document standards are used

Four of the five standards share one "Core Principle" phrasing. Zoom-out has its own principle (`resources/document_standards/zoom-out-standard.md:6-12`), and Heilmeier says "project" rather than "codebase". The shared phrasing is: the document passes if "a competent engineer (or fresh AI session) who is unfamiliar with the codebase" can understand it or act on it (`resources/document_standards/feature-spec-standard.md:8-11`; `resources/document_standards/implementation-readiness-standard.md:7-10`). In other words, the Goldfish reader test is written down as a rubric.

**How a standard reaches a reviewer.**
- The `Standards` map in `egm-review-loop` assigns each reviewer a standard. A name is a shortname, or a path if it contains a slash (`skills/egm-review-loop/SKILL.md:56, 65-78`).
- The Claude adapter tells the reviewer to read the target and every supplied standard. If one is unreadable, it must "report an incomplete review instead of a verdict" (`.claude-plugin/agents/zoom_out.md:16-17`) `[implemented]`.

| Standard | What it tests | Where it is wired by default |
| --- | --- | --- |
| **Zoom-out** | Context sufficiency as a prerequisite; root cause vs symptom; YAGNI; no premature optimisation; "anti-weeds" altitude control; reuse of existing code (`resources/document_standards/zoom-out-standard.md:6-60`) | Stages 5 and 8 via `zoom_out` (`skills/egm-review/SKILL.md:315-325`; `agents/zoom_out.md:44`) `[implemented]` |
| **Feature-spec** | Mandatory alternatives with concrete rejection reasons; no unlinked "rejected by maintainer"; risks and limits; goals and non-goals (`resources/document_standards/feature-spec-standard.md:13-39`) | Stage 7 for `design_critic` and `structural` (`skills/egm-review/SKILL.md:373-376`) `[implemented]`; also the draft "Document Structure" alignment (`docs/designs/draft.md:188`) `[claimed]` |
| **Implementation-readiness** | Zero-Decision Rule; phases that each leave a buildable state; Target Scope & File Boundary as a write allowlist; concrete test plan (`resources/document_standards/implementation-readiness-standard.md:12-37`) | Stage 9 for `implementation_readiness` and `codebase_details` (`skills/egm-review/SKILL.md:400-405`) `[implemented]` |
| **Re-implementation** | A fresh reader could write functionally identical code; Zero-Assumption Rule; include contracts, exclude syntax (`resources/document_standards/re-implementation-standard.md:6-37`) | **No default stage.** Explicitly banned for comprehension because it would demand code detail in FeatureRange (`skills/egm-review/SKILL.md:355-356`). Reachable only as a review-loop shortname (`skills/egm-review-loop/SKILL.md:74-76`). It is the obvious rubric for bootstrap READMEs, but bootstrap never references it. |
| **Heilmeier** | 8 catechism questions: objectives "with absolutely no jargon", state of the art, impact, risks, cost, timeline, exams (`resources/document_standards/heilmeier-standard.md:13-30`) | **No default stage.** Review-loop shortname only (`skills/egm-review-loop/SKILL.md:75`). The brainstorm design doc claims it is used (`docs/designs/brainstorm.md:129-131`) `[claimed]`; the brainstorm skill never loads it. |

The `inventive_catalyst` persona has no standard file. It carries an inlined catalog of 10 TRIZ-derived software patterns, each with its "secondary trade-off" (`agents/inventive_catalyst.md:29-52`).

### How they chain

```
                      ┌── human: multi-turn Q&A ──┐
/egm-brainstorm ──► readiness gate ──► egm-synthesizer (Mode: BRAINSTORM)
                                         └─► 7 personas in BRAINSTORM mode (parallel)
                     ◄── concepts_brief.md ──┘   ──► handoff gate (RFC | draft | refine | stop)
/egm-draft ──► intake (brief > discussion_summary > chat) ──► 4 sections, each with an approval gate
           ──► reconcile draft vs brief (Elephant only) ──► save docs/designs/<F>.md (+SITEMAP.md)
/egm-review <doc> ──► preset gate ──► split FeatureRange | DetailedRange
   S5 zoom_out + inventive_catalyst (full)  ─► zoom_out_report.md            ─► gate
   S6 comprehension (direct, doc only)      ─► comprehension_report.md       ─► gate
   S7 egm-review-loop[design, structural, style] (Feature) ─► critic_report.md ─► gate ─► egm-resolve?
   S8 zoom_out (full, focus on additions)   ─► intermediate_zoom_out_report.md ─► gate
   S9 egm-review-loop[impl_readiness, codebase_details, style] (Detailed) ─► implementation_readiness_report.md ─► gate ─► egm-resolve?
human PR of the design doc ──► "tell AI to build to the plan" (no EGM skill) ──► /egm-drift-report (weekly)
/egm-bootstrap (brownfield context) ──► optional drift report on generated READMEs
/egm-lite (small changes): critique ─checklist─► [goldfish spec review] ─exec─► tests ─review─► fresh diff review ─► triage ─► done | loop
```

---

## 3. End-to-end walkthrough

The example is "add webhook delivery" (the README's own example, `README.md:78`).

### Step 1. `/egm:egm-brainstorm Add webhook delivery`

**Opening (Elephant, main context).**
- Resolves the author from `git config user.name` (`skills/egm-brainstorm/SKILL.md:106-109`).
- Asks open-ended questions over several turns. Multiple-choice tools and canned answers are banned in this phase (`skills/egm-brainstorm/SKILL.md:46-53, 110-125`).

**Readiness gate (human decision).**
- The Elephant summarises a 2-3 sentence "anchored hypothesis" and asks a single-select question: "Review with Goldfishes" or "Clarify" (`skills/egm-brainstorm/SKILL.md:127-158`).
- No subagent may be spawned before the human says yes.

**Goldfish swarm (subagents).**
- `egm-synthesizer` runs in `Mode: BRAINSTORM` (`skills/egm-brainstorm/SKILL.md:162-169`).
- It launches 7 personas in their BRAINSTORM mode. Each persona doubles as one "lens" (`docs/designs/brainstorm.md:121-128`):
  - zoom_out = YAGNI
  - design_critic = cost / quota
  - comprehension = UX
  - implementation_readiness = migration
  - codebase_details = observability
  - structural = tech debt
  - inventive_catalyst = TRIZ
- A reviewer that fails twice is recorded as `not run` (`agents/synthesizer.md:29-34`).

**Brief and handoff.**
- **Artifact:** `concepts_brief.md` with the sections Overview, Analysis, Goals/Non-Goals, **Alternatives Weighed** and Key Decisions (`skills/egm-brainstorm/SKILL.md:181-210`).
- The Elephant highlights 2-3 objections and the human iterates (`skills/egm-brainstorm/SKILL.md:212-220`).
- **Handoff gate (human decision):** publish as an RFC to `docs/designs/`, proceed to draft, keep refining, or stop (`skills/egm-brainstorm/SKILL.md:222-271`).

### Step 2. `/egm:egm-draft`

This often runs in a new session.

**Ground rules.** The Elephant loads `resources/execution_instructions.md` (`skills/egm-draft/SKILL.md:22-23`):
- no production code (`resources/execution_instructions.md:3-19`)
- one question per response (`:24-28`)
- if a new request contradicts earlier goals, no file writes in that turn (`:32-37`)

**Intake.** It looks for `concepts_brief.md`, then `discussion_summary.md`, then asks in chat. The human confirms the context (`skills/egm-draft/SKILL.md:141-166`).

**Drafting, one section at a time.** After each section, a single-select approve/revise gate (`skills/egm-draft/SKILL.md:87-139`):
1. Overview / Problem / Goals / Non-Goals.
2. Technical Plan, with diagrams.
3. Alternatives Considered, copied from the brief's Alternatives Weighed: "Do not rely on memory" (`skills/egm-draft/SKILL.md:201-221`).
4. Detailed Implementation: every file, each with a rationale, and NO CODE (`skills/egm-draft/SKILL.md:223-250`).

**Architecture choices (human decision).** When a choice has several defensible answers, the Elephant presents up to 3 **unranked** options with their failure conditions. If the human says "just pick one", it re-presents them (`skills/egm-draft/SKILL.md:63-71`).

**Finalisation.**
- The Elephant reconciles the draft against the brief and lists contradictions. The human decides each one (`skills/egm-draft/SKILL.md:257-275`).
- Gate for the target directory (`:277-304`), then `SITEMAP.md` registration (`:306-307`).
- **Artifact:** `docs/designs/<FEATURE>.md`.

### Step 3. `/egm:egm-review docs/designs/webhooks.md`

**Intake and setup.**
- TargetFile, then an optional `GoldfishContext` reading list (`skills/egm-review/SKILL.md:82-100`).
- Preset gate, a human decision with four options: interactive, consolidated/uninterrupted, feature-spec-only, implementation-only (`skills/egm-review/SKILL.md:121-177`).
- Semantic split at `## Detailed Implementation Plan` into `FeatureRange` and `DetailedRange` (`skills/egm-review/SKILL.md:179-207`).
- Linked files inside the workspace are added automatically. External links and URLs need human approval, and URLs are saved as local files (`skills/egm-review/SKILL.md:101-119`).

**Stages**

| Stage | Reviewers | Scope | Report |
| --- | --- | --- | --- |
| 5 | zoom_out + inventive_catalyst | full document, zoom-out standard | `zoom_out_report.md` (`skills/egm-review/SKILL.md:315-347`) |
| 6 | comprehension, spawned **directly** | document only, no standard, no GoldfishContext | `comprehension_report.md`, starting with the reviewer's paraphrase (`skills/egm-review/SKILL.md:349-369`) |
| 7 | `egm-review-loop` with design, structural, style | FeatureRange, feature-spec standard | `critic_report.md` (`skills/egm-review/SKILL.md:371-396`) |
| 8 | zoom_out | full document, focused on additions from stages 6-7 | `intermediate_zoom_out_report.md` |
| 9 | `egm-review-loop` with implementation_readiness, codebase_details, style | DetailedRange, implementation-readiness standard | `implementation_readiness_report.md` (`skills/egm-review/SKILL.md:398-426`) |

**Stage gates (human decisions).** After each stage the human picks one option (`skills/egm-review/SKILL.md:229-278`):
- proceed
- resolve with the agent (stages 7 and 9)
- edit manually and re-run, with at most 1 re-audit per stage
- pause

**Resolving findings with the agent (egm-resolve, in the Elephant's context).**
- Every finding is classified (`skills/egm-resolve/SKILL.md:54-82`).
- **Artifact:** `goldfish_review_report.md`.
- The Elephant stops with zero tool calls. The human then chooses auto-accept, continue, an item-by-item breakdown, or a custom instruction (`skills/egm-resolve/SKILL.md:110-178`).
- Edits are applied to the design doc and the report is stamped `Status: resolved` (`skills/egm-resolve/SKILL.md:180-187`).

**Uninterrupted preset.** All 5 stages run without gates and produce a cross-stage `consolidated_review_report.md` with a traceability matrix (`skills/egm-review/SKILL.md:280-313`).

### Step 4. Outside EGM

- **Human PR review** of the design doc (`docs/getting_started.md:75-77`).
- **Implementation:** "Tell AI to build to the plan" (`docs/getting_started.md:79-87`). The plan's `Target Scope & File Boundary` list is meant to be the write allowlist, but "nothing enforces it" (`docs/designs/architecture.md:160-167`) `[claimed]`.

### Step 5. Maintenance

- `/egm-drift-report docs/designs/`, run weekly (`docs/getting_started.md:94-99`).
- **Artifact:** `{date}_DRIFT_REPORT.md`, which lists only divergences. The human decides whether to fix the doc or the code.

### Small-change path (HEAD only): `/egm:egm-lite <task>`

1. **Critique pause.** The Elephant grounds itself in code and writes no code (`skills/egm-lite/SKILL.md:96-132`).
2. **`checklist`.** Writes `egm_lite_checklist.md` plus an adaptive "spec review recommended?" BLUF (`:142-184`).
3. **Optional `goldfish`.** A fresh spec review of the checklist (`:186-225`).
4. **`exec`.** Records the baseline commit, implements only the checklist, runs tests and never weakens assertions (`:229-280`).
5. **`review`.** A fresh diff review over a full change inventory (`:284-351`).
6. **Triage.** FIX vs CONTEST, read-only (`:355-428`).

Every transition is a typed human command.

---

## 4. Rubric

### 4.1 Lifecycle phases covered

| Phase | Coverage | Evidence |
| --- | --- | --- |
| Idea | **Strong** | brainstorm Q&A plus 7-lens swarm `[implemented]` (`skills/egm-brainstorm/SKILL.md:102-210`) |
| Requirements / spec | **Strong** | brief Goals/Non-Goals; draft Overview/Goals; feature-spec standard `[implemented]` (`resources/document_standards/feature-spec-standard.md:13-39`) |
| Design | **Strong** | draft Technical Plan and Alternatives; review stages 5-8 `[implemented]` |
| Plan | **Strong** | draft Detailed Implementation; stage 9 against the Zero-Decision Rule `[implemented]` (`resources/document_standards/implementation-readiness-standard.md:12-37`) |
| Implement | **Absent in core.** Lite only. | "No Skill.md is required here" (`docs/designs/architecture.md:157-159`); Lite exec `[implemented]` (`skills/egm-lite/SKILL.md:229-280`) |
| Test | **Weak.** | Template "Verification Plan" section (`skills/egm-draft/references/design_doc.md:161-171`); Lite runs tests and must not weaken assertions (`skills/egm-lite/SKILL.md:262-272`) |
| Review (code) | **Lite only.** | Fresh diff review (`skills/egm-lite/SKILL.md:284-351`). Core EGM reviews *documents*, not diffs. |
| PR / merge | **Absent.** | "Send a Pull Request with your design to another human" (`docs/getting_started.md:75-77`) `[claimed]` |
| Retro / learning | **Absent.** | Only drift detection and bootstrap docs as maintenance. Nothing feeds lessons back into standards. |

### 4.2 Human gates

**Where the human decides**

- **Brainstorm.**
  - Readiness gate before any swarm runs.
  - Iteration on the objections.
  - Handoff gate.

  `[implemented]` (`skills/egm-brainstorm/SKILL.md:127-158, 212-271`)
- **Draft.**
  - Context confirmation.
  - An approval gate per section; "Request revisions" with no text triggers an explicit prompt rather than a loop (`skills/egm-draft/SKILL.md:134-139`).
  - Architecture choices.
  - Brief-contradiction decisions.
  - Target directory.

  `[implemented]` (`skills/egm-draft/SKILL.md:80-139, 257-304`)
- **Review.**
  - Preset choice.
  - Stage checkpoints (interactive preset only).
  - Resolve gate: the Elephant "MUST immediately yield ... zero tools".
  - Round confirmation in `egm-review-loop`.
  - Cap or churn decision.

  `[implemented]` (`skills/egm-review/SKILL.md:121-177, 229-278`; `skills/egm-resolve/SKILL.md:132-134`; `skills/egm-review-loop/SKILL.md:179-187`)
- **Bootstrap.** Approval if more than 15 directories are found (`skills/egm-bootstrap/SKILL.md:66-68, 113-125`) `[implemented]`.
- **Lite.** Every phase transition is a typed command, enforced by a "Model Rule: Halt for <trigger>" convention and a list of banned transitions (`skills/egm-lite/SKILL.md:35-67`) `[implemented]`.

**How the human decides.** Gates follow strict invariants:
- one question per gate (`len(questions) == 1`)
- single-select
- the question is the sole tool call in the turn
- no "(Recommended)" prefix

The aim is to avoid nudging the human (`skills/egm-review/SKILL.md:132-142`; `resources/execution_instructions.md:24-28`) `[implemented]`. Bootstrap itself violates this with "(Recommended) Yes" (`skills/egm-bootstrap/SKILL.md:413`).

**What runs unattended**
- Synthesizer fan-out and dedup.
- The whole 5-stage pipeline under the "Consolidated report" preset (`skills/egm-review/SKILL.md:167-170`).
- Bootstrap workers once approved; spawning is "unbounded" (`skills/egm-bootstrap/SKILL.md:192-200`).
- Lite's test/fix convergence inside the checklist scope (`skills/egm-lite/SKILL.md:265-272`).
- Headless runs skip link-approval questions and leave those links out (`skills/egm-review/SKILL.md:110-117`).

### 4.3 Artifacts and state

**What persists.** All artifacts are Markdown in the working directory, or in an `EGM artifact directory: <path>` named in the prompt or `CLAUDE.md`/`AGENTS.md` (`docs/claude.md:29-38`; `docs/harnesses.md:120-137`) `[implemented]`.

| Phase | Artifacts |
| --- | --- |
| Brainstorm / draft | `concepts_brief.md`, `design_draft.md`, `docs/designs/<F>.md`, `docs/designs/SITEMAP.md` |
| Review | `zoom_out_report.md`, `comprehension_report.md`, `critic_report.md`, `intermediate_zoom_out_report.md`, `implementation_readiness_report.md`, `consolidated_review_report.md` |
| Resolve | `goldfish_review_report.md`, stamped `Status: resolved` |
| Drift / bootstrap | `{YYYY-MM-DD}_DRIFT_REPORT.md`; per-directory `README.md` (or `EGM.md`) contracts |
| Lite | `egm_lite_checklist.md`, `egm_lite_alternatives.md` |

**Phase handoff is file-based by design.**
- The brief's `Alternatives Weighed` section exists because "`/egm-draft` copies these ... and has no other source for them" (`skills/egm-brainstorm/SKILL.md:202-205`), and drafting "often runs in a new session" (`skills/egm-draft/SKILL.md:203-206`) `[implemented]`.
- The deliverables must outlive the per-session scratchpad (`docs/claude.md:29-31`).
- Generated docs carry a provenance footer (`skills/egm-draft/references/design_doc.md:175-177`).

**Resumability is weak in core EGM.**
- No file records the current review stage, the round, or the "settled findings" list. The settled list is kept "across rounds" only in the conversation (`skills/egm-review-loop/SKILL.md:162-165`).
- "Pause Review" just halts and keeps the reports (`skills/egm-review/SKILL.md:276-278`).
- The maintainers acknowledge "Lost After a Break" and propose a Draft `egm-ask` skill to infer next steps from the files on disk (`docs/designs/ask.md:31-38`) `[claimed]`.

**Lite is better here.** The checklist carries the task list, the baseline commit, pre-review exclusions, accepted CONTEST rationales and a `Spec Review Status` stamp (`skills/egm-lite/SKILL.md:147-170, 246-253, 373-375`) `[implemented]`.

### 4.4 Context-isolation strategy

**The metaphor, precisely: who remembers what**

**Elephant: the long-lived main session, together with the human.**
- It remembers the conversation, requirements, constraints, rejected alternatives, code it explored and earlier decisions (`README.md:115`; `docs/designs/architecture.md:42-44`).
- It explores, drafts and later *triages and fixes*. Resolve runs in the Elephant "to recall earlier reasoning and craft higher-quality fixes" (`skills/egm-resolve/SKILL.md:26-28`).
- **Its weakness is that memory.**
  - It "assumes the context it holds in memory is obvious from the text" (`docs/designs/review.md:30-31`).
  - It agrees with its own draft: "The session that wrote the draft agrees with it" (`skills/egm-draft/SKILL.md:258-259`).
  - Over a long thread it builds a "hallucination cascade" of unchecked hypotheses (`docs/designs/architecture.md:25-29`).
- Its long-term memory is pushed into files: the brief, the design doc, `SITEMAP.md` and bootstrap READMEs, plus an optional `<project>-elephant` context-loader skill (`docs/getting_started.md:140-152`). The Elephant does not have unlimited recall; continuity across sessions comes from those written artifacts.

**Goldfish: a brand-new subagent with no conversation memory.**
- It gets the document, a persona, a rubric, an explicit `GoldfishContext` reading list, and read-only tools over the workspace.
- **Its value is that it stands in for the future reader.** That is a new teammate, or the implementing agent in a fresh session, who will have *only* the document.
  - If the Goldfish cannot paraphrase, follow or execute the plan from the text, the gap is in the document, not in the reviewer.
  - That is the essay's core test: if a fresh session cannot understand the plan from the document alone, the document needs more detail (research.google abstract) `[claimed]`.
- It cannot be anchored by the author's framing or by hypotheses formed in the conversation, because it never saw them.

**Human: the third role.** The human resolves trade-offs and approves (`README.md:18, 117`).

**Nuances the marketing glosses over**
- **A Goldfish is not blind.** It has read access to the workspace, so this is "context and tool isolation, not filesystem isolation" (`docs/claude.md:162-166`). `zoom_out` and `codebase_details` are *required* to search the code (`agents/zoom_out.md:45`; `agents/codebase_details.md:37-39`).
- **How much it forgets depends on the stage.** Stage 6 reads the document *alone*; the other stages also get GoldfishContext (`skills/egm-review/SKILL.md:117-119`).
- **Only the Elephant can check fidelity to the brief.** "No Goldfish can do this check, because no Goldfish reads the brief" (`skills/egm-draft/SKILL.md:257-261`).
- **The Goldfish is a proxy, not the audience.** Context added only to satisfy it is escalated, not written (`skills/egm-resolve/SKILL.md:74-76`).
- **Its memory is not always clean.** On Codex and Antigravity, project `AGENTS.md`/`GEMINI.md` reportedly leak into Goldfish context (issue #237; `docs/harnesses.md:149-157`) `[claimed]`.

**Who gets what**

| Agent | Given | Kept away from | Why |
| --- | --- | --- | --- |
| Reviewer Goldfish (8 personas) | Task, target path and line range, persona path, standard path, `GoldfishContext` (linked files plus approved URLs saved as files) (`skills/egm-review-loop/SKILL.md:128-133`; `docs/claude.md:131-134`) | Parent conversation; `CLAUDE.md` (via `omitClaudeMd`); write/shell/MCP tools; earlier reviewers (no fork or resume) (`docs/claude.md:131-146, 162-166`) | Self-review "validates its own faulty assumptions" (`docs/designs/architecture.md:25-29`) |
| Stage 6 comprehension | **Only the document**: no standard and no GoldfishContext (`skills/egm-review/SKILL.md:117-119, 351-356`) | Even the supporting files | A naive reader tests self-containment |
| Synthesizer | Reviewer list, standards map, GoldfishContext; tools Agent/Read/Grep/Glob/Write (`.claude-plugin/agents/synthesizer.md:1-22`) | Shell, MCP; write scope by instruction only | Keeps raw output of 6-12 reviewers out of the Elephant's context (`docs/designs/synthesizer.md:19-33`) |
| Elephant (draft, resolve) | Full conversation and brief (`skills/egm-resolve/SKILL.md:24-28`) | n/a | Memory improves fixes and the brief-vs-draft reconciliation that "No Goldfish can do" (`skills/egm-draft/SKILL.md:257-261`) |
| Bootstrap `goldfish-explorer` | One directory chunk of about 1,500 lines, imports and definition list, child summaries (`skills/egm-bootstrap/SKILL.md:247-286`) | Write and subagent tools | Grounded per-directory extraction with `[file:symbol]` citations |
| Lite spec / diff Goldfish | Checklist text, change inventory and full change content (`skills/egm-lite/SKILL.md:202-211, 297-312`) | "conversational history and authorial justification" | Diff review free of confirmation bias |

**Enforcement level**

- **Host-enforced and unit-tested on Claude Code.** Each reviewer adapter has `tools == {Read, Grep, Glob}`, `omitClaudeMd: true` and no `memory` (`tests/unit/test_harnesses.py:165-178`). This requires Claude Code ≥2.1.271 (`docs/claude.md:8-9`).
- **Only prompt-instructed.**
  - The synthesizer's "write only the report" rule (`docs/claude.md:144-148`).
  - The core phase write boundaries (`docs/designs/architecture.md:164-165`).
- **Not filesystem isolation.** "reviewers can read accessible files" (`docs/claude.md:162-166`).
- **Weaker on other hosts.** Codex and Antigravity reportedly inject `AGENTS.md`/`GEMINI.md` into reviewers (issue #237; `docs/harnesses.md:149-157`) `[claimed]`.
- **Gap at HEAD (inference from the text).** EGM Lite spawns role-named generic subagents with no persona file and no `egm:*` type (`skills/egm-lite/SKILL.md:221-224, 313-317`). In Claude Code they would presumably be general-purpose subagents, without the Read/Grep/Glob restriction or `omitClaudeMd`.

### 4.5 Verification mechanism

**Document correctness** `[implemented]`. Reviewers are graded against explicit standards, and several rules make verdicts hard to game:
- Comprehension must paraphrase the document first. A wrong paraphrase is a finding (`agents/comprehension.md:37, 57`).
- codebase_details treats "Contradicts the Code" as a Blocker and checks every cited path (`agents/codebase_details.md:47-50`).
- Resolve's CONTEST must cite evidence the reviewer could read (`skills/egm-resolve/SKILL.md:71-82`).
- Convergence needs two consecutive clean rounds (`skills/egm-review-loop/SKILL.md:157-181`).
- Bootstrap must "explicitly read every single created or modified contract file" and check that every link target exists (`skills/egm-bootstrap/SKILL.md:386-405`).
- Drift report compares each doc against the code (`skills/egm-drift-report/SKILL.md:24-43`).

**Code correctness.** Only in Lite:
- tests run during exec (`skills/egm-lite/SKILL.md:262-276`)
- a binary LGTM contract on the diff (`skills/egm-lite/SKILL.md:321-344`)

Core EGM explicitly does not replace tests (`README.md:121`).

**Repo self-verification**
- **What CI runs:** `pytest tests/unit` (`.github/workflows/tests.yml:106`; `pyproject.toml:26`). It covers frontmatter, links, packaging, adapter tool restrictions, a 24,000-byte skill body limit (`tests/unit/test_skill_load_limits.py:15-21`), and the presence of some required phrases (`tests/unit/test_style_and_boundaries.py:22-42`).
- **What only gets schema-checked:** the 71 "deterministic" behavioral scenarios. The test checks that they exist and have `scenario_id`/`eval_type`/`turns` (`tests/unit/test_scenario_coverage.py:23-53`). **No runner exists in the repo**: no code consumes `required_pattern`/`forbidden_pattern`.
- **Live model probes are opt-in.** `EGM_CLAUDE_LIVE=1` and `EGM_CODEX_LIVE=1` (`TESTING.md:89-133`) are not run in CI.
- **Model-free probes do run in CI.** For Copilot and OpenCode, CI runs isolation and permission probes against a *scripted local mock model*, triggered on PRs that touch those adapters. They check transport and permissions, "not model compliance or full workflow execution" (`.github/workflows/copilot-native.yml:6-58`; `tests/integration/opencode_native_probe.py:1-4`).
- **No outcome benchmark.** "Completing the EGM workflow alone does not demonstrate a productivity improvement" (`docs/faq.md:45-46`).

### 4.6 Evidence of iteration and quality

**Honest harness test record.** `TESTING.md:143-152` records failures as well as passes:
- Claude Code: "Initial stage-order failure retained".
- Cowork: "Usage limit interrupted stage 8".
- Muse: named agents unspawnable, so the general-purpose fallback was used.
- Antigravity: "bootstrap skill is larger than the load limit".

**Lessons visible in the prompts and tests**
- **Stage order.** A stage-order failure is followed by an explicit "Keep review stages 5 ... 9 sequential ... Uninterrupted mode skips human checkpoints, not these stage dependencies" (`docs/claude.md:44-47`).
- **Stochastic reviewers.** "Fresh reviewers sample differently each round, so a round with zero findings is rare", so the loop requires two clean rounds and detects churn (`skills/egm-review-loop/SKILL.md:159-181`).
- **Silent reviewer failure.** A failed reviewer is "not run", never "zero findings" (`agents/synthesizer.md:31, 41`).
- **False positives.** "Proposed files are not findings" (`agents/codebase_details.md:50`). "You do not know this project. You do know software" limits jargon flags (`agents/comprehension.md:48`).
- **Wrong rubric for comprehension.** Comprehension must not use the re-implementation standard, backed by a scenario (`skills/egm-review/SKILL.md:355-356`; `skills/egm-review/test_scenarios.yaml:104-113`).
- **Over-fitting to the reviewer.** "Do not add context only to satisfy a reviewer" (`skills/egm-resolve/SKILL.md:74-76`).
- **No permission hook.** A test forbids a specific `allow_plugin_reads.sh` hook and any `hooks` key (`tests/unit/test_harnesses.py:234-239`). That probably reflects a removed auto-approval hook, but the shallow history cannot confirm it. Users instead add scoped `Read(...)` rules for the plugin's own folders (`docs/claude.md:57-103`).
- **Weak trace evidence.** "A persona read request alone is not a successful read" (`TESTING.md:170-176`).

**Git window.**
- Of the 30 visible commits (Nov 9-17), only **2** touch runtime prompts: EGM Lite `70406c4` and the .NET detection fix `2665d1f`. The third match, `6d2af49`, is the shallow-clone root, which shows every file as added.
- Most churn is harness adapters, the site, CI hardening, release provenance and OpenSSF Scorecard.

**Governance dogfooding.**
- Features need a design doc made with brainstorm/draft/review and a two-stage design PR then implementation PR (`AI_POLICY.md:14-30`; `AGENTS.md:12-22`).
- EGM Lite went through exactly that: commit `7ee5846` (Stage 1), then `70406c4` (Stage 2). Its design doc is still marked `Status: Proposed` (`docs/designs/lite.md:4`).

### 4.7 Cost and friction

**Agents spawned**
- Brainstorm: 7 reviewers plus 1 synthesizer per swarm round (`agents/synthesizer.md:30`).
- Full review, minimum (uninterrupted), as derived from the HEAD skill text: 2 + 1 + 3 + 1 + 3 = **10 reviewer runs** plus up to 4 synthesizers (`skills/egm-review/SKILL.md:287-303`).
  - The recorded runs show **9** stage reviewers (`TESTING.md:146, 152`) and 6 brainstorm reviewers on Muse instead of 7.
  - I could not explain the gap from the text.
- Stages 7 and 9 via `egm-review-loop` can each run up to 5 rounds, and convergence needs 2 clean rounds. That alone can add up to about 30 reviewer runs.
- The synthesizer may also run "A and B" instances of every reviewer (`agents/synthesizer.md:40`).
- The test record shows 15-16 native reviewers for one brainstorm + draft + review fixture (`TESTING.md:145, 148, 152`).

**Time and tokens**
- The Codex live suite took 573 s and 482 s for two fixture tests (`TESTING.md:148-149`).
- A Cowork run on Opus hit a usage limit mid-review (`TESTING.md:147`).
- The project does not publish token or time costs. One external review (andrew.ooo) points to an open issue #385 asking for them `[claimed]`.

**Human attention**
- One question per response (`resources/execution_instructions.md:24-28`).
- Four section gates while drafting, up to five stage gates in review, plus resolve triage.
- "This will provide *a lot* of feedback by design. Take what you think is relevant" (`docs/getting_started.md:72-73`).

**Ceremony for small tasks.** The maintainers say it "may not pay off for a small, well-understood change" (`docs/faq.md:39-43`) and "Do not forcibly use the design-first process ... for a simple bug fix" (`docs/getting_started.md:49-51`). EGM Lite exists to address this (`docs/designs/lite.md:20-30`).

### 4.8 Portability

**Generic ideas that transfer anywhere**
- The Elephant/Goldfish split.
- Rubrics as versioned Markdown files.
- The altitude-ordered stages.
- The comprehension paraphrase test.
- The resolve classification enum and convergence rules.
- Artifact-first file handoff.

**Shared canonical text.** All harnesses share one canonical text with thin adapters. Unit tests reject metadata drift between manifests (`docs/harnesses.md:3-5`; `tests/unit/test_harnesses.py:104-160`).

**Bound to the harness**
- Subagent tool names (`invoke_subagent` / `Agent` / `spawn_agent`; `skills/egm-review/SKILL.md:21-28`).
- `${CLAUDE_PLUGIN_ROOT}` path resolution and read-permission rules for the plugin cache (`docs/claude.md:49-103`).
- `omitClaudeMd`, which needs Claude Code ≥2.1.271.
- Nesting limits: Cowork cannot nest subagents, so it uses direct dispatch (`docs/claude.md:39-43`).
- Antigravity-flavored `ask_question` JSON payloads and "side-panel artifacts" (`docs/designs/architecture.md:176-185`).
- Antigravity's 24 KB skill body limit, which shapes skill length.
- Instruction-file leaks on Codex and Antigravity.

---

## 5. Strengths as mechanisms

1. **Refuse rather than degrade.**
   - **What it does:** every Goldfish workflow stops if no fresh-context subagent tool exists, because "a review in the same context is not a Goldfish review".
   - **Failure prevented:** silent fallback to self-review, which looks like a review but carries the author's blind spots.
   - **Citation:** `skills/egm-review/SKILL.md:28`; `skills/egm-brainstorm/SKILL.md:36`; `skills/egm-lite/SKILL.md:196-201`; `.windsurf/rules/egm.md:11`
   - `[implemented]`
2. **Host-enforced reviewer sandbox (Claude Code).**
   - **What it does:** each reviewer is a separate agent type with `tools: [Read, Grep, Glob]`, `omitClaudeMd: true` and no memory. Every review spawns a new instance, never a fork or a resume.
   - **Failure prevented:** reviewers that "fix" the doc themselves, inherit project-instruction bias, or remember earlier rounds.
   - **Citation:** `.claude-plugin/agents/zoom_out.md:1-17`; `tests/unit/test_harnesses.py:165-178`; `docs/claude.md:131-134`
   - `[implemented]`
3. **Altitude-ordered pipeline with a second YAGNI pass.**
   - **What it does:** zoom-out and TRIZ run first, then the naive reader, then the critic, then zoom-out again on what the critic added, and implementation readiness runs last. Stage order is a hard dependency even in uninterrupted mode.
   - **Failure prevented:** polishing details of a design that should be cut, and defensive bloat added to answer critic findings.
   - **Citation:** `skills/egm-review/SKILL.md:139-140, 287-303, 320-322`; `docs/claude.md:44-47`
   - `[implemented]`
4. **Semantic split (FeatureRange / DetailedRange).**
   - **What it does:** high-level and plan sections get different reviewers and rubrics. The zoom-out standard forbids code detail high up; the readiness standard demands it in the plan.
   - **Failure prevented:** contradictory rubrics applied to the same text, and "weeds" in the architecture section.
   - **Citation:** `skills/egm-review/SKILL.md:179-207`; `resources/document_standards/zoom-out-standard.md:41-49`
   - `[implemented]`
5. **Paraphrase-first comprehension test.**
   - **What it does:** a naive reader, given only the document, must restate "What this proposes" and "How the existing system works". The author compares that against their intent. It bypasses the synthesizer so the paraphrase is not dropped.
   - **Failure prevented:** documents whose terms are all defined but whose parts do not connect, and context that lives only in the author's head.
   - **Citation:** `agents/comprehension.md:37, 57`; `skills/egm-review/SKILL.md:351-360`
   - `[implemented]`
6. **Zero-Decision Rule and File Boundary as the plan contract.**
   - **What it does:** a plan fails if the implementer must make *any* design choice. It must list exact repository-relative paths to create, modify or delete, usable as a write allowlist.
   - **Failure prevented:** an implementing agent inventing schemas or APIs, and opportunistic refactors.
   - **Citation:** `resources/document_standards/implementation-readiness-standard.md:12-33`; `agents/implementation_readiness.md:37-43`
   - Rubric `[implemented]`; allowlist enforcement `[claimed]` (`docs/designs/architecture.md:164-167`).
7. **Evidence-gated triage.**
   - **What it does:** CONTEST requires evidence the reviewer could have read. ESCALATE covers knowledge outside the document. Rules: no contesting comprehension gaps, no silent severity changes, and "A wish to contest is not evidence".
   - **Failure prevented:** the memory-rich author rationalising away valid findings, and padding docs to please a zero-context bot.
   - **Citation:** `skills/egm-resolve/SKILL.md:54-82`
   - `[implemented]`
8. **Convergence rules for stochastic reviewers.**
   - **What it does:** contested or accepted findings are "settled" and stay settled; a fix does not settle a finding and re-opens if raised again. A clean round has no unsettled Blocker or Major. The loop converges after 2 consecutive clean rounds, caps at 5, and flags churn when reverting a fix would resolve a new finding.
   - **Failure prevented:** endless loops, re-arguing settled issues, oscillating fixes, and false "done" after one lucky round.
   - **Citation:** `skills/egm-review-loop/SKILL.md:157-181`
   - `[implemented]`
9. **Failed reviewer ≠ clean reviewer.**
   - **What it does:** retry once, then record `not run` in a Reviewer Status table. A round with a not-run reviewer is not clean.
   - **Failure prevented:** a timed-out subagent counted as zero findings, which is a silent false pass.
   - **Citation:** `agents/synthesizer.md:31, 41, 50-54`; `skills/egm-review-loop/SKILL.md:140-144, 171-172`
   - `[implemented]`
10. **The Elephant reconciles against the brief; Goldfish never self-grade.**
    - **What it does:** at finalisation the drafting session does *not* grade its own draft against the zoom-out standard ("The session that wrote the draft agrees with it"). It only diffs the draft against the brief and asks the human about each contradiction, because "No Goldfish can do this check".
    - **Failure prevented:** silent drift from agreed decisions, and fake self-review.
    - **Citation:** `skills/egm-draft/SKILL.md:257-275`
    - `[implemented]`
11. **The human chooses; the agent does not anchor.**
    - **What it does:** up to 3 unranked options, each with the conditions under which it fails. "Just pick one" is refused. Gates hold one question and carry no "(Recommended)" label.
    - **Failure prevented:** the human rubber-stamping the agent's preferred option, and architecture decided by default.
    - **Citation:** `skills/egm-draft/SKILL.md:63-71`; `skills/egm-review/SKILL.md:132-142`
    - `[implemented]`
12. **Artifact-first, file-based handoff.**
    - **What it does:**
      - Long content goes to files and never into chat.
      - The synthesizer returns only counts and a path.
      - The brief carries rejected alternatives explicitly because the next phase may run in a fresh session.
    - **Failure prevented:** context bloat in the Elephant, and handoffs that depend on chat memory.
    - **Citation:** `docs/designs/architecture.md:171-185`; `agents/synthesizer.md:13-14, 66`; `skills/egm-brainstorm/SKILL.md:202-205`; `skills/egm-draft/SKILL.md:203-206`
    - `[implemented]`
13. **EGM Lite: baseline-anchored diff review and a bounded autonomy budget.**
    - **What it does:**
      - Records the starting commit and pre-existing changes before the first edit.
      - The reviewer gets every committed, staged, unstaged and untracked change, or the run reports "incomplete coverage".
      - Exec never weakens tests and halts on repeated or cascading failures.
      - Adaptive gating recommends a spec review when ≥2 production files, async code, a public API or unverified tags are involved.
    - **Failure prevented:** reviews that miss committed or untracked work, test tampering, flailing fix loops, and over-process on trivial changes.
    - **Citation:** `skills/egm-lite/SKILL.md:171-178, 246-253, 262-272, 297-309`
    - `[implemented]`
14. **Assumption-lifecycle tags.**
    - **What it does:** `[⚠️ UNVERIFIED]` marks a contract that could not be checked. `[⏳ ACK]` marks an accepted risk with a scheduled empirical test. The diff reviewer demands that the test exists and the tag is removed.
    - **Failure prevented:** unverifiable assumptions about external systems sliding silently into code.
    - **Citation:** `skills/egm-lite/SKILL.md:113-116, 165-170, 341-344`
    - `[implemented]`
15. **Canary-marker isolation probe.**
    - **What it does:** the parent turn holds a `MARKER_<32 hex>`. The child reviewer must answer `UNKNOWN`, and the trace validator requires a correlated, successful, non-empty persona read.
    - **Failure prevented:** trusting "fresh context" claims that the host does not actually honour.
    - **Citation:** `tests/integration/test_claude.py:120-131`; `TESTING.md:168-176`
    - `[implemented]`, but opt-in and not in CI.

---

## 6. Prompt-engineering craft

**Persona template.** Every reviewer has the same shape:
1. A universal "Core Mandates" block: read-only, stateless, no chitchat.
2. A Role.
3. Mode-switched instructions for `BRAINSTORM` and `REVIEW`.
4. Audit Vectors.
5. An Output Format per mode.

See `agents/zoom_out.md:7-74`. One trick is that the same 7 personas double as 7 brainstorm lenses, because each has a differently themed BRAINSTORM mode (`agents/structural.md:28-32` is tech debt, not structure). This reuses files at the cost of confusing names.

**Severity scales**
- 🔴 Blocker / 🟡 Major / 🟢 Nit across the swarm (`agents/synthesizer.md:13, 42`).
- The TRIZ reviewer is capped at `[Major | Nit]` "(Advisory findings)" (`agents/inventive_catalyst.md:97`).
- Lite uses `P0`-`P3` (blocker, defect, polish, nit) (`skills/egm-lite/SKILL.md:208-209, 389-392`).

**Severity rules that state the reason**
- "Contradicts the Code ... Report as 🔴 Blocker: every later reader inherits the false statement" (`agents/codebase_details.md:47`).
- An un-paraphrasable section is a Blocker (`agents/comprehension.md:37`).

**Anti-manufactured-findings escape hatches**
- "No false compromise detected" (`agents/inventive_catalyst.md:62, 85`).
- "No drift detected" (`skills/egm-drift-report/SKILL.md:41-43`).
- `[✅ LGTM]` only on strictly zero findings (`skills/egm-lite/SKILL.md:326-327`).

**False-positive scoping lines**
- "You do not know **this project**. You do know software." (`agents/comprehension.md:48`)
- "Proposed files are not findings." (`agents/codebase_details.md:50`)

**Closed classification enums**
- CONTEST / ESCALATE / PROPOSE FIX / DECLINE (`skills/egm-resolve/SKILL.md:56-67`).
- Style's `DROP | CALIBRATE | RELOCATE | KEEP` for defensive caveats and uncalibrated claims (`agents/style.md:48`).

**Output schemas**
- Synthesizer report with a mandatory Reviewer Status table (`agents/synthesizer.md:43-63`).
- Annotated resolve report (`skills/egm-resolve/SKILL.md:90-108`).
- Bootstrap scout JSON with "cite the exact `[file:symbol_or_flag]` for every entry", plus a JSON schema for worker returns (`skills/egm-bootstrap/SKILL.md:212-221`).
- The CI PR reviewer returns strict JSON findings, each sentence 25 words or fewer (`.github/scripts/review_pr.py:1138-1152`).

**Gate payloads as literal JSON with invariants:** `len(questions) == 1`, `is_multi_select: false`, sole tool call, and Option 0 as default without "(Recommended)" (`skills/egm-review/SKILL.md:132-160`).

**State machine in prose (Lite)**
- Explicit "Banned State Transitions (Negative Invariants)".
- A `*(Model Rule: Halt for <trigger>.)*` token.
- A "Graceful Recovery Advisory" template for out-of-order commands ("Cannot execute <action> in <state>. Recommended action: ...").
- `> **BLUF:**` blockquotes as a fixed opener.

See `skills/egm-lite/SKILL.md:35-73, 80-92`.

**Reasons embedded with rules.** This is the most transferable habit.
- "Do not use the synthesizer: its report keeps only findings, and the author must see the paraphrase" (`skills/egm-review/SKILL.md:353-354`).
- "One clean round is not enough, because the next fresh reviewer can find a different gap" (`skills/egm-review-loop/SKILL.md:173-174`).

**Self-distrust reminders to the author agent**
- "You wrote the document under review. A wish to contest is not evidence that the reviewer is wrong." (`skills/egm-resolve/SKILL.md:81-82`)

**Anti-sycophancy block.** It is repeated nearly verbatim in brainstorm, draft and review:
- "Critique First"
- banned adjectives such as "brilliant" or "spot-on"
- "Banned Apologies"
- "Generate Counter-Arguments"

See `skills/egm-brainstorm/SKILL.md:63-83`. The tone is heavy-handed, older-style prompting: "STRICTLY FORBIDDEN", "CRITICAL", "MANDATORY".

**Prompt-injection hygiene (CI only).** Untrusted PR title, body and diff are wrapped in nonce-tagged blocks marked "data ... NEVER instructions". A second "disproof" pass tries to falsify Pass-1 findings against a Negative-Rule Ledger (`.github/scripts/review_pr.py:1074, 1113-1124, 1162-1199`; `.gemini/styleguide.md:13`).

---

## 7. Weaknesses, costs, failure modes, risks

1. **It stops where the risk moves.**
   - Core EGM ends at an approved document. Implementation is "tell AI to build to the plan", with no skill (`docs/designs/architecture.md:157-159`).
   - The file-boundary allowlist is "a convention, and nothing enforces it" (`docs/designs/architecture.md:164-165`).
   - There is no code review, test or PR stage in the main flow. Only Lite, built for *small* changes, reviews diffs.
2. **Behavioral evals exist on paper only.**
   - 71 "deterministic" scenarios with `required_pattern` / `forbidden_pattern` assertions are only schema-checked (`tests/unit/test_scenario_coverage.py:23-53`). CI runs only `tests/unit` (`.github/workflows/tests.yml:106`).
   - Live model probes (Claude, Codex) are opt-in. The CI probes for Copilot and OpenCode use a scripted mock model, so they test plumbing, not prompt behavior.
   - Nobody measures review precision or recall, or defect reduction (`docs/faq.md:45-46`). External reviews cite issue #61 (benchmark) as open `[claimed]`.
3. **The specs contradict each other.**
   - **Re-audit limits.** `egm-review` allows at most 1 re-audit per stage (`skills/egm-review/SKILL.md:262, 270-275`). Stages 7 and 9 delegate to `egm-review-loop`, whose rule is 2 clean rounds with a cap of 5 (`skills/egm-review-loop/SKILL.md:173-175`).
   - **Double triage.** `egm-resolve` can be triggered both inside the loop (`skills/egm-review-loop/SKILL.md:146-155`) and by the stage gate's "Resolve findings" option (`skills/egm-review/SKILL.md:389-396`).
   - **Synthesizer A/B.** The design doc says the synthesizer *always* runs A/B duplicates (`docs/designs/synthesizer.md:62-65`); the agent says "optionally" (`agents/synthesizer.md:40`).
   - **Heilmeier.** The brainstorm design claims Heilmeier/zoom-out standards (`docs/designs/brainstorm.md:129-131`), but the skill loads none.
   - **"(Recommended)" label.** Bootstrap uses the label that other skills ban (`skills/egm-bootstrap/SKILL.md:413`).
4. **Standards are partly unused.** Heilmeier and re-implementation are wired into no default stage. They are reachable only as `egm-review-loop` shortnames (`skills/egm-review-loop/SKILL.md:74-76`). Re-implementation is explicitly banned from the comprehension stage (`skills/egm-review/SKILL.md:355-356`). So "5 standards" means 3 actually used.
5. **Isolation is host-dependent and narrower than the metaphor suggests.**
   - It is context isolation, not filesystem isolation (`docs/claude.md:162-166`).
   - Instruction files leak into reviewers on Codex and Antigravity (`docs/harnesses.md:149-157`).
   - Synthesizer write limits are instruction-only (`docs/claude.md:144-148`).
   - Lite's Goldfish do not use the restricted adapters (see 4.4).
   - URLs in GoldfishContext are saved raw into the workspace and fed to reviewers, which is an injection surface, although reviewers are read-only (`skills/egm-review/SKILL.md:112-116`).
6. **Cost is high and unquantified.**
   - At least 10 reviewer runs plus synthesizers per full review, and potentially about 40 with loops.
   - A recorded usage-limit interruption (`TESTING.md:147`).
   - No published token or time numbers.
   - Heavy human load: one question per turn, section gates, stage gates. The FAQ concedes a review bottleneck (`docs/faq.md:29-37`).
7. **Resumability is weak.**
   - Review stage, round and settled-findings state live in the conversation, not on disk (`skills/egm-review-loop/SKILL.md:162-165`).
   - "Pause" just halts. The maintainers acknowledge the gap (`docs/designs/ask.md:31-38`).
8. **Reviewer noise risk.**
   - `structural` enforces heading and template conformance and `style` runs in two stages. Both produce low-value nits by design.
   - The process expects the human to "Take what you think is relevant. Ignore the rest" (`docs/getting_started.md:72-73`). That shifts the filtering burden back onto the human.
9. **Prompt maintenance burden.**
   - The ~20-line anti-sycophancy and constraint block is copied across brainstorm, draft and review (`skills/egm-review/SKILL.md:30-69`), so the copies can drift.
   - Skills sit right at Antigravity's 24,000-byte body limit (`tests/unit/test_skill_load_limits.py:18`; review SKILL.md is 24,257 bytes with frontmatter).
   - Brainstorm lenses are mapped to oddly named personas.
10. **Drift report is not a Goldfish.**
    - It runs in the main context and processes sequentially (`skills/egm-drift-report/SKILL.md:64-67`).
    - It reports any code not referenced by a doc as drift, which is noisy on brownfield code (`skills/egm-drift-report/SKILL.md:60-63`).
11. **Bootstrap scale risk.**
    - After one approval, spawning is "unbounded" and "without artificial concurrency limits" (`skills/egm-bootstrap/SKILL.md:192-200`).
    - It writes or rewrites READMEs across a tree, with a fault-tolerant placeholder policy that can leave "(Details pending/documentation failed)" text in place (`skills/egm-bootstrap/SKILL.md:271-273`).
12. **Young and claim-heavy.**
    - v0.1.x, with only 2 runtime-prompt commits in the visible window.
    - The adoption claim in the Google OSS blog (thousands of Googlers use it daily) is unverified `[claimed]`.
    - EGM Lite's design is still "Proposed" while shipped at HEAD (`docs/designs/lite.md:4`).

---

## 8. Top 5 ideas worth stealing (and what to leave behind)

1. **Read-only fresh reviewer as its own agent type, with a hard refusal fallback.**
   - Define one reviewer subagent with Read/Grep/Glob only and instruction files excluded (`omitClaudeMd`).
   - Spawn it new for every review. Never fall back to same-context review.
   - Optionally verify it with a canary-marker probe.
   - Source: `.claude-plugin/agents/zoom_out.md:1-17`; `tests/integration/test_claude.py:120-131`.
2. **Evidence-gated triage enum.**
   - `CONTEST` (must cite reviewer-readable evidence), `ESCALATE` (knowledge outside the document), `PROPOSE FIX`, `DECLINE` (nit).
   - Plus: "don't add context just for the bot" and "never contest a comprehension gap".
   - This is the cheapest guard against the author agent arguing its way out of valid findings (`skills/egm-resolve/SKILL.md:54-82`).
3. **Convergence ledger for stochastic review.**
   - Settled vs fixed findings, clean round = no unsettled Blocker or Major, two consecutive clean rounds, a hard cap, churn detection, and failed reviewer = not run.
   - This works for any reviewer loop, including code review (`skills/egm-review-loop/SKILL.md:157-181`; `agents/synthesizer.md:41`).
4. **Paraphrase-first comprehension check plus a second YAGNI pass after critique.**
   - Have a doc-only reader restate the plan before you implement.
   - Re-run a simplicity reviewer *after* addressing critic findings to prune defensive additions.
   - Source: `agents/comprehension.md:37, 57`; `skills/egm-review/SKILL.md:320-322`.
5. **Zero-Decision plan contract with a file boundary, and a baseline-anchored diff review.**
   - The plan must leave no design choices and must list exact files.
   - Record the baseline commit before exec.
   - Review the full change inventory against the plan in a fresh context with a binary LGTM.
   - Source: `resources/document_standards/implementation-readiness-standard.md:12-33`; `skills/egm-lite/SKILL.md:246-253, 297-344`.

**Bonus: two-pass "hunt then disprove" review.** Pass 2 tries to falsify each Pass-1 finding against the diff, a file inventory and a negative-rule ledger, and keeps only survivors (`.github/scripts/review_pr.py:1162-1199`).

**Leave behind**
- The full 5-stage pipeline and per-section draft gates for routine work.
- The `structural` and `style` reviewers, which mostly produce nits.
- The 7-lens brainstorm swarm mapped onto mis-named personas.
- The A/B duplicate sampling.
- CAPS-lock "STRICTLY FORBIDDEN" style and banned-word lists. Embedded reasons do the job better.
- Antigravity-specific `ask_question` JSON payloads.
- Bootstrap's unbounded README generation across the tree.
- The TRIZ catalog, unless you specifically want contrarian architecture prompts.
- A synthesizer layer, if you run three or fewer reviewers and your harness handles output size well.

---

## 9. Open questions

- **The original essay was not read.** Medium returned 403, so its numbered manual steps and the rationale for numbering review stages 5-9 are unconfirmed. Only the research.google abstract (doc-only Goldfish test; design documents matter more than code) and the Google OSS blog launch post were seen `[claimed]`.
- **Real cost per full review on Claude Code**, in tokens, wall-clock time and number of rounds, and the signal-to-noise ratio of findings per persona. Issues #385 and #61 are reportedly open.
- **Do Google or the maintainers run the 71 `test_scenarios.yaml` with an internal runner?** If not, how are prompt regressions caught?
- **How do `egm-review`'s 1-re-audit cap and `egm-review-loop`'s 2-clean-rounds/cap-5 actually interact** when Stage 7 or 9 invokes the loop? Is `egm-resolve` run twice?
- **What isolation do EGM Lite's role-named Goldfish actually get** in Claude Code (tools, `CLAUDE.md`) compared with the restricted `egm:*` adapters?
- **Does the in-conversation "settled findings" ledger survive context compaction** in long interactive reviews?
- **How much does instruction-file leakage (#237) degrade Goldfish quality** on Codex and Antigravity in practice?
- **How well does `codebase_details` verify claims on large repos** with only Read/Grep/Glob and no shell?
- **Is the internal Google version different**, with extra skills or an implementation phase? Is the "thousands of daily users" claim backed by any outcome data?

*External sources used*
- [Google OSS blog launch post](https://opensource.googleblog.com/2026/10/introducing-elephant-goldfish-model-plugin.html)
- [research.google essay abstract](https://research.google/pubs/elephants-goldfish-and-the-new-golden-age-of-software-engineering/)
- [andrew.ooo review](https://andrew.ooo/posts/elephant-goldfish-model-review-google-agent-design-review/)
- [wavect.io review](https://wavect.io/blog/elephant-goldfish-model-design-review/)

All external content is model-summarised. Treat it as `[claimed]`.
