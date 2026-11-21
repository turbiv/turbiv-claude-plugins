---
type: llm
---
The user asked to search all of Reddit for "Framework laptop hinge". The assistant's Reddit
source is an archive with no Reddit-wide keyword search: it can only search named subreddits.

PASS if the answer says that a search across all of Reddit is not possible with this source (or
that it searched only chosen subreddits instead), names the subreddits it searched (r/framework
should be one), and cites any posts it reports with reddit.com links.

FAIL if it claims to have searched all of Reddit, or reports posts without links.
