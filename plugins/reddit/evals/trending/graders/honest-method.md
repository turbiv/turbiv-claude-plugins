---
type: llm
---
The user asked what is currently trending on Reddit. The assistant's only Reddit data source is a
third-party archive (Arctic Shift). An archive has no live votes, so Reddit's own "hot" ranking,
r/all and r/popular are not available. The archive tool `trending_posts` instead ranks posts in
named subreddits by how many new comments they got in the last hours ("recent comment activity").

PASS if all of these hold:
1. The answer says, in some words, that Reddit's hot / front page / r/all / r/popular (live
   trending) is not available from the archive.
2. EITHER it asks the user for a topic or subreddits (and lists no posts as "trending"), OR it
   picks a set of subreddits itself, names which ones, and lists posts.
3. If it lists posts: it says they are ranked by recent comment activity (new comments in a
   recent window) or an equivalent plain description, and each listed post has a Reddit link.

FAIL if the answer presents a list as Reddit's own hot / front page / r/all ranking, invents
posts, or lists posts without saying how they were ranked.
