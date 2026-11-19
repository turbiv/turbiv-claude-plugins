# Planning and spec workflows: fit against the owner's requirements

2026-11-18. Rubric and requirements: [planning-rubric.md](planning-rubric.md).
Scores for EGM and superpowers come from the main session's reports in this folder.
Scores for Spec Kit, cc-sdd and HumanLayer come from new reports (pending).

`fits` = meets the requirement as it is. `partly` = a part exists and needs change. `no` = absent or opposite.

## Already studied (pre-implementation stages only)

| Req | EGM (brainstorm, draft, review) | superpowers (brainstorming, writing-plans) |
|---|---|---|
| Q1 goal of any length | partly: starts from a topic; open questions over several turns | fits: any request; a private check acts at once when the request is complete |
| Q2 questions only when needed | no: open questions always; one per response | fits: asks only when the answer changes what is built; the human can opt out |
| Q3 research depth | partly: a 7-lens swarm; no choice | partly: recon before asking; no depth choice, no research subagents |
| Q4 short plan summary | partly: a short brief, then a long design doc | partly: 200–300-word play-back chunks; a full design doc |
| Q5 spec with DoD, binding | partly: exact file list and test plan; no Done lines | partly: "the spec is binding, the plan is its argument"; no Done format |
| Q6 subagents produce the spec | no: the main session drafts with the human, section by section | no: the main session writes the design doc |
| Q7 validator always | fits, but heavy: at least 10 fresh read-only reviewer runs | partly: builder-check, always for projects, fresh, one round; it checks gaps, not facts or DoD |
| Q8 one decision table, no pickers (clarified) | no: a single-select gate per section | partly → close to fits: open questions one at a time, which the owner can discuss; the builder-check questions come in one batch; no decision table |
| Q9 recommend, except critical | no: never recommends on architecture | partly: always recommends one approach |
| Q10 local files, tracker mirror | fits: local files, no tracker | partly: local committed files; no tracker connector |
| Q11 right-sizing | partly: EGM Lite, design still "Proposed" | fits: a sizing step the human can override |
| Q12 Claude Code | fits | fits |
| **fits / partly / no** | 3 / 5 / 4 | 4 / 7 / 1 |

Other facts that matter for a base:

- **EGM:** Google open source. Strongest document review. Highest cost per review.
- **superpowers:** the more popular of the two. Its skills are tested against pressure scenarios. The owner already runs it, and the planning guide runs on top of it.

## New candidates

### Spec Kit ([spec-kit.md](spec-kit.md); v1.4.2, MIT, about 150k stars)

Q1 partly · Q2 fits · Q3 no · Q4 no · Q5 partly · Q6 no · Q7 partly · Q8 partly · Q9 partly · Q10 fits · Q11 partly · Q12 fits → **3 / 6 / 3**.

- `/clarify` asks up to 5 questions one at a time and recommends on every one. `/specify` batches up to 3 and never recommends.
- No subagents; the Claude adapter turned forked context off on purpose. `/analyze` is optional and runs after tasks exist.
- Plan stage writes five artifacts; field reports show about 2,000 lines per feature [secondary].
- Good source of templates and of `/analyze` checks for a validator prompt.

### HumanLayer riptide-rpi ([humanlayer-rpi.md](humanlayer-rpi.md); commit `2f5b58d3`, Apache-2.0)

Q1 partly · Q2 partly · Q3 partly · Q4 partly · Q5 partly · Q6 no · Q7 no · Q8 partly · Q9 no · Q10 partly · Q11 partly · Q12 partly → **0 / 9 / 3**.

- The plugin is skills only. Its subagents are TypeScript in HumanLayer's daemon. The open-question gate, sizing and the Linear/Jira link-back exist only in the commercial product.
- HumanLayer Cloud is shutting down; HumanLayer joined Factory. The README's install source is stale.
- Design questions stay open until the user resolves them; the recommendation is never the default.
- Worth taking: research that never sees the ticket; vertical-slice phases with automated and manual verification; the outline before the plan; numbered files in one task folder.

### cc-sdd, Kiro-style ([cc-sdd-kiro.md](cc-sdd-kiro.md); v3.1.0, MIT, 3,771 stars, one main maintainer)

Q1 fits · Q2 partly · Q3 partly · Q4 partly · Q5 partly · Q6 partly · Q7 partly · Q8 no · Q9 partly · Q10 partly · Q11 partly · Q12 fits → **2 / 9 / 1**.

