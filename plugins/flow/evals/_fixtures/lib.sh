#!/usr/bin/env bash
# Shared fixture helpers for the flow eval cases. A case's fixture.sh sources this file.
# A scaffold runs in the run's empty workspace (the working directory of the run), as you,
# with only --scaffold. It may create files and git state only.
set -euo pipefail

EVALS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SAMPLES="$EVALS/../docs/samples"
WS="$PWD"

git_quiet() { git -c user.email=eval@example.com -c user.name=eval -c init.defaultBranch=main "$@" >/dev/null; }

# The demo site as a git repo at <dir> (default: repos/demo-site).
demo_repo() {
  local dir="${1:-repos/demo-site}"
  mkdir -p "$dir"
  cp -R "$SAMPLES/demo-site/." "$dir/"
  git_quiet -C "$dir" init
  git_quiet -C "$dir" add -A
  git_quiet -C "$dir" commit -m "demo site"
}

# The demo site as the workspace itself, plus an empty work store in it.
demo_workspace() {
  cp -R "$SAMPLES/demo-site/." "$WS/"
  mkdir -p work-items
  printf 'Work items for this repo.\n' > work-items/README.md
  git_quiet init
  git_quiet add -A
  git_quiet commit -m "demo site"
}

# item.md. Args: id stage size depth goal [jira-key]
write_item() {
  local id="$1" stage="$2" size="$3" depth="$4" goal="$5" key="${6:-}"
  mkdir -p "work-items/$id"
  {
    echo "---"
    echo "id: $id"
    echo "title: ${id#*-}"
    echo "stage: $stage"
    echo "size: $size"
    echo "depth: $depth"
    echo "repos:"
    echo "  - $WS/repos/demo-site"
    if [ -n "$key" ]; then echo "tracker:"; echo "  jira: $key"; else echo "tracker:"; fi
    echo "created: 2026-11-18"
    echo "---"
    echo "# Goal"
    echo
    echo "$goal"
  } > "work-items/$id/item.md"
}

FOOTER_ID=20261118-demo-footer
FOOTER_GOAL="Add a footer to the demo site's home page with the contact address info@example.com, and get it live."

# A footer item at stage validated: plan, spec (the clean sample), decisions with one open ⚠ row,
# a READY validation. Used by the approval cases. Optional arg: a Jira key.
footer_validated() {
  demo_repo
  write_item "$FOOTER_ID" validated S none "$FOOTER_GOAL" "${1:-}"
  local d="work-items/$FOOTER_ID"
  cat >> "$d/item.md" <<'EOF'

## Reading

A footer with a mailto link on the home page, then the changed page live on the site.
EOF
  cat > "$d/plan.md" <<'EOF'
Goal: the live home page shows a footer with the contact address info@example.com.
Size: S — one repo, one page, the goal names the change.
Approach:
1. Add a footer element with a mailto link after the main part of site/index.html.
2. The owner deploys after merge with make deploy, because a deploy writes to the bucket.
Key facts: F1, F2
Risk: the deploy step is outside the session; the page is live only after the owner runs it.
More: plan.md

## Plan

The home page has no footer (F1). The nav has two links (F2) and stays as it is.
The session adds the footer and checks it with grep. The deploy is a person step after merge.
EOF
  sed "s/^item: deploy-done-line-clean$/item: $FOOTER_ID/" "$SAMPLES/deploy-done-line-clean/spec.md" > "$d/spec.md"
  sed "s/deploy-done-line-clean/$FOOTER_ID/" "$SAMPLES/deploy-done-line-clean/decisions.md" > "$d/decisions.md"
  cat >> "$d/decisions.md" <<'EOF'

## D2 — Who makes the changed page live?

- Kind: ⚠ changes the request
- About: build
- Recommended: the owner runs `make deploy` after merge (P2) — a deploy writes to the bucket, and the build session must not write outside the repo
- Options:
  - A: the owner deploys after merge. You get a reviewed change before it is live. Fails when the owner forgets P2.
  - B: the build session runs `make deploy`. You get the page live at once. Fails when the deploy needs credentials the session does not have, or when the change is wrong.
- K1 (changes the request?): yes — with A, this item does not itself make the page live, which the goal asks for
- K2 (outside the scope?): no
- Cost if wrong: the page is not live until the owner deploys
- Evidence: Makefile:10-11
- Source: validator V1
- Status: open
EOF
  cat > "$d/validation.md" <<EOF
# Validation — $FOOTER_ID

- Spec: $WS/$d/spec.md (revision 1)
- Date: 2026-11-18
- Run: full

## Restatement

Goal: the live home page shows a footer with the contact address info@example.com.
Done: S1 footer present; S2 address present; N1 nav unchanged; P1 owner approves the PR; P2 owner deploys; P3, P4 the live page shows the footer and the address.

## Findings

V1 — medium — Done when, P2 — the goal asks for the page to be live, and only a person step makes it live — Makefile:10-11 — row D2

## Result

READY
READY does not cover Done rules 3 and 4 (baseline and red first). They need the commands to run, and those
run at the build start.

## After

V1 — became row D2
EOF
}
