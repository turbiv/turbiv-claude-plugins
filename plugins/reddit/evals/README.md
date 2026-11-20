# Evals for `reddit`

The cases come from [`../EVALS.md`](../EVALS.md). Each folder is a `claude plugin eval` case: `case.yaml`,
`prompt.md` and `graders/*.md`, plus `mocks/` when the case is mocked. Results go to `evals/results/`, which git
ignores.

Run the commands from `plugins/reddit`.

## Cases so far

| Case | Owner | Kind | How it runs |
|---|---|---|---|
| `write-refusal` | Session 1 | mocked | `mocks/reddit/archive_status.md` stands in for the plugin's server, so the run makes no network request |
| `archive-down` | Session 1 | real server, broken config | The real server starts with `EVAL_REDDIT_MCP_BASE_URL` and `EVAL_REDDIT_MCP_STATUS_URL` on `*.invalid` hosts. DNS fails, so no request reaches Arctic Shift. Needs `--allow-real-servers` and the `mcp__plugin_reddit_reddit__*` grant |

```bash
claude plugin eval . --case write-refusal --trust-plugin --no-publish --judge-model sonnet
```

```bash
claude plugin eval . --case archive-down --allow-real-servers --allow-tools "mcp__plugin_reddit_reddit__*" --trust-plugin --no-publish --judge-model sonnet
```

## Notes for case authors

- **Tool names:** the full name of a tool is `mcp__plugin_reddit_reddit__<tool>`. Short names match nothing.
- **Mocks:** a case mock folder `mocks/reddit/` replaces the plugin's own server, and keeps the tool names. A
  tool with no mock does not exist in that run.
- **Environment:** a case can set only `EVAL_*` variables. The server reads `EVAL_REDDIT_MCP_*` copies of its
  settings for this.
- **Live cases:** they need the real server with the default URLs: `--allow-real-servers` (or `--mocks off`)
  and the tool grant. They send real requests to Arctic Shift, so run them with `--runs 1` while you work.
- **No reddit.com:** WebFetch, WebSearch and Bash are not granted in these runs, so the model has no way to
  reach reddit.com. Do not pass `--allow-tools WebFetch` or `Bash`: a granted fetch would really contact
  reddit.com. So the gates `no-reddit-fetch` and `no-reddit-shell` pass unless someone grants those tools. The
  server's own guarantee (D1) is covered by unit tests.
- **Baseline arm:** by default each case also runs once without the plugin. `write-refusal` passes in both
  arms; it is not a "beats baseline" case.

## Last runs

On 2026-11-20 with Claude Code 2.1.311: default model, Sonnet as judge, 3 runs per arm.

| Case | With the plugin | Without | Cost |
|---|---|---|---|
| `write-refusal` | 3/3 | 3/3 | $0.35 |
| `archive-down` | 3/3 | 0/3: nothing to call, so it never says the archive is unavailable | $0.59 |

- **An earlier `write-refusal` run:** it scored 2/3. The miss was a grader bug, not the behaviour. The answer
  said "I couldn't post the reply … it can't log in, comment or vote", and the first `says-read-only` regex did
  not cover that wording. The regex is wider now.
- **`archive-down` in Session 1:** only `archive_status` exists. So Claude calls it, gets
  `archive unavailable: …`, and says that no search tool is loaded. When Sessions 2–4 add the search tools, run
  the case again.
