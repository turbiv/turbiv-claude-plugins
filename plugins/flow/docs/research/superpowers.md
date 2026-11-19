# Superpowers (obra/superpowers) — workflow analysis

- **Source analysed:** GitHub HEAD = v7.0.2 (commit `22f0b46`, 2026-11-03). This is the same as the installed copy: `diff -rq` of `skills/` and `hooks/` against `~/.claude/plugins/cache/superpowers-marketplace/superpowers/7.0.2` showed no differences.
- **Citations:** `path:line`, relative to the repo root.
- **Tags:**
  - **[implemented]** The behaviour is in HEAD skill text, a hook, a script, or a test. Where code or a test enforces it mechanically rather than prose, the tag adds *(script)* or *(test)*.
  - **[claimed]** Only the README, release notes, design docs, blog posts or eval results say so. Every eval number is [claimed]: the behavioural evals live in a separate repo (`superpowers-evals`) that this analysis did not read, and some eval records are kept outside the repo (`docs/testing.md:21`).
  - **Default:** an untagged statement that cites a HEAD file under `skills/`, `hooks/` or `tests/` is [implemented]. An untagged statement that cites `RELEASE-NOTES.md`, `docs/`, the README, or a web source is [claimed].
- **Design docs are history, not current behaviour.** Several specs describe designs that HEAD has since changed. Those are called out where relevant.
- **Web material** (§4.7, §7) is secondhand: small-model summaries of partially read pages. It is paraphrased, never quoted.

---

## 1. TL;DR

- **What:** a 15-skill library plus a SessionStart hook that makes the agent invoke a matching skill before *any* response, on 15+ harnesses (`hooks/session-start:49`, `skills/using-superpowers/SKILL.md:10-20`).
- **Philosophy:** skills are behaviour-shaping code written test-first against pressure scenarios (`skills/writing-skills/SKILL.md:10-16`, `AGENTS.md:99-106`); evidence before claims; TDD always.
- **Human role:** the human owns intent, design approval and integration; the agent runs the plan unattended.
- **Lifecycle:** idea → design doc → plan → worktree → per-task subagent build and review (or inline "Native") → branch review → merge/PR menu.
- **Gaps:** no project retro or learning loop; `diagnosing-superpowers` only diagnoses the plugin itself.
- **Standout:** an unusually honest eval loop: dead experiments are recorded and claims are narrowed when evals fail.

## 2. Inventory

**Entry points**
- **SessionStart hook** (`hooks/hooks.json:3-15`). Fires on `startup|clear|compact` (`hooks/hooks.json:5`) and runs `hooks/session-start`. The hook inlines the full `skills/using-superpowers/SKILL.md` inside `<EXTREMELY_IMPORTANT>` (`hooks/session-start:49`) and emits it in each harness's JSON dialect (`hooks/session-start:76-88`). [implemented] *(script, tested by `tests/hooks/test-session-start.sh`)*
- **Skill auto-triggering from descriptions.** There are no slash commands any more: `/brainstorm`, `/write-plan` and `/execute-plan` were removed in v5.1.0 (`RELEASE-NOTES.md:436`). [implemented]
- **Per-harness differences:**
  - Codex ships no hook, because "Codex reliably triggers skills on its own" (`RELEASE-NOTES.md:309`).
  - Antigravity bootstraps only through the `using-superpowers` description (`README.md:92-94`).
  - Hermes loses the bootstrap after compaction (`README.md:277-279`).

**Skills (15).** One line each, with SKILL.md word count from `wc -w`:

| Skill | Role | Words |
|---|---|---|
| `using-superpowers` | Bootstrap. The "1% chance → MUST invoke" rule, a red-flags table, skill priority (process skills before implementation skills), and the rule that user instructions beat skills (`skills/using-superpowers/SKILL.md:10-65`). | 492 |
| `brainstorming` | Draws out intent and why. Lays out approaches, writes the design doc, runs a builder-check subagent, then a HARD-GATE: no building before the human approves. Includes an optional browser "visual companion" (`skills/brainstorming/scripts/server.cjs` and others). | 2658 |
| `writing-plans` | Spec → plan with Global Constraints, Review Focus and per-task Interfaces. Ends in a handoff where the human reviews the plan and picks an executor. | 1639 |
| `subagent-driven-development` (SDD) | Controller loop: per task, a fresh implementer, then one task reviewer giving two verdicts, then a scoped fix loop (5-round breaker). Ends with a whole-branch review and a list of rulings. Has 4 helper scripts and 7 `references/`. | 2895 |
| `executing-plans` ("Native") | Inline execution with the same ledger and stop rules as SDD, mechanically gated by `task-start`/`task-done`, and one fresh final reviewer. | 2985 |
| `test-driven-development` | The iron law (no production code without a failing test), the RED/GREEN cycle, a rationalisation table, and `writing-good-tests.md`. | 1475 |
| `systematic-debugging` | Four phases: root cause before fix. After 3 failed fixes, question the architecture. Ships `find-polluter.sh` and technique docs. | 1454 |
| `verification-before-completion` | Gate function: identify, run, read, verify, then claim. | 580 |
| `requesting-code-review` | Generic reviewer dispatch plus `code-reviewer.md`, the template SDD's final review uses. | 425 |
| `receiving-code-review` | Verify before implementing review feedback, push back when it is wrong, no performative agreement. | 913 |
| `dispatching-parallel-agents` | One agent per independent problem domain. | 865 |
| `using-git-worktrees` | Detects existing isolation, asks consent, prefers the harness's native worktree tool, falls back to `git worktree`, then runs a baseline test. | 1069 |
| `finishing-a-development-branch` | Runs tests, presents a fixed merge/PR/keep menu, requires a typed `discard`, cleans up only worktrees it can prove it created. | 1269 |
| `writing-skills` | TDD for skills: pressure scenarios, rationalisation capture, micro-tests, and the "Match the Form to the Failure" table. | 2409 |
| `diagnosing-superpowers` | Transcript forensics: 7 parallel analyst subagents, `path:line`-only findings, a scrubbed bug-report bundle. | 1071 |

**Scripts**
- **SDD helpers** (`skills/subagent-driven-development/scripts/`):
  - `sdd-repo`: picks the repository, like git does.
  - `sdd-workspace`: creates the per-plan, git-ignored directory `.superpowers/sdd/<plan-slug>/`.
  - `task-brief`: extracts one task from the plan into a file.
  - `review-package`: writes the commit list, stat and `-U10` diff to a file, with range guards.
- **executing-plans** `skills/executing-plans/scripts/task-start` / `task-done`: `task-done` writes the ledger line only when the test command passes (`skills/executing-plans/scripts/task-done:42-55`). [implemented] *(script)*

**Tests** (`tests/`) cover plugin infrastructure only:
- hooks;
- skill size under 20,000 bytes (`tests/skill-size/test-skill-size.sh:16`);
- no pressure scenarios shipped inside skill directories (`tests/skill-layout/test-no-dev-files-in-skills.sh`);
- helper invocations must say "by its absolute path" (`tests/sdd-helper-paths/test-sdd-helper-paths.sh:2-12`);
- the SDD workspace (`tests/claude-code/test-sdd-workspace.sh`);
- per-harness manifests.

Skill *behaviour* is tested in the external Quorum eval lab (`docs/testing.md:25-37`). [claimed]

**Chaining** (each skill names the next as a "REQUIRED SUB-SKILL" or a terminal step):

```
SessionStart hook ──> using-superpowers ("1% rule")
                          │
   "build X" ─────────────┼──> brainstorming ──(approach pick, design doc approval: HARD-GATE)
   "fix bug" ──> systematic-debugging                │  builder-check subagent
                                                     v
                                               writing-plans ──(human reviews plan + picks executor)
                                                     │
                          ┌──────────────────────────┴───────────────────────┐
                          v                                                  v
          subagent-driven-development                              executing-plans (Native)
          ├ using-git-worktrees (setup, consent)                   ├ using-git-worktrees
          ├ per task: implementer ─> task reviewer ─> fix loop     ├ per task: TDD + task-done gate
          │    (TDD discipline via plan steps + report evidence)   │
          ├ final whole-branch review (code-reviewer.md)           ├ final fresh reviewer (code-reviewer.md)
          └ "Rulings I made" list                                  └ "Rulings I made" + "Deferred minors"
                          └──────────────────────────┬───────────────────────┘
                                                     v
                                 finishing-a-development-branch ──(human picks merge/PR/keep)

 cross-cutting: test-driven-development, verification-before-completion,
                requesting/receiving-code-review, dispatching-parallel-agents
 meta:          writing-skills (author skills), diagnosing-superpowers (post-mortem)
```

