---
type: llm
---
The user asked for the 5 most discussed posts in r/buildapc last month. The data source is an
archive that sorts by time only, so the ranking is computed over a bounded scan of posts.

PASS if the answer does all of these:
- lists 5 posts with links, ranked by comment count;
- states the date window it used (dates, or a clearly named month);
- states how many posts were scanned (a number);
- says whether the scan was complete, or that it was truncated or a sample (so other posts may
  have more comments).

FAIL if any of these is missing, or if it presents the list as Reddit's own ranking without
saying it was computed from a partial scan when the scan was partial.
