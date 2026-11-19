---
item: <item id>
revision: 1
status: draft            # draft | approved
approved: null           # <date> sha256:<hash of the body>
---
# <repo> — <outcome>

## Goal
One sentence. The outcome, not the method.

## Why
One to three sentences.

## Scope
In:
- <part> (goal) | (D3)
Out:
- <part>

## Constraints
Copied word for word from the goal, the owner's replies and the decisions. Binding.

## Behaviour
Only when behaviour changes. Leave it out for build, CI and infra goals.
Feature:  B1 When <event>, <system> shall <response>.
Bugfix:   Current: When <condition>, <system> <wrong result>.
          Expected: When <condition>, <system> shall <right result>.
          Unchanged: When <condition>, <system> shall continue to <result>.

## Done when — the session checks
| ID | Check | Command (reads only) | Passes when | Proves |
|----|-------|----------------------|-------------|--------|
| S1 | ...   | `...`                | ...         | goal / B1 |
| N1 | Unchanged: ... | `...`       | same result as the baseline | Unchanged |

## Done when — a person checks
| ID | Check | How | When |
|----|-------|-----|------|
| P1 | The owner approves the pull request | The GitHub review shows "Approved" by the owner, or the owner writes "ok" on it | before merge |
| P2 | <step after merge> | automatic on merge / the owner runs `<command>` | after merge |

## Areas
The repos, folders or stacks the work may change. Exact paths only when a decision fixes them.
New files follow the repo's layout.

## Facts
F1 <fact> — <file:line or URL> — <date> — checked|unchecked

## Decisions
D1 <decision> — owner | AI — details in decisions.md

## Needs from a person
Approvals, values and runs, each with its exact command.