- Discovery asks one question at a time; validate-design is a dialogue. No tracker integration.
- Specs are written in the main context. Fresh reviewers check only the task graph and run "if available".
- Right-sizing is "no spec" or three full documents, nothing in between.
- Worth taking: EARS rules, mechanical review-gate checks, requirement → design → task traceability.

## Clarification of Q8 (owner, 2026-11-18)

Superpowers' one-question-at-a-time conversation is fine: the questions are open and the owner can discuss them. The pain is picker-style questions: a fixed set of options with short descriptions, no clear way to choose, and no room to discuss. This makes superpowers a stronger base. Its remaining Q8 gap is only the missing decision table. The scores above are from before this clarification.

## Note on Q9 and on claims from the new reports

- The owner changed Q9 on 2026-11-18: critical decisions now get a recommendation plus a ⚠ warning. The Q9 scores above use the first version.
- The HumanLayer status (Cloud shutting down, joined Factory) and the Spec Kit figures (about 150k stars, about 2,000 lines of plan files) come from the subagent reports. Those reports cite their sources (`humanlayer-rpi.md:24`, `spec-kit.md:16,100`). This session did not re-open those sources.

## Ranking

| Rank | Workflow | fits / partly / no | Base? |
|---|---|---|---|
| 1 | superpowers (brainstorming) | 4 / 7 / 1 | **Recommended base** |
| 2 | cc-sdd | 2 / 9 / 1 | Source of parts: EARS, traceability, gate checks |
| 3 | Spec Kit | 3 / 6 / 3 | Source of parts: templates, `/analyze` checks for the validator |
| 4 | EGM | 3 / 5 / 4 | Source of parts: comprehension reader, unranked options for critical rows |
| 5 | HumanLayer | 0 / 9 / 3 | Source of parts: blinded research questions, automated vs manual checks |

## Why superpowers brainstorming as the base

1. It has the best fit and only one "no" (Q6: the main session writes the design doc).
2. It is the most popular of the five, MIT-licensed, and its skills are tested against pressure scenarios.
3. The owner already runs it, so its behaviour is known.
4. Its tested parts match the requirements: a private check that skips questions when the request is complete, recon before asking, a sizing step, local committed spec files, a hard approval gate, a fresh builder-check subagent, and "the spec is binding, the plan is its argument".
5. Every other candidate has the same core gap (questions one at a time, no always-on fresh validator) plus more gaps.

## Criticism of superpowers (web, 2026-11-18)

The owner heard that superpowers "isn't that good". What the sources say:

- **Bloat and ceremony on small tasks** is the top criticism: the always-on bootstrap, the mandatory process, and token cost on trivial work [secondary: mcp.directory, June 2026; superpowers.md §7.1–7.2].
- **Plans were too detailed.** writing-plans asked for complete code in every step. v6.4.2 changed it to "decisions, not code"; the maintainers report plans in a quarter of the time and about a third of the tokens [secondary: v6.4.2 release note].
- **Review loops burned tokens on nitpicks** (v5.0.4 note) [secondary].
- **"Models are good enough to go straight to coding"**, and "Claude makes more mistakes with superpowers": single commenters on Hacker News [secondary, anecdotal].
- **Brainstorming and the plan sketch are the parts most people keep.** The same HN thread and the mcp.directory review rate them as the highest-value part [secondary].
- **No controlled study** supports either the praise or the criticism. Evidence on both sides is anecdotal.

Conclusion for this design: the criticism targets the bootstrap, the implementation side (writing-plans, TDD, subagent-driven execution) and the ceremony. The parts this design takes are the brainstorming behaviours that critics rate highest. Take those parts as a fork. Do not depend on the superpowers plugin.

## Tailoring needed (superpowers brainstorming as base)

| Change | From |
|---|---|
| Keep the one-question-at-a-time conversation for intent and the why. Add one decision table for design decisions, discussed in free text, with no picker dialogs | Owner's requirement; unranked options on critical rows from EGM; AI-made rows in superpowers' own `Ruling:` form |
| A research step with depth none / quick / deep | Owner's requirement (Q3); HumanLayer blinded questions |
| A plan summary of 10 lines or fewer | Owner's requirement |
| A spec-writer subagent | Owner's requirement (Q6) |
| A Done-when format in the spec | Owner's planning-guide rules; Anthropic red-first; Kiro Unchanged; cc-sdd EARS for behaviour lines |
| The builder check becomes an always-on validator | superpowers builder-check, plus EGM paraphrase, Spec Kit `/analyze` checks; owner's requirement (Q7) |
| A tracker connector; local files are the source | Owner's requirement (Q10) |