## 3. End-to-end walkthrough

Example request: *"Add CSV export to the widgets page."*

0. **Bootstrap.**
   - At session start the hook injects `using-superpowers` (`hooks/session-start:25-49`).
   - The request is creative work, so the agent must invoke `brainstorming` before even exploring the code (`skills/using-superpowers/SKILL.md:20,30`). [implemented]
1. **Brainstorming** (`skills/brainstorming/SKILL.md`).
   - **Private check.** If everything is in the request ("make the icon cornflower blue"), it just does it (`skills/brainstorming/SKILL.md:17-24`).
   - **Recon before asking.** It reads the code first (`skills/brainstorming/SKILL.md:42-50`).
   - **First message.** About 200 words playing the request back, then one open question about *why*. If the agent started brainstorming on its own (the human did not ask for it), the message ends with an offer to just dive in (`skills/brainstorming/SKILL.md:52-97`).
   - **Conversation.** One question at a time, only when the answer changes what gets built (`skills/brainstorming/SKILL.md:99-108`), with ~200-300-word play-back chunks (`skills/brainstorming/SKILL.md:190-200`).
   - **Human decision 1: pick an approach** from 2-3 options laid out in a message of their own (`skills/brainstorming/SKILL.md:156-167`).
   - **Sizing.** The agent states the size and the human can override (`skills/brainstorming/SKILL.md:209-224`).
   - **Artifact:** `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`, committed (`skills/brainstorming/SKILL.md:245-246`).
   - **Builder check (projects only).** A fresh subagent reads the doc as a builder who cannot talk to the author (`skills/brainstorming/builder-check-prompt.md:7-22`). Its questions are sorted into *answered*, *minor* (the agent's call, marked as such) and *theirs*. The "theirs" pile goes to the human in one round (`skills/brainstorming/SKILL.md:250-267`).
   - **Human decision 2: approve the design doc.** The HARD-GATE blocks code, scaffolding and dependency installs until then (`skills/brainstorming/SKILL.md:269-283`). [implemented]
2. **writing-plans** (`skills/writing-plans/SKILL.md`).
   - **Artifact:** `docs/superpowers/plans/YYYY-MM-DD-<feature>.md` (`skills/writing-plans/SKILL.md:16`). It contains:
     - a header with Goal, Architecture, Tech Stack and a `Spec:` pointer;
     - `## Global Constraints`, copied verbatim from the spec;
     - `## Review Focus`: the 5 likeliest untested input classes, each pinned by a test;
     - tasks, each with Files, Interfaces (consumes/produces) and checkbox RED→GREEN→commit steps (`skills/writing-plans/SKILL.md:52-138`).
   - **What a step contains:** decisions, not code bodies (`skills/writing-plans/SKILL.md:140-161`).
   - **Self-review:** spec coverage, step scan, type consistency, Review Focus, and proportion against the spec (`skills/writing-plans/SKILL.md:163-177`).
   - **Human decision 3: review the plan and choose Subagent-driven or Native.** The agent recommends one with a reason (`skills/writing-plans/SKILL.md:179-204`). [implemented]
3. **using-git-worktrees.** It runs at execution setup, not after design approval as the README says (`skills/writing-plans/SKILL.md:14`, `skills/subagent-driven-development/SKILL.md:103-106`).
   - It detects whether it is already in a worktree (`GIT_DIR != GIT_COMMON`).
   - **Human decision 4: consent to a worktree**, unless a preference is already declared (`skills/using-git-worktrees/SKILL.md:41-45`).
   - It prefers the native `EnterWorktree` tool (`skills/using-git-worktrees/SKILL.md:51-57`), then runs project setup and a baseline test run. A failing baseline means it asks the human (`skills/using-git-worktrees/SKILL.md:121-132`).
4. **subagent-driven-development** (`skills/subagent-driven-development/SKILL.md`). Runs unattended.
   - **Setup:**
     - `sdd-workspace PLAN` creates `.superpowers/sdd/<plan>/` (`skills/subagent-driven-development/SKILL.md:113-118`).
     - The ledger `progress.md` gets the identity line `# SDD ledger — plan: …` (`skills/subagent-driven-development/SKILL.md:122-123`).
     - It reads the plan once, plus the spec (`skills/subagent-driven-development/SKILL.md:130-134`).
     - A pre-flight conflict scan writes a table of task pairs to the ledger (`skills/subagent-driven-development/references/preflight.md:13-22`).
   - **Per task:**
     1. Record BASE.
     2. `task-brief PLAN N` writes the brief file.
     3. Dispatch the implementer with a 5-part recipe on an explicit model (`skills/subagent-driven-development/SKILL.md:198-235`, `implementer-prompt.md`). The implementer writes the code, tests, commits and a report file, and returns one of DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT in under 15 lines (`skills/subagent-driven-development/implementer-prompt.md:128-153`).
     4. `review-package PLAN BASE HEAD` writes the review package.
     5. One task reviewer reads brief, report, package and constraints, and returns a spec ✅/❌/⚠️ verdict plus a quality verdict (`task-reviewer-prompt.md`).
     6. On ❌ or a Critical/Important finding, the fix loop runs: resume the same implementer for rounds 1-3, then a fresh, more capable model for rounds 4-5. Each round gets a scoped re-review. After round 5, the controller adjudicates and records rulings (`skills/subagent-driven-development/references/fix-loop.md`).
     7. A ledger line `Task N: complete (commits a..b, review clean)` (`skills/subagent-driven-development/SKILL.md:307-319`).
   - **No human check-ins.** The controller makes rulings instead of asking. Only four conditions stop it: destructive/irreversible, security-sensitive, outside-worktree side effects, or a hopeless plan (`skills/subagent-driven-development/SKILL.md:17-31`). [implemented]
5. **Final review.**
   - A whole-branch package goes to `code-reviewer.md` on the most capable model, together with the ledger's deferred minors and rulings.
   - One omnibus fix subagent, then one scoped re-review. There is no second fix wave.
   - Before the workspace is deleted, the controller's final message lists **"Rulings I made"**, exhaustive and ordered (`skills/subagent-driven-development/references/final-review.md:6-47`). [implemented]
6. **finishing-a-development-branch.**
   - Runs the full suite; red stops it (`skills/finishing-a-development-branch/SKILL.md:14-26`).
   - Detects whether it is in a worktree and which kind.
   - **Human decision 5:** confirm the base branch if unknown (`skills/finishing-a-development-branch/SKILL.md:46-51`).
   - **Human decision 6:** merge locally, push and open a PR, or keep (`skills/finishing-a-development-branch/SKILL.md:53-82`).
   - A merge re-runs tests on the merged result (`skills/finishing-a-development-branch/SKILL.md:98-104`).
   - Worktree cleanup is provenance-based and never uses `--force` (`skills/finishing-a-development-branch/SKILL.md:169-201`).
   - Discarding work requires the typed word `discard` (`skills/finishing-a-development-branch/SKILL.md:132-146`). [implemented]

**Alternative middle (Native).** `executing-plans` does steps 4-5 inline:
- It loads TDD first (`skills/executing-plans/SKILL.md:150-153`).
- `task-start` / `task-done` gate the ledger on a passing test command (`skills/executing-plans/SKILL.md:171-234`).
- A fresh reviewer runs at the end; the executor fixes Critical/Important findings itself, each by RED→GREEN, with no re-review (`skills/executing-plans/SKILL.md:236-291`). [implemented]

## 4. Rubric

### 4.1 Lifecycle phases covered

| Phase | Coverage | Where |
|---|---|---|
| Idea | Strong | `brainstorming` "First: what do you actually know", why-first questions (`skills/brainstorming/SKILL.md:17-24,114-119`) [implemented] |
| Requirements/spec | Strong | Design doc with intent, goals/non-goals/anti-goals, constraints, approaches, and what is left to the builder (`skills/brainstorming/SKILL.md:229-243`); builder check (`skills/brainstorming/SKILL.md:250-267`) [implemented] |
| Design | Medium | Approaches with trade-offs and a recommendation (`skills/brainstorming/SKILL.md:156-167`). There is no separate architecture artifact; "how" choices live in the design doc. [implemented] |
| Plan | Strong | `writing-plans` header, Interfaces, Review Focus, self-review (`skills/writing-plans/SKILL.md:52-177`) [implemented] |
| Implement | Strong | SDD or Native (`skills/subagent-driven-development/SKILL.md`, `skills/executing-plans/SKILL.md`) [implemented] |
| Test | Strong (discipline) | TDD iron law (`skills/test-driven-development/SKILL.md:31-45`); the project suite defines green (`skills/test-driven-development/SKILL.md:185-193`) [implemented] |
| Review | Strong | Per-task reviewer, scoped re-review, final branch review, receiving-review etiquette [implemented] |
| PR/merge | Medium | Menu, PR via the forge CLI, merge-result test (`skills/finishing-a-development-branch/SKILL.md:53-126`). No CI or PR-feedback loop beyond `receiving-code-review`. [implemented] |
| Retro/learning | Weak (project), Medium (meta) | `diagnosing-superpowers` analyses sessions for *plugin* bug reports and is told not to propose fixes (`skills/diagnosing-superpowers/SKILL.md:96-100`). `writing-skills` is how lessons become skills. There is no per-project lessons file or memory; the transcript-memory system described in the 2025 announcement post as not yet wired together is absent from this repo at HEAD [claimed]. |
| Debugging | Strong (cross-cutting) | `systematic-debugging` (`skills/systematic-debugging/SKILL.md:14-20,191-212`) [implemented] |

### 4.2 Human gates

**Where the human decides**
- **Brainstorming:**
  - answering the why question;
  - picking an approach (`skills/brainstorming/SKILL.md:156-167`);
  - overriding the size call (`skills/brainstorming/SKILL.md:211-212`);
  - answering the builder-check "theirs" pile once (`skills/brainstorming/SKILL.md:263-267`);
  - approving the design doc. This is the HARD-GATE, and "sounds good" to an idea does not count (`skills/brainstorming/SKILL.md:269-283,293`).
  - Opting out of questions ends the skill and its gate (`skills/brainstorming/SKILL.md:88-95,276-279`). [implemented]
- **Plan:** review the saved plan and choose the executor. Approving a scope earlier does not count as approving the plan (`skills/writing-plans/SKILL.md:179-198`, `RELEASE-NOTES.md:174`). [implemented]
- **Workspace:**
  - worktree consent (`skills/using-git-worktrees/SKILL.md:41-45`);
  - whether to proceed past a failing baseline (`skills/using-git-worktrees/SKILL.md:130`);
  - consent before implementing on main/master (`skills/subagent-driven-development/SKILL.md:105-106`). [implemented]
- **Finish:**
  - base-branch confirmation;
  - the merge/PR/keep menu;
  - typed `discard`;
  - what to do with uncommitted files that block worktree removal (`skills/finishing-a-development-branch/SKILL.md:46-82,132-146,177-198`). [implemented]

**What runs unattended:** the entire plan execution.
- SDD forbids "Should I continue?" (`skills/subagent-driven-development/SKILL.md:17`) and turns ambiguities into ledgered `Ruling: <what> — <why> — <cost if wrong>` lines (`skills/subagent-driven-development/SKILL.md:19-25`).
- The human sees the decisions only at the end, in the "Rulings I made" list (`skills/subagent-driven-development/references/final-review.md:35-42`). [implemented]
- This was a deliberate reversal:
  - v6.3.0 notes a session "blocked for almost nine hours" on a question the controller could have decided (`RELEASE-NOTES.md:228`).
  - The July fix-loop spec had routed load-bearing and plan-mandated findings to a human stop (`docs/superpowers/specs/2026-07-15-sdd-fix-loop-redesign-design.md:73-77,91-95`).
  - HEAD has the controller rule on both instead (`skills/subagent-driven-development/references/fix-loop.md:14-19,68-73`).

**How the human decides:** in chat, from a fixed menu (finish), a recommended option (approaches, executor), or by reading a file (design doc, plan). The visual companion is an optional browser channel for visual choices (`skills/brainstorming/SKILL.md:296-316`).

### 4.3 Artifacts & state

| Artifact | Location / format | Lifetime |
|---|---|---|
| Design doc | `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`, committed (`skills/brainstorming/SKILL.md:245-246`) | Permanent |
| Plan | `docs/superpowers/plans/YYYY-MM-DD-<feature>.md`, markdown with `- [ ]` steps and a `Spec:` pointer (`skills/writing-plans/SKILL.md:16,52-90`). A code comment notes the plan is typically left uncommitted in the main checkout (`skills/subagent-driven-development/scripts/sdd-repo:7-9`). | Permanent / user-owned |
| Plan workspace | `.superpowers/sdd/<plan-slug>/`, self-ignoring `.gitignore` (`skills/subagent-driven-development/scripts/sdd-workspace:100-102`) and a `plan-path` ownership marker (`skills/subagent-driven-development/scripts/sdd-workspace:77-98`) | Deleted after a clean final review (`skills/subagent-driven-development/references/final-review.md:44-47`) |
| Ledger | `<workspace>/progress.md`. The first line names the plan. Lines cover pre-flight table, `Ruling:`, `fix round R/5`, `minor (deferred)`, `complete (commits a..b …)`. | Same as workspace |
| Briefs / reports / review packages / test logs | `task-N-brief.md`, `task-N-report.md` (fix reports appended), `review-<base7>..<head7>.diff`, `task-N-tests.log` | Same as workspace |
| Commits | One or more per task. The ledger records the ranges. | Permanent |
| Rulings list | Final chat message, exhaustive (`skills/subagent-driven-development/references/final-review.md:35-42`) | Chat only |
| Diagnosis case/report | `~/.superpowers/diagnosing-superpowers/<session-id>/` (`skills/diagnosing-superpowers/SKILL.md:29-35`) | User-owned |

**Phase handoff is by file path, not pasted text.**
- spec → plan via the `Spec:` header;
- plan → implementer via the brief file;
- implementer → reviewer via the report file and review package;
- "Never make a subagent read the whole plan file" (`skills/subagent-driven-development/SKILL.md:203-215`). [implemented]

**Resumability**
- On resume, the ledger plus `git log` beat recollection (`skills/subagent-driven-development/SKILL.md:108-129`).
- `skills/subagent-driven-development/references/resuming.md:6-12` defines the rules: completed tasks are skipped, a mid-loop task resumes at the next round, and a foreign ledger is left alone.
- The bootstrap is re-injected on `compact` (`hooks/hooks.json:5`).
- SKILL.md files are kept under the 20,000-character cut that Claude Code applies when it re-attaches skills after compaction (`tests/skill-size/test-skill-size.sh:2-8`).
- The fix loop must be re-read "before every round" because memory of it "does not survive compaction" (`skills/subagent-driven-development/SKILL.md:302-305`).
- SDD and Native share the workspace format, so a run can switch executors mid-plan (`skills/executing-plans/SKILL.md:121-123`).
- All of the above is [implemented]; the workspace is *(script + test)*.
- **Caveat:** `git clean -fdx` deletes the ledger (`skills/subagent-driven-development/SKILL.md:127-128`).

### 4.4 Context-isolation strategy

| Seat | Given | Kept away from | Why (cited) |
|---|---|---|---|
| Controller (main session) | The plan once, the spec, the ledger, short status returns | Diffs (written to files), full reports, fixing code itself | Pasted content "stays resident … re-read on every later turn" (`skills/subagent-driven-development/SKILL.md:183-185`); controller fixes "pollute your context and skip review" (`skills/subagent-driven-development/SKILL.md:332`, `skills/subagent-driven-development/references/fix-loop.md:56-57`) |
| Implementer | 1 line of context, brief path, cross-task interfaces, the controller's ambiguity resolutions, report path (`skills/subagent-driven-development/SKILL.md:203-215`) | Session history and prior-task summaries. One real dispatch hit "42k chars of which 99% was pasted history" (`skills/subagent-driven-development/SKILL.md:220-224`). The whole plan. Spawning subagents (`skills/subagent-driven-development/implementer-prompt.md:50-60`). | Fresh context per task. Avoids the duplicate review seats observed when workers spawned reviewers: 9/9 such spawns were duplicates (`docs/superpowers/specs/2026-07-30-codex-efficiency-fixes-design.md:44-48`) [claimed] |
| Task reviewer | Brief, report, review package, verbatim Global Constraints | Session history, the controller's opinions ("do not flag" is a tripwire, `skills/subagent-driven-development/SKILL.md:285-290`), freedom to crawl (`skills/subagent-driven-development/task-reviewer-prompt.md:38-50`), mutating git (`skills/subagent-driven-development/task-reviewer-prompt.md:52-53`) | Earlier per-task reviewers did "branch-review-scale work", costing 4-8× spec reviewers (`docs/superpowers/specs/2026-06-09-sdd-task-scoped-review-dispatch-design.md:7-11`) [claimed] |
| Re-reviewer | Findings list and fix-range diff only | Code the fix did not touch (`skills/subagent-driven-development/re-review-prompt.md:55-62`) | Fresh full re-reviews were "the churn engine" (`docs/superpowers/specs/2026-07-15-sdd-fix-loop-redesign-design.md:40`) |
| Final reviewer | Whole-branch package, plan, spec, Review Focus, ledger rulings and minors, most capable model (`skills/subagent-driven-development/references/final-review.md:6-16`) | Session history (`skills/requesting-code-review/SKILL.md:8`) | The one broad, fresh pair of eyes |
| Builder-check subagent | The design doc only. "You will not be able to talk to the person who wrote it." (`skills/brainstorming/builder-check-prompt.md:7-10`) | The conversation | Tests whether the doc stands alone |
| Diagnosis analysts (7, parallel) | Case file, a common prompt, one dimension prompt | Each other | Findings without `path:line` are discarded (`skills/diagnosing-superpowers/SKILL.md:36-43`) |
| Optional orchestrator (Claude Code only) | A nested mid-tier subagent runs the whole SDD loop one layer down (`skills/using-superpowers/references/claude-code-tools.md:9-29`) | The expensive session model | "About half the cost and wall clock" (`RELEASE-NOTES.md:194`) [claimed] |

- The bootstrap tells dispatched subagents to ignore it (`skills/using-superpowers/SKILL.md:6-8`). [implemented]
- There is no parallel implementation, to avoid conflicts (`skills/subagent-driven-development/SKILL.md:235`). Parallelism is reserved for `dispatching-parallel-agents` (independent debugging domains).

### 4.5 Verification mechanism

**Layers in HEAD**
1. **TDD discipline.**
   - No production code without a watched failing test; code written before its test gets deleted (`skills/test-driven-development/SKILL.md:31-45`).
   - Verify RED fails for the right reason (`skills/test-driven-development/SKILL.md:113-128`).
   - Green means the project's whole suite, with every failure reported by name (`skills/test-driven-development/SKILL.md:185-193`).
   - Plan steps are pre-ordered RED → run → GREEN → run → commit (`skills/writing-plans/SKILL.md:108-137`).
   - [implemented]
2. **Evidence gate before any success claim.** Identify, run, read, verify, then claim; "Agent said success" is insufficient (`skills/verification-before-completion/SKILL.md:22-36,47,100-104`). [implemented]
3. **Per-task review.**
   - Spec ✅/❌, plus ⚠️ "cannot verify from diff", which the controller must resolve (`skills/subagent-driven-development/task-reviewer-prompt.md:94-113`, `skills/subagent-driven-development/references/cannot-verify.md`).
   - A quality verdict with file:line evidence for every finding (`skills/subagent-driven-development/task-reviewer-prompt.md:135-143`).
   - Severity calibration; a plan-mandated defect is still a finding (`skills/subagent-driven-development/task-reviewer-prompt.md:145-159`).
   - The reviewer treats the implementer's report and its rationales as unverified claims (`skills/subagent-driven-development/task-reviewer-prompt.md:64-71`).
   - [implemented]
4. **Fix verification.**
   - The controller confirms the fix report lists covering tests, command and output (`skills/subagent-driven-development/references/fix-loop.md:36-42`).
   - The scoped re-review rules ADDRESSED or NOT ADDRESSED; "'Attempted' is not addressed" (`skills/subagent-driven-development/re-review-prompt.md:80-90`).
   - [implemented]
5. **Final branch review.**
   - Reviewers apply a "reasonable person" standard where the spec is silent, and list a "Declined to judge" set that the executor must rule on (`skills/requesting-code-review/code-reviewer.md:33-48`).
   - Plus the plan's Review Focus list (`skills/writing-plans/SKILL.md:77-87`).
   - [implemented]
6. **Mechanical gates.**
   - `task-done` refuses to record a task whose tests fail (`skills/executing-plans/scripts/task-done:42-55`) *(script)*.
   - `review-package` rejects empty or non-descendant ranges (`skills/subagent-driven-development/scripts/review-package:38-41`) *(script)*.
   - `finishing` re-runs the full suite and re-tests the merged result (`skills/finishing-a-development-branch/SKILL.md:14-26,98-104`).
   - [implemented]
7. **Spec verification before any code:** the builder check (`skills/brainstorming/SKILL.md:250-267`). [implemented]

**Gap.** In SDD, per-task test execution is *self-reported*.
- The implementer runs the tests and writes the evidence (`skills/subagent-driven-development/implementer-prompt.md:130-135`).
- The reviewer is told not to re-run the suite (`skills/subagent-driven-development/task-reviewer-prompt.md:73-82`), and the controller is told not to ask it to (`skills/subagent-driven-development/SKILL.md:283-284`).
- The controller only checks that the evidence is *present* (`skills/subagent-driven-development/references/fix-loop.md:36-42`).
- The first independent full-suite run is `finishing` Step 1. The final reviewer template asks "All tests passing?" (`skills/requesting-code-review/code-reviewer.md:87`) without telling it to run anything.
- Native mode is mechanically stronger here, through `task-done`.
- The implementer prompt does not load the TDD skill; it says "following TDD if task says to" (`skills/subagent-driven-development/implementer-prompt.md:36`). Native requires loading it (`skills/executing-plans/SKILL.md:150-153`). A 2025 plan already flagged "Skills Not Being Read" by subagents (`docs/plans/2025-11-28-skills-improvements-from-user-feedback.md:170-181`).

### 4.6 Evidence of iteration / quality

**In-repo artifacts**
- 22 design specs and 4 older plans.
- A 1,600-line release-notes file that cites issues and numbers for most changes.
- Infrastructure tests, including the test-enforced structural lessons in §2.

**Methodology visible in the specs** [claimed]
- **Pre-registered gates, N=5 batteries and a "judgment guardrail".** Cheapen mechanics, never judgment (`docs/superpowers/specs/2026-06-10-strict-cost-sdd-design.md:3-11,25-52`).
- **Negative results kept.**
  - A Sonnet controller "DIED AT THE GATES": a planted defect shipped in 4/5 runs (`docs/superpowers/specs/2026-06-10-strict-cost-sdd-design.md:121-133`).
  - Haiku reviewers were "DEAD": they flagged 0 of 10 planted defects at correct severity and failed "by *advocating* for defects" (`docs/superpowers/specs/2026-06-10-strict-cost-sdd-design.md:205-212`).
- **Claims narrowed when the hypothesis failed.**
  - The plan-scoped-workspace RED baseline did *not* reproduce. 25/25 controllers refused to adopt a stale ledger, so the change shipped on structural grounds plus regression safety only (`docs/superpowers/specs/2026-07-06-sdd-plan-scoped-workspace-eval-results.md:45-56,77-83`).
  - The writing-plans placeholder experiment found no problem (40/40 clean), and the follow-up PR was cancelled (`docs/superpowers/specs/2026-06-10-positive-instruction-redesign-design.md:146-158`).
- **Micro-test harness with a no-guidance control.** One API call per sample, 5+ reps, every match read by hand, about $0.15-0.30 per sample (`docs/superpowers/specs/2026-06-10-positive-instruction-redesign-design.md:125-144`).

**Lessons learned, each tied to a failure** [claimed unless noted]
- **The Description Trap.** A workflow summary in a skill's description made agents follow the summary and skip the body: one review instead of two (`RELEASE-NOTES.md:1084`; `skills/writing-skills/references/discovery.md:63-71`). The fix is that descriptions are trigger-only [implemented].
- **Compaction.** Skills cut at 20k characters lost the 5-round cap, and one task ran 18 fix rounds (`RELEASE-NOTES.md:78`). The fix: content moved to `references/` plus a size test [implemented] *(test)*.
- **Lost place after compaction.** Controllers re-dispatched completed work, "269 dispatches for ~22 tasks" (`docs/superpowers/specs/2026-06-09-sdd-task-scoped-review-dispatch-design.md:91-93`). The fix is the ledger [implemented].
- **Controllers coached reviewers.** They told reviewers what to skip, and the flaw shipped (`RELEASE-NOTES.md:364`). The fix is the pre-judging tripwire [implemented].
- **Omitted model.** Without a model, a dispatch inherits the top tier: "all 26 of its reviewers" ran on it (`RELEASE-NOTES.md:363`). The fix is a REQUIRED model slot [implemented].
- **Reviewer mutated git.** A reviewer's `git checkout` orphaned commits (`RELEASE-NOTES.md:365`). The fix is the read-only rule [implemented].
- **A version-floor constraint never reached reviewers** (`go 1.26.1`, `docs/superpowers/specs/2026-06-10-strict-cost-sdd-design.md:97-103`). The fix is the Global Constraints block [implemented].
- **Only the touched test file was run** in 11 of 12 probe runs (`RELEASE-NOTES.md:188`). The fix is the full-suite rule [implemented].
- **Plans turned into code.** Frontier models tried to implement the project while planning (`RELEASE-NOTES.md:141`). The fix is "A plan records decisions" plus the proportion check [implemented].
- **Deleting a TDD rebuttal section hurt test-first behaviour**: 8/10 → 5/10 (`RELEASE-NOTES.md:267`). The arguments were moved into rationalisation rows.
- **Approval ritual drift.** Brainstorming skipped the design doc without asking in 24/24 runs; after the fix, 3/24 (`RELEASE-NOTES.md:70`).
- **Executor stub did nothing.** The old executing-plans "measured the same as running with no plugin at all" (`RELEASE-NOTES.md:169`).
- **Accidental keyword.** One bullet held a Claude Code keyword that forced every session into extended thinking (`RELEASE-NOTES.md:415`).
- **Agents obeyed test scenarios.** Pressure scenarios installed inside skill directories were read as live instructions (`RELEASE-NOTES.md:53`). The fix is a layout test [implemented] *(test)*.

**Reversals visible across docs** (read specs as history)
- "Full re-reviews stay" (`docs/superpowers/specs/2026-06-09-sdd-task-scoped-review-dispatch-design.md:30`) and "scoped re-reviews: vetoed" (`docs/superpowers/specs/2026-06-10-strict-cost-sdd-design.md:240-241`) became the scoped `re-review-prompt.md` (`docs/superpowers/specs/2026-07-15-sdd-fix-loop-redesign-design.md:40`).
- The two separate spec and quality reviewers (`RELEASE-NOTES.md:1028-1036`) were merged into one reviewer with two verdicts (`RELEASE-NOTES.md:344`).
- Brainstorming went from a heavy flow, to a three-path router (`RELEASE-NOTES.md:224`), to a ground-up rebuild in v7.0.0 (`RELEASE-NOTES.md:93`), then two retunes in v7.0.1 and v7.0.2, about four weeks in all (2026-10-09 to 2026-11-03; `RELEASE-NOTES.md:3-13,59-70`).
- Strict-cost rungs L1.2 (auto-append constraints in `task-brief`) and L1.4 (planner-recommended model tier) are *not* in HEAD: `skills/subagent-driven-development/scripts/task-brief` only extracts task text, and the controller still pastes constraints (`skills/subagent-driven-development/SKILL.md:274-280`).

### 4.7 Cost & friction

**Bootstrap**
- **Direct cost.** 3,192 bytes / 492 words of `using-superpowers` plus a wrapper, injected on every `startup`, `clear` and `compact` (`hooks/hooks.json:5`). Estimate: about 0.8-0.9k tokens per injection (bytes/4), plus the harness's skill-description list (all 15 descriptions are about 2.5 KB). Size: [implemented]. The token figure is an estimate.
- **Induced cost.** "Even a 1% chance" → "ABSOLUTELY MUST invoke", even for "a simple question" (`skills/using-superpowers/SKILL.md:11,39`). Each invoked skill is about 3-20 KB (brainstorming 15 KB, SDD 19.7 KB), roughly 1-5k tokens per load (estimate).
- The bootstrap breaks the project's own budget of "<150 words" for getting-started workflows and "<200 words total" for frequently loaded skills (`skills/writing-skills/references/discovery.md:130-133`).

**Plan execution** [claimed]
- **SDD cost profile:** about $13 per run on the go-fractals benchmark. The controller is about half of that ($6-7; ~150 turns, 46% of them thinking or narration with no tool call). Implementers cost $5-6 and reviewers $1-1.5. Each extra task costs about $0.60-1.00 in fixed dispatch-plus-review overhead (`docs/superpowers/specs/2026-06-10-strict-cost-sdd-design.md:13-23,89-92`).
- **Variance driver:** review-loop count, mostly caused by plan ambiguity (`docs/superpowers/specs/2026-06-10-strict-cost-sdd-design.md:22-23`).
- **SDD vs Native vs bare:**
  - The author's v6.4 post says Native is about 2× faster and half the cost of SDD (secondhand).
  - According to the same post, builds without Superpowers' implementation skills had markedly more bugs (secondhand). [claimed]
  - v6.0 claims about 2× speed and almost 50% fewer tokens against the previous SDD (`RELEASE-NOTES.md:338`).
  - The handoff text itself calls Native "Cheapest and fastest" (`skills/writing-plans/SKILL.md:191-193`) [implemented].
- **Time:** SDD eval runs take roughly 45-70 minutes for a 10-12-task plan (`docs/superpowers/specs/2026-06-09-sdd-task-scoped-review-dispatch-design.md:48-111`). The README claims "a couple hours" of autonomous work (`README.md:44`).

**Human attention**
- Front-loaded: why, approach, design-doc read, plan read, executor choice. Zero touches mid-run. Then the finish menu and reading the Rulings list.
- That is a good shape for big work and heavy for small work.

**Ceremony for small tasks**
- Mitigations: the quick-task exit (`skills/brainstorming/SKILL.md:22-23`); the "Or if you'd rather I just dive in" offer, made only when the agent started brainstorming on its own (`skills/brainstorming/SKILL.md:90-95`); short design docs for small changes (`skills/brainstorming/SKILL.md:214-216`).
- The 1% rule and the HARD-GATE still route most creative requests through brainstorming.
- A July eval of the *pre-rebuild* HARD-GATE wording found it pushed bounded tasks to full ceremony 5/5 (`docs/superpowers/specs/2026-07-30-codex-efficiency-fixes-design.md:119-126`). The current wording has not been re-measured in-repo. [claimed]
- On HN, one user reported removing it because it slowed work down and used more tokens than the stock planning modes (secondhand). [claimed]

### 4.8 Portability

**Generic and transferable**
- The phase model; trigger-only skill descriptions; plan-scoped ledger with file handoffs; one reviewer with two verdicts and a scoped re-review; a round cap with a capability bump; a rulings list; the verification gate; the builder check; TDD-for-prompts with controls.
- Git-primitive detection (`GIT_DIR != GIT_COMMON`) instead of harness sniffing (`docs/superpowers/specs/2026-04-06-worktree-rototill-design.md:39-41`).

**Harness-bound**
- Claude Code is the "reference harness": its vocabulary is `Agent`, todos and `Skill` (`skills/using-superpowers/references/claude-code-tools.md:3-4`).
- Agent resume for fix rounds, with a fallback to a fresh dispatch plus the report file (`skills/subagent-driven-development/references/fix-loop.md:23-27`).
- Nested subagents, Claude-Code-only (`skills/using-superpowers/references/claude-code-tools.md:13-16`).
- The 20k compaction cut and SessionStart `hookSpecificOutput`.
- Bash helpers, run through `bash` explicitly because packagers strip the exec bit (`skills/writing-skills/SKILL.md:161`).

**Multi-harness cost** (skipped dirs: `.kimi-plugin`, `.cursor-plugin`, `.codex-plugin`, `.opencode`, `.pi`, `.hermes-plugin`, `.antigravity-plugin`, `.devin-plugin`, `.muse-plugin`)
- Per-harness JSON output branches in the hook (`hooks/session-start:51-88`).
- Per-harness tool references (`skills/using-superpowers/SKILL.md:52-61`).
- Most v7.0.2 fixes are bootstrap plumbing across six harnesses (`RELEASE-NOTES.md:18-41`).
- The contribution rule that every skill change must work on all supported agents (`README.md:378`) slows evolution.

## 5. Strengths as mechanisms

| # | Mechanism | What it does | Failure it prevents | Citation | Tag |
|---|---|---|---|---|---|
| 1 | **Forced bootstrap and skill-first rule** | The hook injects `using-superpowers` on startup, clear and compact. The agent must invoke any plausibly relevant skill before acting, including before clarifying questions or exploration. A red-flags table pre-empts "just a simple question". | Skills sit on disk unused: "Without it, the skills are dead weight". It also stops the agent starting work before the methodology kicks in. | `hooks/hooks.json:5`, `hooks/session-start:49`, `skills/using-superpowers/SKILL.md:11-20,33-50`, `AGENTS.md:82` | [implemented] (script) |
| 2 | **Trigger-only descriptions** | A description says *when* to use the skill ("Use when…") and never summarises *how*. | The Description Trap: the agent follows a one-line summary instead of the skill, and drops review stages. | `skills/writing-skills/references/discovery.md:63-85`, `RELEASE-NOTES.md:1084` | [implemented] convention; evidence [claimed] |
| 3 | **Builder-check subagent on the spec** | A fresh "talented builder" who cannot talk to the author lists only the questions whose answers change the plan. The agent triages them into answered, minor and theirs, and asks the human once. | Specs with hidden gaps that the implementer guesses wrong, and endless clarification rounds. | `skills/brainstorming/SKILL.md:250-267`, `skills/brainstorming/builder-check-prompt.md:7-22` | [implemented] |
| 4 | **Hard approval gate with an explicit approval scope** | Nothing is built before the design doc is approved. "Sounds good" to an idea does not approve an unwritten doc. Keeping a spike's output is a new request. Plan approval is a separate step. | Scope approval being treated as a licence to scaffold (`RELEASE-NOTES.md:179`); building the wrong thing. | `skills/brainstorming/SKILL.md:269-294`, `skills/writing-plans/SKILL.md:179-198`, `RELEASE-NOTES.md:174` | [implemented] |
| 5 | **Plans as decisions, with propagation slots** | Plan header carries `Spec:`, verbatim Global Constraints and Review Focus. Each task carries Interfaces (consumes/produces signatures). Steps are "one reasonable thing". A proportion check flags plans longer than the code. | Constraints never reaching reviewers (the `go 1.26.1` incident); cross-task name drift; plans becoming code transcripts; crashes on inputs the spec implied but never named (`RELEASE-NOTES.md:175`). | `skills/writing-plans/SKILL.md:52-106,140-177`, `docs/superpowers/specs/2026-06-10-strict-cost-sdd-design.md:97-108` | [implemented] |
| 6 | **Files, not pastes, between seats** | `task-brief` and `review-package` write artifacts to the plan workspace. Implementers return a status of under 15 lines and put the rest in a report file. The controller never sees diffs. | Controller context bloat (a 42k-char dispatch that was 99% history); reviewers re-deriving diffs with dozens of git calls. | `skills/subagent-driven-development/SKILL.md:183-185,203-224`, `skills/subagent-driven-development/scripts/task-brief`, `skills/subagent-driven-development/scripts/review-package`, `skills/subagent-driven-development/implementer-prompt.md:128-149` | [implemented] (script) |
| 7 | **One skeptical, scoped task reviewer** | One reading of the diff gives two verdicts plus a ⚠️ "cannot verify" channel. The reviewer distrusts the report and its rationales ("left it per YAGNI" is a claim), cites file:line for everything, is read-only, and widens scope only for a named risk. | Rubber-stamping; reviewers sliding into merge-scale review; self-justifying implementers. | `skills/subagent-driven-development/task-reviewer-prompt.md:38-113,135-159` | [implemented]; cost effect [claimed] |
| 8 | **Anti-pre-judging tripwire** | If the controller's reviewer prompt contains "do not flag", "at most Minor" or "the plan chose", it must stop. A plan-mandated defect is still reported as Important. | The controller suppressing findings to avoid a fix loop; the defect shipping. | `skills/subagent-driven-development/SKILL.md:285-290`, `skills/subagent-driven-development/task-reviewer-prompt.md:153-157`, `RELEASE-NOTES.md:364` | [implemented] |
| 9 | **Convergent fix loop** | Resume the original implementer (rounds 1-3), then a fresh implementer on a stronger model (rounds 4-5). Every round ends with a scoped re-review. Adjudication happens only at the cap, and each ruling goes in the ledger. Minors are ledgered, not looped. | Unbounded review/fix churn (18 rounds observed); loops that never converge because new findings keep appearing; silent discards. | `skills/subagent-driven-development/references/fix-loop.md:9-77`, `skills/subagent-driven-development/re-review-prompt.md:55-100`, `RELEASE-NOTES.md:78` | [implemented] |
| 10 | **Plan-scoped, identity-stamped ledger** | Per-plan directory with an ownership marker. The ledger's first line names the plan. Resume rules trust ledger plus `git log` over memory. The workspace is deleted at plan end. | Re-dispatching completed tasks after compaction; reading another plan's ledger; scratch files committed to git. | `skills/subagent-driven-development/scripts/sdd-workspace:6-25,77-102`, `skills/subagent-driven-development/references/resuming.md`, `tests/claude-code/test-sdd-workspace.sh`, `docs/superpowers/specs/2026-07-06-sdd-plan-scoped-workspace.md:24-45` | [implemented] (script + test) |
| 11 | **Rulings, not stalls, plus an exhaustive rulings list** | Ambiguities are decided and recorded as `Ruling: what — why — cost if wrong`. Only 4 conditions stop the run. Every ruling surfaces in the final message. | Sessions parked for hours on answerable questions (`RELEASE-NOTES.md:228`); decisions made "in secret". | `skills/subagent-driven-development/SKILL.md:19-31`, `skills/subagent-driven-development/references/final-review.md:35-42`, `skills/executing-plans/SKILL.md:32-37` | [implemented] |
| 12 | **Required model slot and "cheapen mechanics, never judgment"** | Every dispatch template has a REQUIRED `model:` line. Tiering rules: turn count beats token price, a mid-tier floor for reviewers, the most capable model for the final review, and an escalation tier for fix rounds 4-5. | Silent inheritance of the most expensive model; cheap models advocating for defects. | `skills/subagent-driven-development/implementer-prompt.md:8-9`, `skills/subagent-driven-development/SKILL.md:140-175`, `docs/superpowers/specs/2026-06-10-strict-cost-sdd-design.md:25-52,205-212` | [implemented] slot; tier evidence [claimed] |
| 13 | **Worker no-subagents contract** | Implementers and reviewers may not spawn helpers or reviewers. "That review is already scheduled." | Duplicate review seats at full cost: 9/9 observed depth-2 spawns were duplicates. | `skills/subagent-driven-development/implementer-prompt.md:50-60`, `skills/subagent-driven-development/task-reviewer-prompt.md:55-62`, `docs/superpowers/specs/2026-07-30-codex-efficiency-fixes-design.md:42-66` | [implemented] |
| 14 | **TDD for skills, with pressure scenarios and wording micro-tests** | RED: run the scenario without the skill and record the rationalisations verbatim. GREEN: write the minimal counter. REFACTOR: close each new loophole, then meta-test by asking the agent how the skill should have been written. Wording is micro-tested against a no-guidance control (5+ reps, every match read by hand). | Guidance that addresses imagined failures; prohibitions that backfire; skills that crack under time, sunk-cost or authority pressure. | `skills/writing-skills/SKILL.md:30-45,163-182,272-305`, `skills/writing-skills/references/testing-skills-with-subagents.md:43-161,240-265`, `tests/systematic-debugging/pressure-scenarios/test-pressure-1.md`, `tests/claude-code/test-worktree-native-preference.sh:2-19` | [implemented] process; outcome numbers [claimed] |
| 15 | **Match the Form to the Failure** | Discipline failures get a prohibition plus rationalisation table and red flags. Wrong-shaped output gets a positive recipe. Omissions get a REQUIRED template slot. Condition-dependent behaviour gets a conditional on an observable predicate. No nuance clauses. | "Don't X" prohibitions that measurably *increase* X in composition tasks: 4.4 restated values vs 3.6 for the no-guidance control. | `skills/writing-skills/SKILL.md:248-263`, `docs/superpowers/specs/2026-06-10-positive-instruction-redesign-design.md:8-33` | [implemented] guidance; numbers [claimed] |

**Honourable mentions** [implemented]
- `task-done` mechanically gates the ledger on passing tests (`skills/executing-plans/scripts/task-done:42-55`).
- Provenance-based worktree cleanup, never `--force`, and a typed `discard` (`skills/finishing-a-development-branch/SKILL.md:132-201`).
- The `receiving-code-review` verify-then-push-back protocol (`skills/receiving-code-review/SKILL.md:14-25,113-129`).
- `systematic-debugging`'s "3 failed fixes → question the architecture" rule (`skills/systematic-debugging/SKILL.md:191-212`).

## 6. Prompt-engineering craft

**Discipline devices**
- **Iron laws in code fences.** "NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST" (`skills/test-driven-development/SKILL.md:33-35`); equivalents in verification (`skills/verification-before-completion/SKILL.md:16-18`), debugging (`skills/systematic-debugging/SKILL.md:16-18`) and skills (`skills/writing-skills/SKILL.md:165-167`).
- **Loophole closing by name.** "Don't keep it as 'reference'… Delete means delete" (`skills/test-driven-development/SKILL.md:39-45`).
- **Spirit-vs-letter pre-emption.** "Violating the letter of the rules is violating the spirit of the rules." (`skills/test-driven-development/SKILL.md:14`). The authors present it as a one-line kill-switch for a whole class of rationalisations (`skills/writing-skills/references/bulletproofing.md:36-44`).

**Recognition devices**
- **Rationalisation tables** (`| Excuse | Reality |`), harvested verbatim from baseline failures. They appear in roughly every discipline skill, e.g. `skills/test-driven-development/SKILL.md:222-236` and `skills/subagent-driven-development/SKILL.md:327-339`. The doctrine is that recognition tables "work" because they are read at decision time (`docs/superpowers/specs/2026-06-10-positive-instruction-redesign-design.md:24-25`).
- **Red-flag thought lists.** "These thoughts mean STOP—you're rationalizing" (`skills/using-superpowers/SKILL.md:33-50`). Systematic-debugging even lists the *human's* signals: "Stop guessing", "Ultra-think this" (`skills/systematic-debugging/SKILL.md:233-242`).
- **Phrase-level tripwires.** "If the prompt you are writing contains 'do not flag' … stop" (`skills/subagent-driven-development/SKILL.md:288-290`).

**Output-shaping devices**
- **Positive composition recipes over prohibitions.** "Your dispatch should contain: (1)…(5)" (`skills/subagent-driven-development/SKILL.md:207-215`). The doctrine: ties go to the shorter phrasing, and appending a nuance clause to a winning recipe degrades it (`docs/superpowers/specs/2026-06-10-positive-instruction-redesign-design.md:26-33`).
- **REQUIRED template slots** for things models omit: `model: [MODEL — REQUIRED …]` (`skills/subagent-driven-development/implementer-prompt.md:8-9`).
- **Status enums and tight return contracts:** `DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT`, "under 15 lines" (`skills/subagent-driven-development/implementer-prompt.md:140-146`).
- **Reviewer output starts with the verdict:** "no preamble, no process narration" (`skills/subagent-driven-development/task-reviewer-prompt.md:140-143`).
- **Psychological permission to escalate.** "Bad work is worse than no work. You will not be penalized for escalating." (`skills/subagent-driven-development/implementer-prompt.md:77-78`).
- **Good/Bad paired examples** in XML-ish tags (`skills/test-driven-development/SKILL.md:75-106`).

**Structure and wording devices**
- **Dot (Graphviz) graphs as the authoritative process.** Earlier releases treated prose as supporting content (`RELEASE-NOTES.md:1080-1082`); the graphs survive in SDD and executing-plans (`skills/subagent-driven-development/SKILL.md:35-99`). The bootstrap's graph was replaced by prose to save tokens (`RELEASE-NOTES.md:303`).
- **XML attention markers:** `<EXTREMELY-IMPORTANT>`, `<HARD-GATE>`, `<SUBAGENT-STOP>` (`skills/using-superpowers/SKILL.md:6-16`, `skills/brainstorming/SKILL.md:269`).
- **Persuasion principles**, consciously applied per Cialdini and Meincke et al.: authority ("YOU MUST"), commitment ("announce 'Using [skill] to [purpose]'"), and forced A/B/C choices in tests (`skills/writing-skills/references/persuasion-principles.md:5-35`; `skills/using-superpowers/SKILL.md:24`).
- **Deliberate terminology.** "your human partner" is tuned language that contributors may not change (`AGENTS.md:106,114`).
- **Hidden-reasoning guards.** "Do not trust the report" plus "a stated rationale never downgrades a finding's severity" (`skills/subagent-driven-development/task-reviewer-prompt.md:64-71`).

**Size and compaction engineering**
- SKILL.md under 20,000 bytes, enforced by a test (`tests/skill-size/test-skill-size.sh`).
- Rarely needed content goes to `references/` and is read "before every round" (`skills/subagent-driven-development/SKILL.md:302-305`).
- Stated per-skill word budgets exist (`skills/writing-skills/references/discovery.md:130-133`), although HEAD does not meet them.
- `@`-links are banned because they force-load files (`skills/writing-skills/references/discovery.md:195-200`).
- Brainstorming is the counter-example: it moved *away* from caps-heavy rules toward plain-language persona prose ("You are very good at building… that belief is usually thinner than it feels", `skills/brainstorming/SKILL.md:8-10`).

## 7. Weaknesses, costs, failure modes, risks

1. **The always-on bootstrap is expensive and over-eager by design.**
   - The "1% chance" rule (`skills/using-superpowers/SKILL.md:11`) is injected on every startup, clear and compact (`hooks/hooks.json:5`).
   - The bootstrap is ~492 words, against the project's own <150/<200-word budget (`skills/writing-skills/references/discovery.md:130-133`).
   - It pulls 3-20 KB skills into contexts that did not need them.
   - The maintainers removed the Codex hook because it "made the UX worse" (`RELEASE-NOTES.md:309`).
   - Public criticism centres on bloat, and on extra tokens and time compared with built-in planning modes (HN, secondhand). [claimed]
2. **Ceremony on small and medium work.**
   - The quick-task exit exists, but brainstorming plus a design doc plus a plan review plus an executor choice is the default path for anything "creative".
   - The maintainers measured the pre-rebuild gate wording forcing full ceremony on bounded tasks (`docs/superpowers/specs/2026-07-30-codex-efficiency-fixes-design.md:119-126`). Since then they have rebuilt brainstorming once and retuned it twice in about four weeks (v7.0.0 to v7.0.2; `RELEASE-NOTES.md:3-13,59-70,91-103`). That churn shows the right amount of ceremony is still unsettled. [claimed]
3. **SDD is costly, and its advantage over Native is unproven at HEAD.**
   - About $13 per benchmark run, half of it the controller (`docs/superpowers/specs/2026-06-10-strict-cost-sdd-design.md:13-20`).
   - The author's v6.4 blog post says Native is about 2× faster and half the cost (secondhand). [claimed]
   - The per-task review's marginal quality over Native plus final review is not shown in-repo.
   - The cheap-controller path recommended for Claude Code — a nested mid-tier orchestrator (`skills/using-superpowers/references/claude-code-tools.md:18-26`) — sits uneasily with the L2 result that Sonnet controllers shipped a planted defect 4/5 times (`docs/superpowers/specs/2026-06-10-strict-cost-sdd-design.md:121-133`).
4. **Per-task verification in SDD rests on self-reported evidence** (see §4.5).
   - Reviewers read rather than run, the controller checks only that evidence is present, and implementers are not told to load the TDD skill.
   - Only Native's `task-done` gate is mechanical.
   - One HN user reported that Claude still cuts corners on verification even with the skills installed (secondhand). [claimed]
5. **The orchestration is prose, not code.**
   - Round caps, the four stop conditions, "re-read before every round" and the ledger format are all instructions the model must keep following.
   - Compaction already broke one: 18 rounds against a cap of 5 (`RELEASE-NOTES.md:78`).
   - HN critics argue reliable workflows need programmatic orchestration (secondhand). [claimed]
   - Only a few invariants are scripts.
6. **Autonomy shifts decisions away from the human.**
   - "Rulings, not stalls" (`skills/subagent-driven-development/SKILL.md:19-25`) means plan-mandated defects and load-bearing review findings are now ruled on by the controller (`skills/subagent-driven-development/references/fix-loop.md:14-19,68-73`). Earlier designs sent them to the human (`docs/superpowers/specs/2026-07-15-sdd-fix-loop-redesign-design.md:73-77,91-95`).
   - The reviewer template still says "the human decides" (`skills/subagent-driven-development/task-reviewer-prompt.md:156-157`), which contradicts the controller rule.
   - The human sees rulings only after the branch is built, so a wrong early ruling compounds across later tasks.
7. **Model-generation sensitivity and accretion.**
   - Each frontier model needed retuning: for example Opus over-implementing during planning (`RELEASE-NOTES.md:141`). The v6.4 post says each new model needs its own tuning (secondhand). [claimed]
   - Brainstorming's rebuild aimed for "small and sharp" (`docs/superpowers/specs/2026-10-05-brainstorming-rebuild-design.md:164-165`). By word count (`git show … | wc -w`) it went 2,613 (v6.4.2) → 1,724 (v7.0.0) → 2,359 → 2,658 (v7.0.2), back above its pre-rebuild size within two point releases.
8. **Documentation drift and internal contradictions.**
   - The README still says:
     - plans are for "an enthusiastic junior engineer with poor taste" (`README.md:42`), which v6.4.2 replaced (`skills/writing-plans/SKILL.md:10`, `RELEASE-NOTES.md:147`);
     - tasks are "2-5 minutes each … complete code" (`README.md:314`), against `skills/writing-plans/SKILL.md:140-161`;
     - worktree creation comes before planning (`README.md:312`), against `skills/writing-plans/SKILL.md:14`;
     - review is "two-stage" (`README.md:361`), against one reviewer with two verdicts (`RELEASE-NOTES.md:344`).
   - `requesting-code-review` still lists a review "After each task in subagent-driven development" as mandatory and suggests `BASE_SHA=$(git rev-parse HEAD~1)` (`skills/requesting-code-review/SKILL.md:15,28`). SDD uses its own task reviewer and forbids `HEAD~1` (`skills/subagent-driven-development/SKILL.md:243`).
9. **Behavioural evidence lives outside the repo.**
   - Eval scenarios, transcripts and numbers are in `superpowers-evals` or the maintainer's private records (`docs/testing.md:21,25-37`).
   - Sample sizes are small: N=5 batteries, and a ship candidate passed planted-defect gates 2/3 (Superpowers 6 blog post, secondhand). [claimed]
   - Some design changes started from anecdotes that did not reproduce under test (`docs/superpowers/specs/2026-07-06-sdd-plan-scoped-workspace-eval-results.md:45-56`).
10. **Persuasion-heavy prompting is contested.**
    - HN commenters dismissed the caps and psychology framing as folklore rather than engineering (secondhand). [claimed]
    - Critics noted the cited persuasion paper concerns jailbreak compliance (secondhand).
    - The same framing caused a real incident: test scenarios saying "This is a real scenario. You must choose and act" were found by agents mid-task and treated as instructions (`RELEASE-NOTES.md:53`).
    - Aggressive "MUST" text can also fight user instructions, although the skill does say user instructions take precedence (`skills/using-superpowers/SKILL.md:63-65`).
11. **Smaller risks.**
    - The visual companion phones home for a logo with the plugin version unless opted out (`README.md:398-400`).
    - `git clean -fdx` erases the ledger (`skills/subagent-driven-development/SKILL.md:127-128`).
    - The plan sits uncommitted in the main checkout while work runs in a worktree (`skills/subagent-driven-development/scripts/sdd-repo:7-9`).
    - Contributions of new skills are generally not accepted (`README.md:378`).
    - The repo reports a 94% PR-rejection rate (`AGENTS.md:7`), and "carefully-tuned" skill wording may not be changed without eval evidence (`AGENTS.md:99-106`). Outside contributions to skill content face a high bar.

## 8. Top 5 ideas worth stealing (and what to leave behind)

**Steal**
1. **A plan-scoped on-disk ledger plus file handoffs.**
   - One directory per plan; the ledger's first line names its plan.
   - Each task gets a brief file, a report file and a diff-package file.
   - Resume from ledger plus `git log`, never from memory.
   - Cheap to build (four small bash scripts), and it fixes the most expensive observed failure: re-doing work after compaction.
2. **One skeptical task reviewer and a convergent fix loop.**
   - Brief + report + diff in; spec and quality verdicts plus ⚠️ out; file:line evidence required.
   - The implementer's rationales count as claims.
   - A scoped re-review gives ADDRESSED / NOT ADDRESSED.
   - Hard round cap with a capability bump, then ledgered adjudication.
   - Add the "do not flag" tripwire to your own controller prompt.
3. **Rulings ledger plus explicit stop conditions.** Write down the few things that justify interrupting the human, decide everything else with `Ruling: what — why — cost if wrong`, and hand back the exhaustive list. Consider keeping plan-mandated defects as human decisions; Superpowers itself wavered on that.
4. **Plan slots that carry decisions downstream.**
   - `Spec:` pointer, verbatim Global Constraints, per-task Interfaces, Review Focus (untested input classes, each pinned by a test).
   - "A plan records decisions, not code", with a proportion check.
   - Pair this with the builder-check subagent on the spec.
5. **Test your prompts the way you test code.**
   - Baseline without the guidance, record rationalisations verbatim, use 3+ combined pressures.
   - Micro-test wording against a no-guidance control: 5+ reps, read every hit.
   - Choose the guidance form by failure type ("Match the Form to the Failure").
   - Keep descriptions trigger-only.
   - Keep test scenarios *outside* the installed skill directory.

**Also cheap to copy**
- The `verification-before-completion` gate function.
- A `task-done`-style script that records completion only when tests pass, adding the mechanical gate SDD lacks.
- The REQUIRED `model:` slot in every dispatch template.

**Leave behind**
- The "1% → ABSOLUTELY MUST" mandatory bootstrap. Use explicit invocation or narrow triggers, plus a small always-on rule set.
- Full brainstorming ritual for work you have already specified.
- Per-task SDD for small or tightly scoped plans. Native plus one strong final review is the cheaper default by the author's own data.
- Caps-and-persuasion styling outside true discipline rules.
- Cheap-model reviewers or controllers for judgment work: the strict-cost spec records both failing.
- The visual-companion server.
- The multi-harness plumbing.

## 9. Open questions

1. **SDD vs Native vs bare on your own codebases.** What quality difference does per-task review buy for its ~2× cost? The repo's numbers come from two benchmark projects (go-fractals, svelte-todo) and are not reproducible from this repo.
2. **Nested mid-tier orchestrator quality.** The Claude Code reference recommends it for cost (`skills/using-superpowers/references/claude-code-tools.md:18-26`, `RELEASE-NOTES.md:194`). How does it fare on the planted-defect and judgment audit that killed the Sonnet-controller rung (`docs/superpowers/specs/2026-06-10-strict-cost-sdd-design.md:121-158`)?
3. **Rulings in practice.** How often are the "Rulings I made" wrong, and how much rework do they cause? Is surfacing them only at the end acceptable for multi-hour runs, or should high-cost rulings get an async notification?
4. **Self-reported test evidence in SDD.** How often do implementer reports overstate test results? Would a `task-done`-style mechanical gate per task in SDD pay for itself?
5. **Coexistence with native harness features.** Plan mode, auto skill discovery, built-in worktrees, and other plugins' skills. Does the bootstrap's priority rule cause conflicts or double ceremony? The bootstrap only covers the case of plan mode starting before brainstorming (`skills/using-superpowers/SKILL.md:22`).
6. **The external eval lab.** Do the `superpowers-evals` scenarios (planted-defect, rejects-extra-features, ceremony battery) work as a reusable personal eval harness for your own skills?
7. **Prose rules versus compaction on long runs.** Does the "re-read the reference before every round" pattern actually hold, or do the caps need to move into scripts or hooks (for example, the ledger counting fix rounds)?
8. **Trigger reliability over time.** Does the 1% rule over-trigger on newer models, as the Codex hook removal suggests? Is description-only discovery, as on Codex and Antigravity, now sufficient?

---

**Public sources consulted** (secondhand; small-model page summaries, partially truncated):
- Original announcement: <https://blog.fsck.com/2025/10/09/superpowers/>
- Superpowers 6: <https://blog.fsck.com/2026/06/15/Superpowers-6/>
- Superpowers 6.4: <https://blog.fsck.com/2026/09/21/superpowers-6.4/>
- Original HN thread (mirror): <https://blog.fsck.com/mentions/mentions/2025-10-11-hn-superpowers/archive.html>
- HN thread on a different post ("Agent Skills") with Superpowers comments: <https://hn.nuxt.dev/item/48015397>
- User review: <https://emschwartz.me/a-rave-review-of-superpowers-for-claude-code/>
