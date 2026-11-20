---
type: llm
---
Facts: the archive holds 22 comments on this post, 9 of them top-level (the post author,
u/willswill, wrote 10 of the 22). The post's stored num_comments field is 2, but that is a stale
snapshot from 2022, not the real count. The score is 9, and it is a frozen snapshot from when the
archive captured the post, not a live score.

PASS if all of these hold:
- The answer gives the number of comments as 22 (wording like "22 archived comments" is fine).
  If it also gives a top-level count, it is 9.
- It does not present 2 as the number of comments (mentioning that a stored field says 2 but is
  stale is fine).
- If it gives the score (9), it labels it as a snapshot, archived, or not live/current.

FAIL otherwise, for example "2 comments", a wrong count, or a score of 9 presented as the live
score with no qualifier.
