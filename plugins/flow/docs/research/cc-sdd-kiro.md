# cc-sdd (Kiro-style SDD for Claude Code): planning and spec stages

2026-11-18. Scope: stages before implementation only. Rubric: `research/planning-rubric.md`.

**Path short forms used below.** All paths are inside the cc-sdd repo.

- `S/` = `tools/cc-sdd/templates/agents/claude-code-skills/skills/`
- `R/` = `tools/cc-sdd/templates/shared/settings/rules/` (the installer copies each rule into the `rules/` folder of each skill that declares it)
- `T/` = `tools/cc-sdd/templates/shared/settings/templates/`
- `G/` = `docs/guides/`

**Evidence tags.** `[implemented]` = in a prompt or code. `[claimed]` = in docs only. `[secondary]` = third party.

## 1. Identity

| Item | Value |
|---|---|
| Repo | https://github.com/gotalab/cc-sdd |
| Commit read | `e2a0c671aef37a482404905b409ab5c27092b25b` (HEAD of `main`, 2026-09-23), package v3.1.0 (`tools/cc-sdd/package.json`) |
| Licence | MIT (`LICENSE:1`) |
| Stars / forks | 3,771 / 285 (GitHub API, 2026-11-18). One blog says "about 12K" in April 2026 [secondary]. The API figure contradicts it. |
| Last push | `pushed_at` 2026-10-22. Last release v3.1.0 on 2026-09-23. |
| npm downloads | 67,417 in the last 30 days (npm API). |
| Maintenance | Active. One main author: 325 commits. The next contributor has 9. 16 open issues and PRs. Single-maintainer risk. |
| Variant scored | `claude-code-skills`. It is the default agent (`tools/cc-sdd/src/cli/agents.ts:23`). The legacy `claude-code-agent` variant (commands plus static subagents) is noted where it differs. |

## 2. Stages before implementation

The minimal workflow is in `tools/cc-sdd/templates/agents/claude-code-skills/docs/CLAUDE.md:23-40`. All files go to `.kiro/specs/<feature>/`.

| Stage | Input | Output | Subagents | Human gate |
|---|---|---|---|---|
| Steering (optional) | Codebase | `.kiro/steering/product.md`, `tech.md`, `structure.md` | None (`S/kiro-steering/SKILL.md:4`) | No explicit gate. Sync mode "Propose[s] updates" (`:80`). |
| `/kiro-discovery` | Idea text | Path A–E. `brief.md` (C), plus `roadmap.md` (D/E) | Codebase explorer, web researcher, viability checker (`S/kiro-discovery/SKILL.md:67-71,101,105`) | Confirms the path (`:56`). The user picks an approach (`:103-105`). |
| `/kiro-spec-init` | Description or `brief.md` | `spec.json`, `requirements.md` stub (`S/kiro-spec-init/SKILL.md:19-27`) | None | Questions until who / current state / change are known (`:16`) |
| `/kiro-spec-requirements` | Stub, brief, steering | `requirements.md` (EARS) | Optional codebase, domain and steering scans (`S/kiro-spec-requirements/SKILL.md:37-48`) | Stops on real ambiguity (`:68`). Asks the user to approve or modify (`:108,127-135`). |
| `/kiro-validate-gap` (optional) | `requirements.md` | Appends to `research.md` (`S/kiro-validate-gap/SKILL.md:58-64`) | None. `allowed-tools` has no `Agent` (`:4`). | None. Warns if requirements are unapproved (`:95`). |
| `/kiro-spec-design [-y]` | Requirements, `research.md` | `research.md`, `design.md` (`S/kiro-spec-design/SKILL.md:89-130`) | Optional codebase and web research (`:68-79`). Synthesis must stay in main context (`:102`). | Stops if requirements are unapproved, unless `-y` (`:36-38,169-172`) |
| `/kiro-validate-design` (optional) | Requirements, design | GO/NO-GO in chat. No file. | None. `allowed-tools` has no `Agent` (`S/kiro-validate-design/SKILL.md:4`). | Interactive dialogue (`:48`) |
| `/kiro-spec-tasks [-y]` | Requirements, design | `tasks.md` (`S/kiro-spec-tasks/SKILL.md:107-113`) | One fresh task-graph reviewer, if the host supports it (`:84-101`) | "Approve and proceed?" (`:121-129`) |
| `/kiro-spec-quick [--auto]` | Description | All of the above, without gap or design validation | Final sanity reviewer, if available (`S/kiro-spec-quick/SKILL.md:147-158`) | A yes/no after each phase, or none with `--auto` (`:97-131`) |
| `/kiro-spec-batch` | `roadmap.md` plus briefs | Full specs per feature | One subagent per feature per dependency wave, plus a cross-spec reviewer (`S/kiro-spec-batch/SKILL.md:57-125`) | None until the end |

