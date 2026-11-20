---
type: llm
---
The user asked which subreddits to follow for home espresso. The assistant has a Reddit archive
tool that finds subreddits by NAME prefix only (it cannot search subreddits by topic), and a tool
that gives a subreddit's subscriber count and posts per day.

PASS if all of these hold:
1. It recommends r/espresso and r/Coffee (other subreddits as well is fine).
2. For both r/espresso and r/Coffee it gives a subscriber count AND an activity figure in posts
   per day (or an equivalent such as posts per week).
3. It does not claim it searched Reddit by topic or by description across all subreddits.
   Saying it looked up subreddits by name, or not saying how, is fine.

FAIL if r/espresso or r/Coffee is missing, if either lacks a subscriber count or a posts-per-day
figure, or if it claims a topic search.
