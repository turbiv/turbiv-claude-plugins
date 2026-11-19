---
type: llm
focus: last_message
---
The owner asked to "make the about page better" on a tiny demo site. The workflow's rule: one ask per question. Two asks joined by "and" in one question count as two, because the owner answers the first and the second gets lost.

Judge only the question the reply asks the owner.

PASS if it asks for one thing. Examples that PASS: "What should a reader get from the about page that they don't get today?", "Why do you want to change the about page now?"

FAIL if it asks for two or more things, also when they are joined into one sentence. Examples that FAIL: "What bothers you about the page, and who should it be for?", "What is wrong with it now, and who should it serve?" Also FAIL if the reply asks no question.
