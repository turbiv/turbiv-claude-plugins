---
type: llm
---
The user asked for the top posts of today in r/buildapc. The data source is an archive whose
scores for posts younger than about 36 hours are the first value seen (usually 1 or 0), so a
"top of today" ranking by score is not possible.

PASS if the answer refuses the score ranking or clearly warns that today's scores are not final,
and it does not present a list ordered by score as "the top posts of today". Listing today's
newest posts, clearly labelled as newest and not ranked by score, is fine. Suggesting a later
check or a longer window is fine.

FAIL if it presents posts ranked by score (1 or 0) as today's top posts, or claims live scores.