**Approval mechanics are inconsistent [implemented].**

- No skill sets `approvals.requirements.approved` before the design stop-check. Design sets it only after the check (`S/kiro-spec-design/SKILL.md:36-38,136`). Tasks sets it again (`S/kiro-spec-tasks/SKILL.md:112-113`).
- So the user approves requirements and design by passing `-y`, which the skill itself suggests (`S/kiro-spec-design/SKILL.md:172`), or by editing `spec.json`. Running the next command without `-y` stops.
- The docs say "Approve by running: /kiro:spec-design" (`G/command-reference.md:365`). That conflicts with the stop rule in the skill (`S/kiro-spec-design/SKILL.md:169-172`).
- `ready_for_implementation` (`T/specs/init.json:21`) is never written in skills mode.
- Only the tasks phase has an explicit approval prompt.

The legacy variant has no discovery command. Its validators run as static subagents (`tools/cc-sdd/templates/agents/claude-code-agent/agents/validate-design.md:1-6`).

## 3. Questions

- **Discovery asks one question at a time.** "Ask clarifying questions sequentially (not all at once)". There is a fixed list of 7 topics (`S/kiro-discovery/SKILL.md:77-85`). It skips questions that context answers, and it skips them all if the description is clear (`:87`).
- **No default answer is offered per question.** Discovery recommends one of 2–3 approaches (`:92-103`). The individual questions have no recommended answer.
- **spec-init and spec-requirements push for more questions.** spec-init says "Ask as many questions as needed; do not fill in gaps with your own assumptions" (`S/kiro-spec-init/SKILL.md:16`). spec-requirements repeats this (`S/kiro-spec-requirements/SKILL.md:98`). Requirements questions must cover WHAT, not HOW (`:78-95`).
- **validate-design is a dialogue.** It "Engage[s] interactively ... ask clarifying questions, propose alternatives" (`S/kiro-validate-design/SKILL.md:48,59`).
- **Questions can be skipped.** A `brief.md` skips the spec-init questions (`S/kiro-spec-init/SKILL.md:15-16`). `spec-quick` Phase 1 asks nothing (`S/kiro-spec-quick/SKILL.md:52-95`).
- **Unresolved conflict.** `--auto` says "Stop ONLY after the sanity review completes or if error occurs" (`S/kiro-spec-quick/SKILL.md:16-20`). The requirements skill says to stop and ask on ambiguity (`S/kiro-spec-requirements/SKILL.md:68,98`). The prompts do not say which rule wins.

## 4. Research

- **Depth is chosen by the model, not the owner [implemented].** Design sorts the feature into a class (`S/kiro-spec-design/SKILL.md:44-66`):
  - New or complex: full discovery (`R/design-discovery-full.md`).
  - Extension: light discovery (`R/design-discovery-light.md:1-48`, which escalates on risk at `:36-42`).
  - Simple addition: a quick pattern check only.
