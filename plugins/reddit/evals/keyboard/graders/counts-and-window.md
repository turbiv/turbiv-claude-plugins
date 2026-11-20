---
type: llm
---
The user asked for the most recommended mechanical keyboard on Reddit in the last 3 months. The
assistant has a Reddit archive tool that counts how many posts and comments mention each
candidate term in chosen subreddits over a date window, often from a sample of the window.

PASS if all of these hold:
1. It names a top keyboard or brand (or a short ranked list) as the answer.
2. It gives mention counts (numbers of mentions or threads) for the candidates it compares.
3. It states the exact date window it counted, with a start and an end date (for example
   "2026-08-20 to 2026-11-20"), not only "the last 3 months".
4. It names the subreddits it counted in.
5. It says the data comes from an archive, and does not present the counts as exact live
   Reddit statistics (mentioning a sample, a scan limit or that mentions are not always
   recommendations is enough).

FAIL if any of these is missing, or if it invents counts or threads.
