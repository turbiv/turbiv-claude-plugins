# context-band

A band above the prompt in the Claude apps (desktop, VS Code, mobile). It shows:

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
