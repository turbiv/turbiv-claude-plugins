# What changed since you last looked

Agreed with the owner on 2026-11-20. A small change: the board page and its docs only.

## Why

Cards now change without the owner doing anything (the daily 09:00 sync). The owner wants to open the
board and see at a glance what changed since they last looked: new cards, cards that moved column,
rewritten text, renamed or removed cards. Their worry: "otherwise, how do I know which cards have
changed position and so on?" They use the board on two laptops and a phone.

## Goals

- The page shows the difference between the board now and the board as it was when this viewer last
  saw it. Not seen for a week: the difference covers the week. Deterministic, no history needed.
- "Seen" is detected by itself (the owner's first choice), with a button as the safety net.
- One "last seen" per person across all their devices.
- The owner's own edits on the page never show up as changes for the owner, on any device.

## Non-goals

- No change to sync, `kanban-tool` or the card schema. (The review session is changing sync; this
  stays clear of it.)
- No old wording of a rewritten summary or next step: only that it changed.
- No history of past syncs.

## Approaches

1. Sync writes a change list per run. Exact, but changes sync code that another session is changing.
2. **Picked by the owner:** the page keeps a per-viewer copy of the board as last seen and compares.
   Deterministic and simple ("it's pretty much the diff per day, and if we haven't seen it, the diff
   just gets bigger"). My earlier worry, own edits lighting up, is solved by updating the copy on each
   own edit.
3. A `changed_at` per card. Loses removed cards and the "from" column.

## Design

**The copy.** One document per viewer: `data/users/<user id>/seen` =
`{at: ISO time, cards: {<card id>: {t: title, s: status, h: hash of summary, n: hash of next_step,
x: id of the newest session}}}`. A removed entry is `null` (update merges objects, so a key cannot be
dropped). About 150 bytes a card; far below the 256 KiB document limit at 1000 cards. Hashes are 32-bit
FNV-1a in hex.

Viewers who cannot write their own folder (Viewer and Commenter on the share menu, and outside
visitors) keep the copy in `localStorage` (`kanban.seen`). Per device, but it works. The page tries the
database first and falls back after a refused write.

**The comparison** (baseline = the copy when the page loaded):
- card not in the baseline: **new**
- status differs: **moved**, "from <column>"
- title differs: **renamed**
- summary hash, next step hash or newest session differs: **updated**
- in the baseline, not on the board: **removed** (deleted or merged), listed by its old title
A card can carry more than one (moved and updated). No baseline yet (first visit): nothing is
highlighted, and the copy is saved.

**When it counts as seen.**
- After the page has been visible (Page Visibility API) for 10 s in a row with the board loaded, the
  page saves the copy of the board as it is now. The highlights stay for the rest of the visit; the
  next load starts from the new copy. A sync that lands while the page is open shows its changes, and
  10 more visible seconds save again.
- Opening a card: that card's highlight goes, and its entry in the copy is updated.
- **Mark all seen** (shown when there are changes): saves the copy and clears the highlights now.
- The copy is written only when it differs from the saved one, one write at a time.

**Own edits.** When the page writes a card (move, edit, add, delete), it also writes the new values of
that card into the copy (`update({cards: {<id>: …}})`, only the fields it changed). Changes made by
Claude in chat (`/kanban:board`) are not page writes and show as changes.

**What it looks like.**
- In the status line: "Since you last looked (3 days ago): 2 new · 3 moved · 4 updated · 1 removed".
  It is a button: it turns on a "Changes" filter that shows only changed cards, plus a short list of
  removed titles. Next to it: "Mark all seen".
- On a changed card: a badge (NEW, MOVED, UPDATED, RENAMED) and an accent outline. MOVED carries
  "from Todo". The card dialog says the same in its sub line.
- The existing `is_new` NEW badge stays as it is.

**Access rules.** Add `{path: "data/users/{self}", write: "interact"}` to the board's rules, so a
Contributor can keep their own copy too (the root stays `write: "admin"`). The owner and editors can
already write their own folder. Setup and the schema doc name the new rule.

## Left to the builder

The badge styling, the exact copy text, the preview's fake `data/users` support, and how the pure
comparison is tested (the page is a single HTML file; the comparison is plain functions tested in
Node if available).

## Overlap

The session "Board: color cards by project" changes `board/index.html` on its own branch. Both change
`renderCard`; whichever merges second fixes a small conflict. Keep the card change small.
