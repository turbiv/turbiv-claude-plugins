#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../_fixtures/lib.sh"
demo_repo
write_item "$FOOTER_ID" planned S none "Add a footer with the contact address info@example.com to the demo site."
d="work-items/$FOOTER_ID"
cat > "$d/plan.md" <<PLAN
Goal: the demo site shows a footer with the contact address info@example.com.
Size: S — one repo, static pages, the goal names the change.
Approach:
1. Add a footer element with a mailto link to the site.
2. Check the footer with grep.
Key facts: F1
Risk: none known.
More: plan.md

## Plan

F1 The site has two pages, site/index.html and site/about.html. Neither has a footer — $WS/repos/demo-site/site/index.html:7-16 — 2026-11-18 — checked

The footer is a footer element with the text "Contact:" and a mailto link (D1).
PLAN
cat > "$d/decisions.md" <<DEC
# Decisions — $FOOTER_ID

## D1 — The footer element and its text

- Kind: made by me
- About: build
- Recommended: a footer element with class "footer" after the main part, with the text "Contact:" and a mailto link — a mailto link lets a reader write at once
- Options:
  - A: footer with a mailto link. You get a clickable address. Fails when the reader has no mail client.
  - B: footer with the plain address. You get text only. Fails when the reader wants to click it.
- K1 (changes the request?): no
- K2 (outside the scope?): no
- Cost if wrong: one line to change in review
- Evidence: F1
- Source: plan
- Status: open
DEC
