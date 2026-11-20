---
type: llm
focus: trace
---
The assistant answered a question about power limits for an Intel i9-9900K, using a Reddit
archive plugin (tools named mcp__plugin_reddit_reddit__*). A known relevant thread is
r/buildapc post wi7uhk, "Intel 9900K Underclocking/Power Limit Experiments" (2022).

PASS if the trace shows either:
- a deep_search call whose result lists wi7uhk among its candidates, or
- a web search that found the wi7uhk URL, followed by a plugin call (get_posts, get_thread or
  similar) that read wi7uhk from the archive.

FAIL if wi7uhk never appears in a plugin tool result (for example it is cited only from memory or
only from a web search snippet), or if the assistant fetched reddit.com directly.
