# Agentic workflow review: synthesis

2026-11-18. This compares two skill sets and relates them to your own planning guide.
It finds strengths. It does not design the merged workflow yet.

| Report | Source analysed |
|---|---|
| [elephant-goldfish-model.md](elephant-goldfish-model.md) | GitHub HEAD `70406c4`, 2026-11-17, with EGM Lite. Installed: v0.1.1, without EGM Lite |
| [superpowers.md](superpowers.md) | GitHub HEAD `22f0b46` = v7.0.2 = installed |
| [other-workflows.md](other-workflows.md) | 28 other workflows, each checked on the web on 2026-11-18 |

The line numbers in the citations hold for those commits. The clones are in a temporary folder.

Each report has the same nine sections and the same eight-part rubric. Every strength cites `path:line`
and is tagged `[implemented]` or `[claimed]`. I opened a sample of 15 citations myself, and all matched.
The other citations were checked by the agents that wrote the reports.

## The two in one line each

- **Elephant-Goldfish Model (EGM):** design docs are written with the human, then attacked by fresh
  reviewers that have never seen the conversation. Its strength is **document review**. The core stops
  before code.
- **Superpowers:** a library of discipline skills for one feature at a time, from brainstorm to branch.
  Its strengths are **unattended execution** and **testing the skills themselves**.

They don't compete. They cover different stages, and your guide covers a stage neither of them has.

## Coverage map

| Stage | Your planning guide | EGM | Superpowers |
|---|---|---|---|
| Split a large change into tickets, run sessions in parallel | **Strong.** Epic, Story, Sub-task; pick and claim; at most 3 sessions | None | None: one plan at a time |
| Requirements and interview | Planning session runs brainstorming | brainstorm: unranked options, each with how it fails | brainstorming, then a builder-check subagent |
| Design review | A fresh session reviews the tickets against the code | **Strongest.** Ordered reviewer personas, evidence-gated triage, convergence rules | builder-check only |
| Plan | Build session, one plan per slice | Zero-Decision rule; exact list of files | Decisions, not code; interfaces; constraints copied word for word |
| Build | executing-plans, inline | EGM Lite only: records the start commit, never weakens tests | Implementer and reviewer per task, or inline; TDD |
| Verify | Fresh final review, which also reads the PR description | EGM Lite: fresh review of the whole change set | Skeptical per-task reviewer; fix loop capped at 5 |
| PR and ship | **Strong.** Stacked draft PRs, fixup and autosquash, force-with-lease | None | Finishing menu |
| State and resume | Jira checklist plus end note (Progress, Surprises, Decisions, Next) | Files; the brief keeps rejected options | Local ledger per plan, deleted at the end |
| Learning loop | Manual log; every rule names the failure it prevents | drift-report (docs against code) | None for projects |
| Tests of the workflow itself | Dry runs | Unit tests on reviewer config; opt-in isolation probe | Skills built test-first against pressure scenarios |
| Gates enforced by the harness | Hooks for Jira writes | Reviewer tools limited by agent type, and a unit test checks it | Approval gates are prompt-only; a `task-done` script in inline mode |

## Strengths: the mechanisms that make each one good

Each line names the failure the mechanism prevents.

### Elephant-Goldfish Model

1. **Refuse rather than degrade** (`skills/egm-review/SKILL.md:28`). With no subagent tool, the review
   stops: "a review in the same context is not a Goldfish review". This prevents a self-review that
   looks like an independent one.
2. **The reviewer is its own agent type** (`tests/unit/test_harnesses.py:165-178`). Read, Grep and Glob
   only; `omitClaudeMd`; no memory; enforced by a unit test. This prevents reviewers that fix the doc,
   inherit project bias, or remember earlier rounds.
3. **Evidence-gated triage** (`skills/egm-resolve/SKILL.md:54-82`). The author may CONTEST a finding
   only with evidence the reviewer could have read; knowledge outside the doc means ESCALATE; a
   comprehension gap can't be contested. This stops the author agent from arguing valid findings away.
4. **Convergence rules for reviewers that vary from run to run** (`skills/egm-review-loop/SKILL.md:157-181`).
   - Settled findings stay settled; a fix does not settle a finding.
   - Done after two clean rounds in a row; cap of 5; churn is detected.
   - A failed reviewer is "not run", not clean.

   This prevents endless loops, fixes that undo each other, and a false pass after one lucky round.
