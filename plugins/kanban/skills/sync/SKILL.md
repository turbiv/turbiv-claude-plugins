---
name: sync
description: Updates the user's kanban board from their Claude sessions - finds the sessions that are not on the board yet, puts each on the right card, and rewrites where the card stands and its next step. Use for /kanban:sync, "sync my board", "update the kanban", or when a session-start note says sessions are not on the board yet and the user says yes.
argument-hint: "[unattended | again <session id>]"
---

# Sync

Brings the board up to date. `kanban-tool` does the file work. You decide which session belongs to which
card and write the card text. The board is a claude.ai artifact; you read and write its cards with the
`ArtifactData` tool.

Read `${CLAUDE_PLUGIN_ROOT}/resources/sync-rules.md` first. It says what a card is, how to group
sessions, what to write and the format of the decision.

- Data folder: `${CLAUDE_PLUGIN_DATA}`. Call it `<data>` below and pass it in double quotes.
- `kanban-tool` is on the PATH of the Bash tool. If the shell does not find it, call
  `"${CLAUDE_PLUGIN_ROOT}/bin/kanban-tool"`.
- `ArtifactData` may be a deferred tool. Load it with ToolSearch (`select:ArtifactData`) when needed.
- If `ArtifactData` does not exist in this session, say so in one line and stop. Change no file.

With the argument `unattended` (the daily task), ask nothing: follow the "Unattended" section.

With the argument `again <session id>` (a card that sync wrote wrong): in step 3 add
`--again <session id>` to `collect`. That session is read again from its start, also when it is synced.
Rewrite its card from the whole session. The session id is in the card's session list on the board
(the first 8 characters are enough).

## Steps

1. Run `kanban-tool begin --data "<data>"`. It prints the board URL and the folder for step 2.
   If it says the board is not set up, tell the user to run `/kanban:setup` and stop.

2. Save the board. Call `ArtifactData` twice with the board URL, `action: "list"` and the `out_dir` that
   step 1 printed: once with `collection: "meta"`, once with `collection: "cards"`. Keep the two
   results: they show the `version` of each document. A collection with more than 100 documents needs
   `query.limit: 1000`.

3. Run `kanban-tool collect --data "<data>"` (with `--again <id>` when asked, see above).
   - "Nothing new": the tool has closed the sync and brought the local copy in line with the board. Do
     the one board write it prints (`last_sync` in `meta/board`, with the version from step 2), tell the
     user the board is up to date, and stop.
   - Otherwise it prints the cards on the board and the new sessions. When they are too long to print,
     it names two files instead: read both in full.
   - Sessions marked `UNPARSED` could not be read by the tool. For each, read the last 20 KB of the
     transcript yourself (`tail -c 20000 <file>`) and work from that. Name these sessions in your report,
     so the user knows the transcript format changed.

4. Decide, by the sync rules: one entry per card that gets sessions, and a `skip` entry for every other
   session. Write `status`, `summary` (bullets), `next_step` and one `log` line per session. Read the
   owner's notes in the card list first.

5. Give the decision to the tool:

   ```bash
   kanban-tool apply --data "<data>" <<'KANBAN_DECISION'
   { ...the decision JSON... }
   KANBAN_DECISION
   ```

   - `REFUSED`: nothing was written. Fix what the message names and run it again.
   - `OK`: it prints one JSON list of writes (or several, when there are more than 50 writes).

6. Write the board. Call `ArtifactData` with `action: "batch"`, the board URL, and `writes` set to the
   printed list, unchanged. Several lists: one call per list, in the printed order.
   - If a write fails because a version changed (someone edited a card meanwhile): start again at
     step 1, once. The sessions are not lost. This also holds in an unattended run.
   - If the tool refuses for another reason: stop and report. Do not run step 7.
   - Never run step 7 when the batch was not written. If that happened in an earlier run and sessions
     are missing from the board, run `kanban-tool collect --data "<data>" --scan-days 30` in step 3: it
     looks at the last 30 days again and leaves out what the board already has.

7. Run `kanban-tool commit --data "<data>"`. It updates the local copy that the session-start hook
   reads. If it says older sessions wait, run the sync once more.

8. Report in at most 10 lines: cards made (title), cards updated, sessions skipped (count), sessions
   unparsed (names), and the board URL. No card text.

## Attended runs

- The first sync of a board (the digest says many sessions and the board has no cards) is run by
  `/kanban:setup`, which shows the proposed cards and asks before step 5.
- When you would make more than three new cards in one run, show their titles first and ask once
  whether to go ahead.
- Otherwise do not ask. A wrong grouping is cheap to fix: `/kanban:board merge`, or drag on the board.

## Unattended

- Ask no question. Never wait for an answer.
- When a session's card is unclear, make a new card. New cards carry a "new" mark on the board, so the
  user sees and fixes them.
- If a tool call is refused or `ArtifactData` is missing: stop, say what was refused in one line. Do not
  retry and do not work around it. (A version conflict in step 6 is not a refusal: see there.)

## Limits

- This skill writes only: the data folder and the board's `cards` and `meta` documents.
- It never changes a repo, never commits, never pushes.
- It never changes a title or the user's notes, and never moves a card out of Won't do.
