# Evals brief: `flow` plugin

2026-11-18. For the session that researches and writes the evals.

## Goal

Evals that tell the owner, while the plugin is developed, whether each skill and agent does what the design says. First research how to write good evals for Claude Code skills and agents. Then write them.

## Read first

- The design: `docs/design/pre-implementation-stages.md`. After the implementation session moves it: `~/git/turbiv-claude-plugins/plugins/flow/docs/design/`.
- The plugin, once built: `~/git/turbiv-claude-plugins/plugins/flow/`. Another session builds it at the same time. Check its state before you write evals that need it.

## Phase 1: research (no dependency on the build)

Find out how to write good evals for skills and agents. Start with these:

- superpowers `skills/writing-skills/` (pressure scenarios, a baseline without the skill, testing wording against a no-guidance control) and its `tests/`.
- EGM `tests/` (unit tests on reviewer config, an isolation probe).
- `claude plugin eval` (Claude Code's own plugin eval runner). Ask the `claude-code-guide` agent how it works.
- Anthropic's guidance on evals: start with about 20 real cases, an LLM judge with a rubric, plus human review.
- The existing research in `research/` (main session reports, section 4.6 of each).

Write the findings to `plugins/flow/docs/research/evals.md` with sources. Tag each claim [read], [secondary] or [unverified].

## Phase 2: write the evals

- Put them in `~/git/turbiv-claude-plugins/plugins/flow/evals/`. Touch no other folder in the plugin.
- Cover the behaviours most likely to fail. At least:
  - A clear goal gets no questions. An unclear goal gets open questions, one at a time, with no picker dialog.
  - The plan summary is 10 lines or fewer.
  - Every decision row has a recommendation. A row that changes the request or the scope has ⚠. "ok" alone does not accept a ⚠ row.
  - The spec writer runs as a subagent and returns its guesses.
  - The validator always runs, sees no conversation, and returns READY or NOT READY. A spec with a Done line that writes (for example a deploy) gets NOT READY.
  - Nothing outside the item folder is written before approval.
  - No Jira write in version 1.
- Explain to the owner how to run them, in `evals/README.md`.

## Rules

- Work on your own branch in `~/git/turbiv-claude-plugins`. Commit only your files. Do not push until the owner says so. The repo has uncommitted changes in `plugins/jira-guard/` that are not yours.
- Do not write to Jira.
- When a behaviour in the design is unclear, ask the owner.
