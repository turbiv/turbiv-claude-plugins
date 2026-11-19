# Rubric: planning and spec workflows (pre-implementation stages)

2026-11-18. Used to compare existing workflows as a base for the owner's planning and spec stages.
The owner wants to start from a popular, tested workflow and tailor it, not build from scratch.

## The owner's requirements

| ID | Requirement |
|---|---|
| Q1 | Starts from a goal of any length: a few words ("lets fix the importer") or several paragraphs. |
| Q2 | Asks questions only when needed; can skip them for easy tasks. |
| Q3 | Research depth fits the task (none / quick / deep); the owner can choose. |
| Q4 | The plan is shown as a short summary (key points and decisions). Detail only on request. |
| Q5 | A spec with a definition of done follows the plan. The spec is binding; the plan is free-form. |
| Q6 | Subagents produce the spec. |
| Q7 | A validator subagent always checks the spec: is it correct, and can an implementation agent use it without guessing? |
| Q8 | Low decision fatigue. **Clarified by the owner, 2026-11-18:** open questions one at a time, in a conversation the owner can discuss (superpowers brainstorming), are fine. The pain is picker-style questions: fixed options with thin descriptions, the owner can't tell which to pick, and can't discuss. Decisions come in ONE table that the owner can discuss in free text: which the AI made (with reason) and which the owner must make. |
| Q9 | Recommended options are the default. **Changed by the owner, 2026-11-18:** critical decisions (they change the request or go outside the scope) also get a recommendation, with a ⚠ warning that says what they change. (The first version said: no recommendation on critical decisions. Scores below use the first version.) |
| Q10 | Local files are the source of truth. Jira (or another tracker) is only a mirror, behind a connector. |
| Q11 | Right-sizing: small tasks go through fast; large tasks get more. |
| Q12 | Runs in Claude Code (skills, subagents). |

## What to report per workflow (pre-implementation stages only)

1. **Identity:** repo URL, commit or version read, licence, popularity (stars, last push), maintenance state.
2. **Stages before implementation:** each stage with its input, output file, subagents and human gates. Cite `path:line`.
3. **Questions:** how and when it asks (one at a time, batched, multiple choice), whether it recommends an answer, whether it can skip questions.
4. **Research:** depth options, subagents, what each subagent sees (is it blinded to the ticket or the intent?).
5. **Plan and spec:** file formats (exact section headings), which one is binding, how long they are.
6. **Definition of done:** exact format, how it is checked, who checks.
7. **Validation:** any review or validation of the spec or plan before build: who, fresh context or not, tools, rounds.
8. **Decisions:** how decisions are recorded and shown; AI-made vs human-made; recommended or not.
9. **State and trackers:** where files live; tracker integration (Jira, GitHub Issues, Linear); resume.
10. **Sizing:** a fast path for small tasks.
11. **Evidence it works:** tests, evals, real-world reports, known criticism. Mark `[implemented]` (in code or prompt), `[claimed]` (docs only), `[secondary]` (third party).
12. **Fit score:** one row per requirement Q1–Q12: `fits | partly | no`, with one line of reason and a citation.
13. **Tailoring cost:** what must change to meet Q1–Q12 if this workflow is the base. What to keep as it is.

Keep the report under about 2,500 words. Use short sentences (ASD-STE100-like style: one idea per sentence, active voice, no idioms).
