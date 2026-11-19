---
name: setup
description: Sets up the user's kanban board - creates the board page as a claude.ai artifact (or links an existing one), runs the first sync over their recent Claude sessions with a review of the proposed cards, and offers a daily sync task. Use for /kanban:setup, "set up the kanban board", or to update the board page after a plugin update.
---

# Setup

Makes the board and fills it for the first time. It is safe to run again: it then checks the board,
updates the page when the plugin has a newer one, and offers the daily task if there is none.

- Data folder: `${CLAUDE_PLUGIN_DATA}`. Call it `<data>` below and pass it in double quotes.
- Plugin folder: `${CLAUDE_PLUGIN_ROOT}`. Never write into it.
- `kanban-tool` is on the PATH of the Bash tool. If the shell does not find it, call
  `"${CLAUDE_PLUGIN_ROOT}/bin/kanban-tool"`.
- `ArtifactData` and the scheduled-task tools may be deferred. Load them with ToolSearch when needed.

Ask each question on its own and wait for the answer. Nothing here is tied to one user: take every
path, name and choice from this machine and this user.

## 1. Check what is needed

Run `kanban-tool status --data "<data>"`.

- The command fails because `python3` is missing: tell the user that the plugin needs Python 3.8 or
  later, and stop.
- This session has no `Artifact` tool: tell the user that the board needs artifacts (a Pro, Max, Team
  or Enterprise plan, a session signed in with `/login`, and a current Claude Code or desktop app), and
  stop.

## 2. The board

**The status shows a board URL.** Call `ArtifactData` `list` on collection `meta` to confirm that the
board opens. Then compare `page_version` in `meta/board` with the number after `PAGE_VERSION =` in
`${CLAUDE_PLUGIN_ROOT}/board/index.html`. When the plugin's number is higher, ask the user whether to
update the page. On yes: read the artifact (`Artifact`, `action: "read"`), publish the plugin's page to
the same `url` with the capabilities below, and update `page_version` in `meta/board`. The cards are
not touched by this. If the publish is refused because the page has a newer version from elsewhere,
show the user the message and ask before you do anything else.

**No board URL.** Ask: make a new board, or link one that exists (for example after a reinstall)?

- Link: take the URL from the user, or find it with `Artifact` `action: "list"` (the page's title is
  "Kanban Board"). Confirm with `ArtifactData` `list` on `meta`.
- New: read `${CLAUDE_PLUGIN_ROOT}/board/index.html` in full, then publish it with the `Artifact` tool:
  - `file_path`: that file. If the tool refuses the location, copy the file to your scratchpad folder
    and publish the copy.
  - `icon`: `board`
  - `description`: "Your work streams as cards: where each one stands, the next step, and which ones
    were left alone."
  - `capabilities`: `{"db": {"rules": [{"path": "", "read": "view", "write": "admin"}]}, "user": {}}`

  Then write `meta/board` with `ArtifactData` `set`: `{"title": "Kanban", "schema": 1, "page_version":
  <the page's number>, "stale_days": 14, "cold_days": 30}`.

In both cases run `kanban-tool init --data "<data>" --url <board URL>`.

## 3. Check the access rules

Do this once, after a new publish or a page update:

- `ArtifactData` `list` on `cards` with `as_level: "view"` must work (it may be empty).
- `ArtifactData` `set` of `cards/zz-access-check` with `as_level: "interact"` and data
  `{"title": "access check"}` must be refused.

If the write is not refused: delete that document, tell the user that the board's access rules are
wrong, and stop.

## 4. The first sync, with a review

Skip this section when the board already has cards; offer `/kanban:sync` instead.

Follow `${CLAUDE_PLUGIN_ROOT}/skills/sync/SKILL.md`, steps 1 to 4, with these changes:

- After `collect`, show the "By repo" list (folders with their session counts) and ask once: "Is there
  a folder I should leave off the board?" The board may be shared, so work the user must not publish
  stays off. For each folder named, run `kanban-tool exclude --data "<data>" --add <folder>` with the
  full path from the list (a folder's name alone also works, and covers every folder of that name).
  Then start again at step 1 of the sync and check that the folder is gone from the list.
- Before `apply`, show the proposed cards as a table: title, column, repos, number of sessions, and the
  next step. Then list in one line how many sessions you would skip and the main reasons. Ask: "Write
  these cards to the board?" Take corrections (rename, merge, split, drop, another column) and show the
  table again when it changed much.
- With the table, ask whether a project is missing. A project with no session in the last 30 days (or
  whose sessions ran on another machine) is not in the digest. For each one the user names, read its
  README and `git log -8`, and propose a card (`todo`, or `idea` when nothing is built). Say in its
  summary that it comes from the git history. Write these cards as `/kanban:board` writes a new card,
  with `repos`, `folders` and a GitHub link set, in the same `ArtifactData` batch or right after it.
- After the user's yes, do steps 5 to 8 of the sync. If you added cards by hand, refresh the local copy
  as `/kanban:board` does.

## 5. The daily sync

Only when this session has the tool `mcp__scheduled-tasks__create_scheduled_task` (the Claude desktop
app). Check `mcp__scheduled-tasks__list_scheduled_tasks` first: if a task `kanban-daily-sync` exists,
skip this section.

Tell the user: a scheduled task can run the sync once a day. It runs only while the desktop app is open
and the computer is awake; a missed run is caught up at the next launch. Ask whether to create it, and
at what time (offer 09:00).

On yes, create it with:

- `taskId`: `kanban-daily-sync`
- `title`: `Kanban daily sync`
- `description`: `Updates the kanban board from the day's Claude sessions.`
- `cronExpression`: `0 9 * * *` (or the user's time, in local time)
- `prompt`:

  ```text
  [kanban-sync] Update my kanban board. Use the Skill tool to run the skill "kanban:sync" with the
  argument "unattended". Ask no questions. If that skill or the ArtifactData tool is not available in
  this session, say so in one line and stop.
  ```

Then say: "The first run needs you. I start it now; open it from the Scheduled list and approve the
tools it asks for with 'always allow'. Later runs then go through alone." Start it with
`mcp__scheduled-tasks__run_scheduled_task`. Do not wait for it.

Without the scheduled-task tool (the terminal CLI): say that sync runs by hand with `/kanban:sync`, and
that a note at session start says when sessions wait.

## 6. Finish

Tell the user, in a few lines:

- the board URL, and that it is private until they share it from the page's Share menu. People they
  share it with see every card, read-only, and must be signed in to claude.ai.
- the commands: `/kanban:sync`, `/kanban:board`.
- that the hooks start with the next session, and that Claude then knows the open cards of the project
  it starts in.
- optional: the allow rule `Bash(kanban-tool:*)` in `~/.claude/settings.json` stops the permission
  prompts for the tool. Do not add it yourself.
