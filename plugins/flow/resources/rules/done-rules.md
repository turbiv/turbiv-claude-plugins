# Rules for the spec and its Done lines

Source: design sections 6.2 and 6.3. The template is `resources/templates/spec.md`.

## The spec

- **Binding.** After approval, the spec wins over every other file (see Precedence in
  `resources/conventions.md`).
- **Loose, not vague.** The spec states the outcome, the constraints and the checks. It does not name
  functions, classes or file paths, unless a decision `D#` fixes them. The implementation agent chooses
  those.
- **Sections per size.** S: Goal, Scope, Done when (both tables), Areas. M and L: every section of the
  template. Behaviour only when behaviour changes; leave it out for build, CI and infra goals.
- **Length.** An S spec aims for about one page (about 60 lines). Reason: a small change needs a small
  spec; a long one costs the owner and the builder time and hides the few lines that matter.
- **Constraints** are copied word for word from the goal, the owner's replies and the decisions.

## Rules for Done lines

1. **Pass or fail.** Every line passes or fails. "Works well" or "is clean" is not a line.
2. **Read-only commands.** A session line uses a command that only reads. A command that can write (a
   deploy, a change set, a migration, a push) is not a check. Use its read-only form, or make it a person
   line. *Why: in a trial, a `make check` target also pushed a build; its read-only
   form only lists the changes.* A test run that starts only local, throw-away resources (for example
   a local Docker container that the run removes) counts as reads only, when it changes nothing in the
   repo and nothing outside the machine.
3. **Baseline.** A diff or count check states a change against a baseline from the untouched branch. It
   never says "empty". *Why: an untouched branch already showed 11 differences.*
4. **Red first.** A line for new behaviour must fail at the baseline. If it passes before any work, it
   proves nothing; rewrite it. An Unchanged line (`N#`) must pass at the baseline; if it fails, record it
   as "already broken", not as work.
5. **Trace.** Every goal part and every Behaviour line has at least one Done line. Every Done line names
   what it proves.
6. **Underspecified.** If no Done line can be written for a goal part, the spec is underspecified. That
   part becomes a ⚠ row.
7. **Bugfix.** A bugfix spec has at least one Unchanged line.
8. **After merge.** A step after the merge is a person line. It says "automatic on merge" or gives the
   command the person runs. *Why: "the merge deploys" was read as a manual deploy.*
9. **Areas.** Areas name repos, folders or stacks. New files follow the repo's layout. *Why: "one new
   test file under `tests/`" was followed to the letter, against the repo's layout.*
10. **Outcome, not method.** Goal and Scope state the outcome and the decided constraints. A method
    appears only as a decision `D#`. *Why: a session reads "can" as "do".*
11. **Frozen text.** After approval, a later stage changes only the status of a line, never its text.
    Exception: when the baseline at the build start breaks rule 4, the build stops; a revised line goes
    to the owner as a row, and the spec gets a new revision. Status values: PASS, FAIL, PENDING,
    AFTER-MERGE. A line that was not checked never gets PASS. The status lives outside `spec.md`.
12. **What the user sees.** Prefer the check the user sees: the CI run, the deployed endpoint. A unit
    test alone is not enough when an end-to-end check exists.
13. **One-line command.** A session line uses one short command on one line: a `grep`, a test filter, a
    CLI call, or a script that already exists in the repo. Do not write a script into the spec. When no
    short command can check a part, make it a person line (`P#`) and say in its Check why no command
    exists. *Why: for a small layout change, a spec writer wrote a 60-line parser as a Done check; the
    check cost more than the change.*

## When the commands run

Done commands first run at the build start (design decision R2). The spec writer and the validator run
no commands. So validation cannot confirm rules 3 and 4; the build start checks them.

## Example

`S1 — The CI build on the branch passes — gh run list --branch <branch> --workflow <name> --limit 1
--json conclusion — conclusion is "success" — goal`. The baseline shows "failure", so the line is red
first.