- **No flag lets the owner pick none / quick / deep.** The only design argument is `-y` (`S/kiro-spec-design/SKILL.md:5`).
- **Subagents return summaries only.** Codebase exploration returns a summary of at most 200 or 150 lines (`S/kiro-discovery/SKILL.md:68`, `S/kiro-spec-requirements/SKILL.md:42`). Raw web results do not enter the main context (`S/kiro-discovery/SKILL.md:101`).
- **Research subagents are not blinded.** The prompt templates name the user's request (`S/kiro-discovery/SKILL.md:68`, `S/kiro-spec-requirements/SKILL.md:42`).
- **One check is blinded to the main context's reasoning.** The task-graph reviewer gets "only file paths, the draft task plan" and reads the source files itself (`S/kiro-spec-tasks/SKILL.md:87`).
- **validate-gap runs inline.** It does codebase and web research in the main context (`S/kiro-validate-gap/SKILL.md:40-47`). It gives "Information over Decisions" (`:67`). A user reported shallow gap analysis before v3, in issue #115 [secondary].

## 5. Plan and spec

**Mapping to the owner's model.**

- `brief.md` (from discovery) and `research.md` are the free-form plan. `brief.md` comes first, as in the owner's model.
- `requirements.md`, the design's boundary sections and File Structure Plan, and the task annotations are the binding contract. The docs call these "the specification, the contract that must be respected". `design.md` internals and task order are "free territory" (`G/why-cc-sdd.md:22-25`).
- The binding contract is split over three files. Part of it (File Structure Plan) sits inside `design.md`, which is otherwise free-form.
- `brief.md` exists only when discovery runs. `spec-init` alone keeps only a "Project Description (Input)" section (`T/specs/requirements-init.md:3-4`).

**Exact headings.**

- `brief.md`: Problem, Current State, Desired Outcome, Approach, Scope, Boundary Candidates, Out of Boundary, Upstream / Downstream, Existing Spec Touchpoints, Constraints (`S/kiro-discovery/SKILL.md:130-164`).
- `requirements.md`: Introduction, Boundary Context (optional), Requirements → "Requirement N", Objective (user story), Acceptance Criteria (`T/specs/requirements.md:1-32`).
- `design.md`: Overview (Goals, Non-Goals), Boundary Commitments (This Spec Owns, Out of Boundary, Allowed Dependencies, Revalidation Triggers), Architecture, File Structure Plan, System Flows, Requirements Traceability, Components and Interfaces, Data Models, Error Handling, Testing Strategy, Optional Sections, Supporting References (`T/specs/design.md:18-329`).
- `research.md`: Summary, Research Log, Architecture Pattern Evaluation, Design Decisions, Risks & Mitigations, References (`T/specs/research.md:12-58`).
- `tasks.md`: `- [ ] N.M (P)` items with detail bullets, `_Boundary:_`, `_Depends:_`, `_Requirements:_` (`T/specs/tasks.md:1-24`).

**Length.**

- The design template is 332 lines. It warns at about 1,000 lines (`T/specs/design.md:12`).
- Chat summaries are capped at 200–300 words (`S/kiro-spec-design/SKILL.md:161`, `S/kiro-spec-requirements/SKILL.md:113`).
- A doc example shows 87 acceptance criteria for one OAuth feature (`G/command-reference.md:359`) [claimed].

## 6. Definition of done

There are two levels of definition of done [implemented].

1. **EARS acceptance criteria per requirement.** The patterns are When / While / If / Where / ubiquitous "the [system] shall" (`R/ears-format.md:10-39`). Each criterion must be "testable, verifiable, and describe a single behavior" (`:47`).
2. **An observable completion bullet per sub-task.** Each executable sub-task needs one detail bullet that says "What will be true when this task is done?" (`R/tasks-generation.md:91-97`). It also carries `_Requirements:` IDs (`:84-89`).

**Checks before build.**

- Mechanical checks: numeric IDs, at least one EARS criterion per requirement, no technology terms (`R/requirements-review-gate.md:39-44`).
- Traceability checks: every requirement ID appears in the design and in at least one task (`R/design-review-gate.md:38-39`, `R/tasks-generation.md:116-118`).

**Checks during build** (outside scope): a fresh reviewer checks each task against its criteria (`S/kiro-review/SKILL.md:101-106`).

