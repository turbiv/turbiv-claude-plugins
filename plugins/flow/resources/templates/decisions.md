# Decisions — <item id>

<!--
One block per row. Rules: resources/rules/decision-table.md.
Kind: ⚠ | recommended | made by me | owner.
K1 and K2 are required on every row. A row without them is invalid.
Status: open | accepted | changed | delegated by owner.
About: build (what gets built; the default) | check (only how a Done line checks: its command, its pass
value, when a person checks). The chat folds open "check" rows that are not ⚠ into one line.
Source: intake | plan | spec writer guess G# | spec writer guess U# | validator V# | owner reply.
-->

## D1 — <question or decision>

- Kind: <⚠ changes the request | ⚠ changes the scope | ⚠ may change the scope | recommended | made by me | owner>
- About: <build | check>
- Recommended: <choice> — <why>
- Options:
  - A: <option>. You get <x>. Fails when <y>.
  - B: <option>. You get <x>. Fails when <y>.
- K1 (changes the request?): <no | yes — what | not sure — why>
- K2 (outside the scope?): <no | yes — what | not sure — why>
- Cost if wrong: <one line; required for "made by me">
- Evidence: <F#, file:line, URL>
- Source: <intake | plan | spec writer guess G<n> | spec writer guess U<n> | validator V<n> | owner reply>
- Status: open