5. **Review order and a paraphrase-first reader** (`skills/egm-review/SKILL.md:287-303`,
   `agents/comprehension.md:37`).
   - The simplicity check runs first, and runs again after the critic.
   - A naive reader must restate the doc before judging it.

   This prevents polishing a design that should be cut, and docs that only make sense to the author.
6. **Zero-Decision plan with an exact file list**
   (`resources/document_standards/implementation-readiness-standard.md:12-33`). A plan fails if the
   implementer must make any design choice. This prevents invented schemas and APIs, and opportunistic
   refactors.

### Superpowers

1. **A ledger per plan, and files between agents** (`skills/subagent-driven-development/references/resuming.md:6-12`).
   The ledger's first line names its plan; resume trusts the ledger and `git log`, not memory. This
   prevents redone work after compaction.
2. **A skeptical per-task reviewer** (`skills/subagent-driven-development/task-reviewer-prompt.md:64-113`).
   The implementer's reasons count as claims. A tripwire stops the controller if its reviewer prompt
   says "do not flag" (`SKILL.md:285-290`). This prevents rubber-stamping and hidden findings.
3. **A fix loop that ends** (`references/fix-loop.md:9-77`). Rounds 1–3 resume the implementer; rounds
   4–5 use a fresh, stronger model; then the controller rules. This prevents endless churn; one session
   once ran 18 rounds.
4. **Rulings, not stalls** (`skills/subagent-driven-development/SKILL.md:19-31`). Only four things stop
   the run. Everything else is recorded as `Ruling: what — why — cost if wrong` and listed at the end.
   This prevents a session parked all day on a question it could answer.
5. **Plans carry decisions, not code** (`skills/writing-plans/SKILL.md:52-106`). A spec pointer,
   constraints copied word for word, and interfaces per task. This prevents constraints that never
   reach the reviewer, and names that drift between tasks.
6. **Skills are tested like code** (`skills/writing-skills/SKILL.md:248-305`). Run the scenario without
   the skill, record the agent's excuses word for word, write the counter, and compare the wording with
   a no-guidance control. "Match the form to the failure": a "don't X" rule can increase X. This
   prevents rules written against imagined failures.

## What they share, including the weak points

- **Approval gates mostly live in prompt text.**
  - Superpowers' approval gates are prose.
  - One third-party blog comparison reports that a single pre-approval sentence skipped BMAD's gates.
    It is one source, and I did not check it.
  - Anthropic's guidance is to put any rule that must always hold in a hook or a deny rule.
  - EGM enforces only one thing in the harness: its reviewers' tools.
- **Neither measures results on real work.**
  - EGM's behaviour tests don't run in CI.
  - Superpowers' numbers come mostly from the author's own benchmarks.
- **Both are expensive, and only partly scaled to the size of the task.**
  - EGM: at least 10 reviewer runs per review. EGM Lite is its answer for small changes, and its design
    is still "Proposed".
  - Superpowers re-injects a 492-word rule set at every start, `/clear` and compaction.
  - Superpowers' per-task review costs about $13 per benchmark run. That is the authors' own
    measurement, in `docs/superpowers/specs/2026-06-10-strict-cost-sdd-design.md:13-23`.
  - The report relays a claim from the author's blog that inline runs about 2× as fast at half the
    cost. I did not check it.

## Where they disagree, and where your guide stands

| Question | EGM | Superpowers | Your guide |
|---|---|---|---|
| Stop and ask, or decide and record? | The human picks from unranked options | Decide and record; stop for 4 things only | 4 stop triggers; other decisions go in the PR description. Closest to Superpowers, but stricter on wrong facts |
| Should the agent recommend an answer? | No: up to three options, unranked, and "just pick one" is refused (`skills/egm-draft/SKILL.md:63-71`) | Yes: "Recommend one and say why" (`skills/brainstorming/SKILL.md:162`) | Stop comments carry a recommendation |
| Review the plan or the code? | The plan, in depth | Both are gated | The code: draft PRs. A secondary summary of a 2026 HumanLayer talk says HumanLayer moved the same way |
| Review per task, or once at the end? | — | Per task (SDD) or once (inline) | Once, inline by default; Superpowers' cost data points the same way |
| Where state lives | Files | Local files, deleted at the end | Jira; no handoff file |