There is no single "Done when" section. The definition of done is spread across `requirements.md` and `tasks.md`.

## 7. Validation before build

| Check | Who | Fresh context? | Rounds |
|---|---|---|---|
| Requirements Review Gate | Same agent, self-review | No (`S/kiro-spec-requirements/SKILL.md:63-68`) | ≤2 repair passes |
| Design Review Gate: coverage, architecture, boundary and executability readiness, mechanical checks | Same agent | No (`S/kiro-spec-design/SKILL.md:118-124`; `R/design-review-gate.md:1-50`) | ≤2 |
| Task Plan Review Gate | Same agent | No (`S/kiro-spec-tasks/SKILL.md:65-80`) | ≤2 |
| Task-graph sanity review: verdict PASS / NEEDS_FIXES / RETURN_TO_DESIGN | Fresh subagent "if ... available", else inline. Mode is reported. | Yes, conditional (`S/kiro-spec-tasks/SKILL.md:84-101`) | 1 fix, then stop |
| `/kiro-validate-design`: ≤3 critical issues, GO/NO-GO | Main context, uses conversation history | No (`S/kiro-validate-design/SKILL.md:45,58`; `R/design-review.md:49-65`) | Manual |
| `spec-quick` final sanity review | Fresh subagent preferred | Conditional (`S/kiro-spec-quick/SKILL.md:149-158`) | 1 |
| `spec-batch` cross-spec review (10 checks) | Fresh subagent | Yes (`S/kiro-spec-batch/SKILL.md:84-125`) | ≤3 |

**What the optional validators check.**

- `validate-gap` outputs a requirement-to-asset map with gaps tagged Missing / Unknown / Constraint. It also gives options A/B/C (extend / new / hybrid), effort S–XL, risk, and research items for design (`R/gap-analysis.md:129-136`). It does not judge the spec. It informs design.
- `validate-design` uses four criteria: architecture alignment, consistency and standards, extensibility and maintainability, type safety and interfaces (`R/design-review.md:20-42`). These measure architecture quality. They do not ask whether an implementer can use the spec.
- In the legacy `claude-code-agent` variant, both validators run through the Task tool as subagents (`tools/cc-sdd/templates/agents/claude-code-agent/commands/validate-design.md:19-23`).

**Gaps.**

- No fresh validator checks `requirements.md` or `design.md` on their own.
- Nothing asks the question "can an implementer use this without guessing?" in fresh context. Only the design gate's "without guessing ownership" comes near (`R/design-review-gate.md:14`), and that check is inline.
- Issue #190 reports that widening the scope after task generation re-runs no validation [secondary]. The reporter says they used cc-sdd for about 40 specs.

## 8. Decisions

- **Discovery** records the chosen approach. For Path D/E, the roadmap has "Approach Decision", with Chosen, Why and Rejected alternatives (`S/kiro-discovery/SKILL.md:181-184`).
- **Design** records decisions in `research.md`. Each decision is one subsection with Context, Alternatives Considered, Selected Approach, Rationale, Trade-offs and Follow-up (`T/specs/research.md:38-51`).
- **No field records who made the decision**, the AI or the owner.
- **The owner never sees all decisions in one table.**
- **No rule separates critical decisions from routine ones.**
- **Recommendations:**
  - Discovery recommends one approach (`S/kiro-discovery/SKILL.md:103`).
  - Gap analysis must not decide (`R/gap-analysis.md:140`).
  - validate-design proposes alternatives in a dialogue (`R/design-review.md:87-88`).

## 9. State and trackers

- **Local files are the source of continuity.** "Files on disk are the source of continuity" (`S/kiro-discovery/SKILL.md:253`).
- **Phase state lives in `spec.json`.** It holds the phase and an approvals object (`T/specs/init.json:1-22`).
- **Resume points exist.** `roadmap.md` supports re-entry (`S/kiro-discovery/SKILL.md:229-262`). `/kiro-spec-status` reports phase, approvals and next actions (`S/kiro-spec-status/SKILL.md:19-52`).
- **No tracker integration exists.** A search of the whole repo finds only:
  - "Add JIRA fields" to templates (`G/customization-guide.md:34`) [claimed].
  - A GitHub Action that closes stale issues on the cc-sdd repo itself (`CHANGELOG.md:218`).
