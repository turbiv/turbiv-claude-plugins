---
type: llm
focus: { source: file, path: "work-items/20261118-demo-footer/decisions.md" }
---
This is a decisions file. Each row starts with a heading "## D<n> — ...". Ignore HTML comments.

PASS if there is at least one row, and every row has a "Recommended:" line that names a concrete choice, a "K1" line and a "K2" line, each with an answer (no, yes or not sure).

FAIL if there is no row, or any row lacks a Recommended line with a concrete choice, or lacks a K1 or K2 answer.
