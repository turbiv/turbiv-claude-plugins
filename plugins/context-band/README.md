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

  It counts the main turn's tool calls in flight and the background work that outlives them (background shells, subagents, monitors, workflows). Background work shows from the call that starts it (asked for, or moved there with ctrl+b) and leaves as soon as Claude Code reports it ended (completed, failed or stopped); the whole list is also refreshed at the end of each turn from the list Claude Code keeps of work still in flight.
- **How hard the session works**, acted out by the same crab while the model thinks, a tool runs or several things run. The pace is the output tokens (the answer, the thinking and the tool calls, subagents' too) of the last minute against the usual rate for the model:
  - 0, normal: the crab as above;
  - 1, busy (about 1.5x the usual): it dances faster, with worried brows and a sweat drop;
  - 2, hyped (2x): steam and speed lines; while thinking, gears turn in its head; with several things running, it starts juggling;
  - 3, frenzy (3x): it turns red and jitters, its eyes spin and sparks fly; thinking brings lightning; it juggles four balls;
  - 4, meltdown (4x or more): rainbow colours and ghost crabs; flames and `!!` at work, rays from its head while thinking, six balls and a `9+` badge when many things run;
  - when the pace falls back from hyped or more, it pants and fans itself for a few seconds, then comes down one level at a time.

  The usual rate is learned, not set: only minutes in which the model actually wrote count, a burst counts for at most three times the usual rate, and each model has its own. It is kept between sessions in the plugin's own store (a small JSON file under your Claude Code configuration folder: numbers only, no prompts or replies). Until the band has seen a model for a few minutes, it uses a guess of 2,500 tokens a minute. The level reads the stream as it arrives (about 4 characters to a token) and settles on the API's own count when each response ends.
- **Context fill**: a 12-cell bar and percent, green below 40%, amber from 40%, red from 85%, then tokens used of the window.
- **What you spend**, decided per session from what the API reports:
  - on a Pro/Max subscription (its responses carry the 5-hour and 7-day windows): those windows, and when each resets;
  - on usage billing (an API key, or a pay-per-use Team/Enterprise seat signed in with claude.ai): the session's cost in USD,
    an estimate.

  A claude.ai login shows neither until its first response says which it is.
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
