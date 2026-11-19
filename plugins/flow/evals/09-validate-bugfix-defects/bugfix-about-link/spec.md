---
item: bugfix-about-link
revision: 1
status: draft
approved: null
---
# demo-site — the About link on the about page works again

## Goal
On the about page, the About link in the nav opens the about page again.

## Why
The link points to `/abuot.html`, which does not exist, so readers get a 404.

## Scope
In:
- The About link in the nav of the about page (goal)
Out:
- The home page
- Other links

## Behaviour
Current: When a reader clicks About in the nav of the about page, the site returns a 404.
Expected: When a reader clicks About in the nav of the about page, the site shall open the about page.

## Done when — the session checks
| ID | Check | Command (reads only) | Passes when | Proves |
|----|-------|----------------------|-------------|--------|
| S1 | The about page links to the right file | `grep -c 'href="/about.html"' site/about.html` | prints 1 (baseline: 0) | Expected |
| S2 | The site looks right after the fix | open the site in a browser | the pages look good | goal |
| S3 | Nothing else changed | `git diff --stat main -- site/index.html` | the output is empty | goal |

## Done when — a person checks
| ID | Check | How | When |
|----|-------|-----|------|
| P1 | The owner approves the pull request | The GitHub review shows "Approved" by the owner | before merge |

## Areas
The `site/` folder of the demo-site repo.

## Facts
F1 The About link on the about page points to `/abuot.html` — site/about.html:10 — 2026-11-18 — checked

## Decisions
none
