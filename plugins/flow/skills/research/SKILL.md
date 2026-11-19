---
name: research
description: Researches a flow work item at depth none, quick or deep, and writes the results to the item's research folder. Use with an item ID when the owner types /flow:research, or when flow:start calls it after intake.
argument-hint: <item> [none|quick|deep]
---

# Research

Read these first, unless you read them earlier in this session:

- `${CLAUDE_PLUGIN_ROOT}/resources/conventions.md`: work store, item, stages, facts, commits, style.
- `${CLAUDE_PLUGIN_ROOT}/resources/rules/sizes.md`: research depth.

## Check the input

1. Find the work store and the item as `conventions.md` says, also when Bash cannot run.
2. `item.md` must exist and have a `stage` value. With no item, say so and name `/flow:start <goal>`.
   With no `stage` value, intake is not finished: name `/flow:start <id>`. Then stop.
3. **Depth.** The argument wins, then `depth` in `item.md`, then the default for the size. When the
   argument differs from `item.md`, update `depth` there and say so in one line. When the depth is
   `deep` only by the size default, ask the owner for a yes and end the turn, because deep research
   costs more and takes longer.
4. When `research/` already has files, read them first. Add to them. Do not delete earlier facts,
   because later files may cite them.

## Depth none

Write no files. Go to Finish.

## Depth quick

- Read the code of the repos in `item.md` yourself. Use at most one Explore subagent, for a wide
  search.
- Read with Read, Glob and Grep. Use the shell only for `git log` and `git show`. Do not run the
  code, import its modules or look at installed copies. Reason: every other shell call asks the owner
  for approval, and running code is not reading it.
- Find how the relevant part works today and what the change would touch. Do not plan: the plan
  stage decides how.
- Write `research/notes.md`, one page or less, from
  `${CLAUDE_PLUGIN_ROOT}/resources/templates/research-notes.md`.

Number the facts from the next free number in the item.

## Depth deep

The researchers must not know the goal. A researcher that knows the intent describes the code it wants
to find, not the code that exists.

1. **Questions.** Write `research/questions.md` from
   `${CLAUDE_PLUGIN_ROOT}/resources/templates/research-questions.md`.

   - 2 to 8 questions. Each asks how the system works now, never how to build the change.
   - Do not use the goal's words. Do not name the item ID, its title or the item's own ticket key.
     Reason: the slug and the title state the goal, and the outside researcher can read tickets.
2. **Fact numbers.** Find the next free fact number `N` in the item. The repo researcher starts at
   `F<N>`, the outside researcher at `F<N+100>`. Reason: they run in parallel, and fact numbers are
   unique in an item.
3. **Dispatch** both agents in one message, so they run in parallel:
   - `flow:repo-researcher` gets: the text of `questions.md`, the absolute repo paths from `item.md`,
     its first fact number and today's date.
   - `flow:outside-researcher` gets: the text of `questions.md`, its first fact number and today's
     date.
   - Neither gets the goal, the item ID, the title, the ticket, the item folder, the work store path
     or the conversation. Give each call a neutral description, such as "Repo research questions".
     Reason: every field of the call reaches the agent.
4. **Write the replies unchanged**: the repo researcher's to `research/repo.md`, the outside
   researcher's to `research/outside.md`, each under a heading `# Repo research — <id>` or
   `# Outside research — <id>`. Reason: you know the goal, so an edit by you brings it back into the
   research.
5. When a researcher fails, or says a tool was not available, write that in its file and say so in
   one line. Go on. The plan stage sees the gap.

## Finish

1. When `stage` is `intake`, set it to `researched`. When the item is at a later stage, keep its stage
   and say in one line that the later files may be out of date.
2. Commit the item folder as `conventions.md` says. When `git` fails, say so in one line and go on.
3. Tell the owner in one or two lines: the depth, the files written, the number of facts, and the most
   important open point. End with this last line: `Next: /flow:plan <id>`.

When this skill stops early (a missing item, no stage, the yes for deep research), end with
`Stop: <reason>` as the last line. Reason: `/flow:start` reads the last line to know whether to go on.