- **Doc drift.** The customization guide says to edit rules in `.kiro/settings/rules/` (`G/customization-guide.md:40`). In skills mode the installer copies each rule into the `rules/` folder of the skill that declares it (`tools/cc-sdd/src/plan/fileOperations.ts:163-219`). The skills manifest installs only `settings/templates` (`tools/cc-sdd/templates/manifests/claude-code-skills.json:23-31`). So the doc claim does not hold in skills mode. The commands-mode manifest was not checked.

## 10. Sizing

- **Discovery routes work into one of five paths** (`S/kiro-discovery/SKILL.md:34-57`):
  - A: extend an existing spec.
  - B: "No spec needed". Fix directly. The workflow ends.
  - C: one new spec.
  - D/E: several specs.
- **No light spec exists between B and C.** A small task either gets no spec and no definition of done, or the full set of three documents.
- **`spec-quick` saves approval steps, not size.** It runs all phases with the same templates (`S/kiro-spec-quick/SKILL.md:105-145`).
- **Design discovery scales with size** (§4).
- **The docs advise against small work.** "Solo work that fits in a single agent session" does not need cc-sdd (`G/why-cc-sdd.md:62-68`) [claimed].
- **Kiro has more options.** It has Quick Spec, a separate `bugfix.md` spec type, and Requirements-First or Design-First variants (https://kiro.dev/docs/specs/) [claimed]. A cc-sdd user asked for a bug-fix flow (issue #165). The maintainer agreed that a full spec "is too heavy for most bug fixes" [secondary].

## 11. Evidence it works

- **[implemented]** The 40 test files in `tools/cc-sdd/test/` test the installer only: manifests, CLI and paths. No eval tests prompt behaviour or spec quality.
- **[claimed]** The README says existing Kiro specs "remain compatible" (`README.md:15`).
- **[secondary]** Issue #190: the reporter used cc-sdd for "over 40 specs over the last two months". They report that validation drifts after the scope widens.
- **[secondary]** Issue #115 (Dec 2025, before v3) reports that `validate-gap` is shallow.
- **[secondary]** A comparison of SDD tools for Codex says cc-sdd's strength is its built-in validators. Its weakness is "17 skills" of schema bloat (danielvaughan.com, 2026-04-27).
- **[secondary]** Böckeler (martinfowler.com, Oct 2025) writes about Kiro, not cc-sdd. In her test, Kiro turned a small bug into 4 user stories with 16 acceptance criteria, "like using a sledgehammer to crack a nut". cc-sdd copies this flow, so the same risk applies.
- **[claimed]** Kiro's own docs list "Analyze Requirements", a check for inconsistency, ambiguity and gaps before design. cc-sdd has no such check as a separate step. It is folded into the inline review gate.

## 12. Fit score

| ID | Fit | Reason | Citation |
|---|---|---|---|
| Q1 | fits | Accepts any free-text idea or description. No skill rejects short or long input. Short goals cause questions (scored in Q2). | `S/kiro-discovery/SKILL.md:6`; `S/kiro-spec-init/SKILL.md:5,12` |
| Q2 | partly | Skips questions that context answers. Prompts also say "ask as many questions as needed". | `S/kiro-discovery/SKILL.md:87`; `S/kiro-spec-requirements/SKILL.md:98` |
| Q3 | partly | Depth scales automatically. The owner cannot choose it. | `S/kiro-spec-design/SKILL.md:44-66` |
| Q4 | partly | Chat summaries are short. The documents are long, and the owner must review them at the gates. | `S/kiro-spec-design/SKILL.md:161`; `T/specs/design.md:12` |
| Q5 | partly | A binding contract exists with EARS criteria and completion bullets. It is split over three files. There is no single DoD section. | `G/why-cc-sdd.md:22-25`; `R/tasks-generation.md:91-97` |
| Q6 | partly | In the default variant, single specs are written in the main context. Subagents write specs in `spec-batch` and in the legacy variant. | `S/kiro-spec-design/SKILL.md:102`; `S/kiro-spec-batch/SKILL.md:57-74`; `G/claude-subagents.md:30-35` |
| Q7 | partly | Fresh reviewers check the task graph, quick-spec coherence and cross-spec consistency, all only "if available". None validates requirements or design content. | `S/kiro-spec-tasks/SKILL.md:86`; `S/kiro-spec-quick/SKILL.md:152` |
| Q8 | no | One question at a time. validate-design is a dialogue. There is no decision table. | `S/kiro-discovery/SKILL.md:77`; `S/kiro-validate-design/SKILL.md:48` |
| Q9 | partly | Recommends one approach. Has no rule for critical decisions. | `S/kiro-discovery/SKILL.md:103` |
| Q10 | partly | Local files are the source of truth. There is no tracker mirror. | `S/kiro-discovery/SKILL.md:253`; `G/customization-guide.md:34` |
| Q11 | partly | Routes A–E. A small task gets no spec or the full spec. No middle path. | `S/kiro-discovery/SKILL.md:34-57`; `G/why-cc-sdd.md:62-68` |
| Q12 | fits | Default install is Claude Code skills with `Agent` and `AskUserQuestion`. | `tools/cc-sdd/src/cli/agents.ts:23`; `S/kiro-discovery/SKILL.md:5` |

## 13. Tailoring cost

**Change (largest cost first).**

1. **Replace the question and approval model (Q2, Q8, Q9).**
   - Rewrite the questioning in discovery, spec-init, requirements and validate-design. Collect all open points into ONE table. Mark each row "AI decided (reason)" or "owner decides". Show recommended defaults. Show no recommendation on critical rows.
   - Remove the "ask as many questions as needed" rules.
   - Fix the approval mechanics. Add one explicit approve step that sets `spec.json`. Remove the circular stop on unapproved requirements.
   - This touches about 6 skills.
2. **Add an always-on fresh spec validator, and move spec writing to subagents (Q6, Q7, Q4).**
   - Generalise the task-graph reviewer pattern (`S/kiro-spec-tasks/SKILL.md:84-101`) into one mandatory subagent. It reads requirements, design and tasks from disk. It answers "correct?" and "usable without guessing?". Make it run always, not "if available".
   - Have subagents write requirements, design and tasks. The legacy variant already has such subagent definitions to port (`G/claude-subagents.md:30-35`). The main context shows only a short summary plus the decision table.
3. **Add right-sizing and owner-chosen depth (Q3, Q11, Q5).**
   - Add a light path between Path B and Path C: one short spec file with EARS criteria and a "Done when" list.
   - Add a depth flag: none / quick / deep.
   - Always write a short plan (`brief.md`), also when discovery is skipped. Put the binding parts into one spec file with one "Done when" section.
   - Cut the 332-line design template down for medium tasks.

**Smaller costs.**

- Write a tracker-mirror connector skill (Q10).
- Re-run validation when the scope widens (issue #190).

**Keep as is.**

- The EARS rules (`R/ears-format.md`).
- The mechanical checks in the requirements and design gates (`R/requirements-review-gate.md:39-44`, `R/design-review-gate.md:36-43`).
- The boundary vocabulary: Boundary Candidates, Boundary Commitments, `_Boundary:_`.
- The requirement → design → task ID traceability.
- The observable-completion rule for tasks (`R/tasks-generation.md:91-97`).
- The task-graph reviewer: blinded inputs, a verdict enum, bounded rounds.
- Discovery's A–E routing and the `brief.md` format.
- The decision format in `research.md`.
- File-based state in `.kiro/specs/` with `spec.json`.
- The MIT licence, which permits a fork.
