---
type: llm
focus: trace
---
The user asked for r/MechanicalKeyboards posts with the flair "Help" about key chatter from 2025.
The assistant used a Reddit archive plugin (tools named mcp__plugin_reddit_reddit__*).

PASS if:
- a search_posts call used the flair "Help" (as `flair:Help` in the query) and a 2025 date range
  (for example after "2025" and before "2025", or 2025-01-01 to 2026-01-01), and the tool result
  shows `link_flair_text` "Help" among its archive filters;
- every post the final answer lists has a created date in 2025 and a reddit.com permalink;
- if nothing matched, or the search was a partial scan, the answer says so plainly.

FAIL if the answer lists a post from outside 2025, a post without a link, or invents posts that
are not in the tool results.
