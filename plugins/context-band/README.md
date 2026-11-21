# context-band

A band above the prompt in the Claude apps (desktop, VS Code, mobile).

![context-band: a crab with a badge of 2 and "2 shells running", then context fill, plan usage and the current Spotify track](docs/band-shells.webp)

With the count opened, the band lists each thing that runs:

![context-band: the band above, with a list under it of the two running shell commands](docs/band-shells-list.webp)

It shows:

- **What the session is running**, first, so you can tell a working session from an idle one. A small pixel crab acts it out (desktop and mobile; hover it and it waves):
  - nothing: the crab sleeps, `Idle`;
  - the model thinking: a thought bubble;
  - one tool: the crab dances for a few seconds, then bobs slowly (it dances again when the state changes);
  - only background work left: it watches an hourglass;
  - waiting for your answer: a `?`;
  - several things: the crab wears a badge with the count, and the count beside it opens a list of each one.

  Beside the crab, one thing reads as a few words for it: the Bash call's description (`Running the tests`), `Reading foo.ts`, `Agent: review the diff`, or `Thinking` while the model works with no tool running. Several read as how many and of what kinds, `3 running: 2 shells, 1 agent`.

  It counts the main turn's tool calls in flight and the background work that outlives them (background shells, subagents, monitors, workflows). The background list is refreshed at the end of each turn, from the list Claude Code keeps of work still in flight.
- **Context fill**: a 12-cell bar and percent, green below 40%, amber from 40%, red from 85%, then tokens used of the window.
- **What you spend**, decided per session:
  - signed in with claude.ai (Pro/Max): the 5-hour and 7-day plan windows, and when each resets;
  - with an API key: the session's cost in USD.
- **Spotify's current track** (macOS only), on the right. It asks Spotify only when it is already running, every 5 seconds, so it never launches it.

In a terminal session the band draws nothing and does not poll Spotify; the terminal keeps its own status line.

## Install

```text
/plugin marketplace add turbiv/turbiv-claude-plugins
/plugin install context-band@turbiv-claude-plugins
```

Then `/reload-plugins` or start a new session.

## Develop

Run the tests from the repo root:

```sh
claude plugin test plugins/context-band
```

After changing the band, raise `version` in `.claude-plugin/plugin.json`, then
`claude plugin update context-band@turbiv-claude-plugins` and `/reload-plugins`: a session runs the installed copy, not
this folder. To skip reinstalling while you work, load it from the checkout with `CLAUDE_CODE_PLUGIN_DIRS` (see the
repo README).
