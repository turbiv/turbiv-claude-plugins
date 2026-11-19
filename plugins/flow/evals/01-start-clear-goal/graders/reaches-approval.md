---
type: llm
focus: last_message
---
The run started a work item from a clear goal (a footer with a contact address on a demo site's home page).

PASS if the reply is the approval message of the work item: it shows Done lines (IDs such as S1, N1 or P1) and asks the owner to approve with "ok" or to answer named decision rows. It may also list open decision rows.

FAIL if the reply asks the owner what they want (an intake question about the goal), says that the item is already approved, or stops before the approval message for any other reason.
