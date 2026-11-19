# Validation — <item id or spec path>

- Spec: <path> (revision <n>)
- Date: <yyyy-mm-dd>
- Run: <full | re-check of V#, V#>

## Restatement

Goal: <the goal in the validator's own words>
Done: <the Done list in the validator's own words, one line per ID>

## Findings

<!-- One line per finding. Severity: high | medium | low. High blocks READY.
     Where: a spec section, a line ID (S1, B2, D3) or a fact (F4). -->
V1 — <high|medium|low> — <where> — <problem> — <evidence> — <proposed row or fix>

## Result

<READY | NOT READY — <n> high findings: V#, V#>
READY does not cover Done rules 3 and 4 (baseline and red first). They need the commands to run, and those
run at the build start.

## After

<!-- Written by the main session. One line per finding. -->
V1 — <fixed as row D# "made by me" | became row D# | open as ⚠ row D#> — changed: <spec line IDs and sections, or "none">
