---
item: deploy-done-line-clean
revision: 1
status: draft
approved: null
---
# demo-site — the home page shows a contact footer, live

## Goal
The live home page of the demo site shows a footer with the contact address info@example.com.

## Scope
In:
- A footer with the contact address on the home page (goal)
- The changed home page is live (goal)
Out:
- Other pages
- Changes to the build and deploy targets

## Done when — the session checks
| ID | Check | Command (reads only) | Passes when | Proves |
|----|-------|----------------------|-------------|--------|
| S1 | The home page has a footer | `grep -c 'class="footer"' site/index.html` | prints 1 (baseline: 0) | goal: footer |
| S2 | The footer holds the contact address | `grep -c 'mailto:info@example.com' site/index.html` | prints 1 (baseline: 0) | goal: address |
| N1 | Unchanged: the nav keeps its two links | `grep -c '<a href="/' site/index.html` | prints 2, the same as the baseline | Unchanged |

## Done when — a person checks
| ID | Check | How | When |
|----|-------|-----|------|
| P1 | The owner approves the pull request | The GitHub review shows "Approved" by the owner, or the owner writes "ok" on it | before merge |
| P2 | The changed site is deployed | the owner runs `make deploy` | after merge |
| P3 | The live home page shows the footer: `curl -s https://demo-site.example.com/ \| grep -c 'class="footer"'` prints 1 (baseline before P2: 0). Proves goal: live | the owner runs the command | after merge, after P2 |
| P4 | The live footer holds the contact address: `curl -s https://demo-site.example.com/ \| grep -c 'mailto:info@example.com'` prints 1 (baseline before P2: 0). Proves goal: live | the owner runs the command | after merge, after P2 |

## Areas
The `site/` folder of the demo-site repo.

## Facts
F1 The home page has no footer today; it has a nav and a main part — site/index.html:7-16 — 2026-11-18 — checked
F2 The nav has two links, and both start with `/` — site/index.html:8-11 — 2026-11-18 — checked

## Decisions
D1 The footer is a `<footer class="footer">` element after the main part, with a mailto link — AI — details in decisions.md