## Ideas that fit your guide

These are candidates for the next round of research, not decisions. Each is chosen because it targets
a failure your guide already records.

1. **The fresh reviewer as a read-only agent type with `omitClaudeMd`, which refuses if it can't run
   fresh** (EGM). This makes "have a fresh session review" a rule the harness enforces.

   A limit: with only Read, Grep and Glob, the reviewer can't read Jira or run `git show`. Your
   review step needs both. It would need read-only Jira tools and a narrow Bash allowlist.
2. **A paraphrase-first reader on a Sub-task before build** (EGM). Two of your lessons from an earlier
   build are comprehension failures: "can" read as "do", and "one new test file under `tests/`" followed
   to the letter. A naive restatement is aimed at exactly this kind of failure.
3. **Evidence-gated triage and convergence rules when a review is applied** (EGM).
   - For build reviews, your guide fixes cheap minor points and lists the rest in the PR description.
   - It has no rule for when a session may contest a finding, or for when a review loop is done. This
     matters most for "Apply the review" in planning sessions.
4. **The `Ruling: what — why — cost if wrong` line in the PR description** (Superpowers). Your guide
   already sends in-scope decisions there; the "cost if wrong" part tells you what to check first.
5. **Tests for the guide itself** (pressure scenarios from Superpowers). Today the guide is checked
   with dry runs.
6. **A retrospective that gathers the evidence** (Compound Engineering in the survey).
   - Your lessons log is in the guide, so every session reads it.
   - The manual part is the step before that: going through transcripts, reviews and PR comments, then
     turning a lesson into a rule.

## Other workflows worth studying

This list leaves out what was already studied: BMAD, Spec Kit, Kiro, Codex execution plans,
Anthropic's long-running harness posts, Beads, Cursor and Cognition. The ranking is from
[other-workflows.md](other-workflows.md), section 4.

1. **HumanLayer research→plan→implement, now CRISPY/QRSPI.** Research runs without seeing the ticket,
   so the ticket's claims can't anchor it. A short design-discussion doc is reviewed before the plan,
   and each stage prompt has an instruction budget.
   - A secondary summary of a 2026 talk says HumanLayer changed from reviewing plans to reading the code.
     That would match your guide's choice to review the code. It is not checked beyond that summary.
2. **Anthropic's official plugins: `code-review` and `feature-dev`.** A confidence score with an 80
   threshold and a list of known false positives. Hooks, Stop hooks and `/goal` for gates that must
   always hold.
3. **Compound Engineering (Every).** Lessons go to `docs/solutions/`, and the next planning run reads
   them automatically.
4. **Matt Pocock's skills.** `GLOSSARY.md` and ADRs are updated while the interview runs.
   Tracer-bullet ticket slicing (`to-tickets`) and `wayfinder` for work across several sessions are
   close to your Story-to-Sub-task step.
5. **OpenSpec.** Delta specs are merged into a living "current behaviour" spec. This conflicts with your
   guide's choice to keep the design in Jira, so it is useful mainly as the contrast.
6. **cc-sdd (Kiro's flow for Claude Code).** A bugfix spec must state the behaviour that must not change.
   `validate-gap` checks existing code before design.

Gone or changed: the original GSD repo was archived on 2026-06-26 and continues as `open-gsd/gsd-core`.
Claude Task Master has had no push since 2026-04-28. Tessl turned into a skills registry.
claude-flow is now ruflo.

## Open questions for the next round

- **Your guide is longer than 20,000 characters, and every session reads it whole.**
  - After compaction, Claude Code re-attaches a skill cut at 20,000 characters. One Superpowers skill lost
    its cap of 5 fix rounds that way, and a session ran 18 rounds (`RELEASE-NOTES.md:76-78`).
  - Your guide is loaded with Read, not as a skill, so that case may not apply.
  - The open question: what does a build session that compacts still know of the guide?
- **EGM:** run one `egm-review` on a real Story design, then compare its cost with the findings it
  produced. Look at EGM Lite again when its design is no longer "Proposed".
- **Superpowers:** your guide was written against 7.0.0, and 7.0.2 is installed.
  One plan per slice with stacked slices is still untested, and so is SDD against inline on a
  Sub-task with several slices.
