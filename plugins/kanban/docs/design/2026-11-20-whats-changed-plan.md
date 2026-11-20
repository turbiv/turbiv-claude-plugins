# What changed since you last looked: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The board page highlights what changed since this viewer last saw the board, and notices by itself that they have seen it.

**Architecture:** Pure comparison functions in a marked block of `board/index.html` (tested from Python through Node). The page keeps a per-viewer copy at `data/users/<id>/seen`, falls back to `localStorage`, and saves the copy after 10 s visible, on "Mark all seen", on opening a card, and on each own edit.

**Tech Stack:** plain ES5-style JS in one HTML file (as today), Python `unittest`, Node for the JS unit test, `tests/board-preview.py` for the browser check.

**Spec:** `plugins/kanban/docs/design/2026-11-20-whats-changed-design.md`

## Global Constraints

- No change to sync, `kanban-tool`, `lib/` or card fields. Only the page, the preview mock, docs, setup's capabilities line, the version.
- Copy doc: `data/users/<user id>/seen` = `{at, cards: {<id>: {t, s, h, n, x}}}`; removed entry in a patch = `null`.
- Hash: 32-bit FNV-1a, 8 lower-case hex characters.
- Seen after 10 s visible in a row (`SEEN_AFTER_MS = 10000`).
- One write at a time to the copy doc; write only when it differs from the last saved copy.
- Never save a copy while the baseline is unknown (read failed or still loading).
- `PAGE_VERSION` 3 → 4. Plugin version 0.1.1 → 0.2.0.
- New access rule: `{"path": "data/users/{self}", "write": "interact"}` next to the root rule.
- All card text set with `textContent` (as today).

## Review Focus

- A failed or slow read of the copy must not lead to saving a fresh copy (that would wipe the unseen changes). Test: `diffBoard(null, …)` is empty, and the page saves only when `S.seenKnown` is true.
- A card that moves into a closed column (Won't do, Archived) is counted as moved but hidden unless "Closed" is on. The Changes view shows closed columns when a changed card is in one.
- The viewer's own move on this device must not light up in this visit either: own edits patch the in-memory baseline too.
- Old or odd copy data (`cards` missing, an entry `null`, extra keys) must not throw: test `diffBoard` with `{cards: {a: null}}` and `{}`.
- A Viewer whose writes are refused (`invalid_argument`) switches to `localStorage` for the rest of the visit, without a toast per attempt.

---

### Task 1: Comparison functions

**Files:**
- Modify: `plugins/kanban/board/index.html` (new block between `// ---- seen:begin` and `// ---- seen:end`, inside the IIFE, before the helpers)
- Create: `plugins/kanban/tests/test_board_seen.py`

**Interfaces:**
- Produces (all pure, no DOM, in the marked block):
  - `fnv(s: string) -> string` (8 hex chars)
  - `entryOf(card) -> {t, s, h, n, x}`: `t` title, `s` status, `h` = fnv(summary), `n` = fnv(next_step), `x` = id of `sessions[0]` or "".
  - `snapshotOf(cards: card[]) -> {id: entry}`
  - `diffBoard(base: {id: entry|null} | null, cards: card[]) -> {byId: {id: {kinds: string[], from: string}}, removed: [{id, title}], counts: {new, moved, updated, renamed, removed}, total}`. `kinds` in the order new, moved, renamed, updated. `base` null → everything empty, total 0.
  - `patchBase(base, id, patch) -> void` (merges a patch into a base in place; `patch === null` sets the entry to null).

- [ ] **Step 1: Write the failing test** `tests/test_board_seen.py`: extract the marked block from `board/index.html`, append a JS driver that reads JSON cases from stdin and prints results, run with `node` (skip the class when `shutil.which("node")` is None). Cases:
  - `fnv("")` == `"811c9dc5"`, `fnv("a")` == `"e40c292c"`.
  - base null → `total == 0`.
  - base `{}`, one card → `counts.new == 1`, `byId[id].kinds == ["new"]`.
  - status todo → doing → `kinds == ["moved"]`, `from == "todo"`.
  - title changed → `["renamed"]`; summary changed → `["updated"]`; new `sessions[0].id` → `["updated"]`; move and summary → `["moved", "updated"]`.
  - unchanged card → not in `byId`.
  - base has `gone: {t: "Old", …}`, card missing → `removed == [{id: "gone", title: "Old"}]`; base entry `null` → not removed, and a card with that id counts as new.
  - `patchBase(base, "a", {s: "done"})` keeps `t`, changes `s`; then `diffBoard` shows no move for a card now done.
- [ ] **Step 2: Run** `python3 -m unittest plugins/kanban/tests/test_board_seen.py -v` — FAIL (no marked block).
- [ ] **Step 3: Implement** the five functions in the marked block.
- [ ] **Step 4: Run** the test — PASS. Run the whole suite `python3 -m unittest discover -s plugins/kanban/tests` — PASS.
- [ ] **Step 5: Commit** `kanban: board compares the cards with the viewer's last-seen copy`.

### Task 2: Seen state on the page, and the preview mock

**Files:**
- Modify: `plugins/kanban/board/index.html` (state, `start()`, write paths, render)
- Modify: `plugins/kanban/tests/board-preview.py` (mock: paths of any even length, deep-merge `update`, `user.id()`, `?seen=` presets)

**Interfaces:**
- Consumes: Task 1 functions.
- Produces: `S.base` (baseline for this visit), `S.saved` (last saved copy, JSON string), `S.seenKnown`, `S.seenLocal` (true = use `localStorage`), `S.diff`, `S.changesOnly`; functions `loadSeen()`, `saveSeen(reason)`, `ownEdit(id, patch)`, `armSeenTimer()`.

- [ ] **Step 1: Preview mock first.** `db.doc(path)` splits off the last segment as the doc id and the rest as the collection key; `update` merges nested plain objects recursively (arrays replace); `user.id()` returns `"preview-user"` (null with `?view=1`); with `?view=1` writes under `data/users` reject `{code: "invalid_argument"}`. `?seen=old` seeds `data/users/preview-user/seen` with a copy of the sample cards where card 2 was `todo`, card 1 is missing (so new), card 6's summary hash differs, and an extra card `gone-1` titled "Sample: a card that was deleted". `window.__stores` stays.
- [ ] **Step 2: Page state and load.** After `db` and `user`: `uid = await user.id()`; if uid, `db.doc("data/users/" + uid + "/seen").get()`; exists → `S.base = data.cards || {}`; not exists → try `localStorage` `kanban.seen`, else `S.base = null`, and mark first visit. `S.seenKnown = true` only after the read settled without error. Read error → `S.seenKnown = false`, no highlights, never save.
- [ ] **Step 3: Saving.** `saveSeen()` builds `{at: now, cards: snapshotOf(S.cards)}`; skips when `JSON.stringify(cards)` equals `S.saved`; writes with `set` through the existing `write("__seen", …)` queue, but without its toasts (own `.catch`): `invalid_argument` → `S.seenLocal = true` and write `localStorage`. First visit: save right after cards load. `armSeenTimer()`: on each cards snapshot and on `visibilitychange` to visible, (re)start a 10 s timer; on hidden, clear it; the timer calls `saveSeen()`.
- [ ] **Step 4: Own edits.** `ownEdit(id, patch)`: `patchBase(S.base, id, patch)` when `S.base`, then `update({cards: {[id]: patch}})` on the copy (or the local copy). Call it from `moveCard` (`{s}`), `saveDialog` (`{t}` and/or `{n}`, from the new values), `addCard` (`entryOf(doc)`), delete (`null`), and `openCard` (`entryOf(card)`: this clears its highlight).
- [ ] **Step 5: Check by hand** in the preview (`python3 plugins/kanban/tests/board-preview.py /tmp/x.html` then open `?seen=old`): `window.__stores` shows the copy saved after 10 s, a move updates `cards.<id>.s`. Run the suite — PASS.
- [ ] **Step 6: Commit** `kanban: the board remembers what each viewer has seen`.

### Task 3: Showing the changes

**Files:**
- Modify: `plugins/kanban/board/index.html` (CSS, `renderStatus`, `visible`, `render`, `renderCard`, `renderDialog`)

**Interfaces:**
- Consumes: `S.diff` (recomputed in `render()` as `diffBoard(S.base, S.cards)`), `S.changesOnly`, `saveSeen`.

- [ ] **Step 1: Status line.** When `S.diff.total`: a button "Since you last looked (<ago of S.baseAt>): 2 new · 3 moved · 4 updated · 1 renamed · 1 removed" (parts with 0 left out) with `aria-pressed` = `S.changesOnly`, and a small "Mark all seen" button (`S.base = snapshotOf(S.cards)`, `saveSeen()`, `S.changesOnly = false`). No changes: nothing new in the status line.
- [ ] **Step 2: Changes view.** `S.changesOnly`: `visible()` keeps only cards in `S.diff.byId`; closed columns show when a changed card is in one; a row above the columns lists removed titles ("Removed or merged: A, B"). Turns off by itself when the diff becomes empty.
- [ ] **Step 3: Card badge.** A changed card gets class `changed` (2px accent outline) and one badge: NEW, MOVED, RENAMED or UPDATED (first kind); MOVED has the title "Moved from <column label>" and a small "from Todo" line under the title. The `is_new` badge shows only when there is no change badge. Dialog sub line: "Moved from Todo since you last looked" / "New since you last looked" / "Updated since you last looked".
- [ ] **Step 4: Check in the preview** at desktop and 375 px, light and dark, `?seen=old`, `?view=1&seen=old`, and without `?seen` (first visit: no highlights). Mark all seen clears; opening a card clears it; dragging a card does not highlight it.
- [ ] **Step 5: Commit** `kanban: the board shows what changed since you last looked`.

### Task 4: Docs, rules, version

**Files:**
- Modify: `plugins/kanban/resources/card-schema.md` (new section `data/users/<id>/seen`, access rules line), `plugins/kanban/skills/setup/SKILL.md` (capabilities line with the new rule), `plugins/kanban/README.md` (one short paragraph), `plugins/kanban/board/index.html` (`PAGE_VERSION = 4`), `plugins/kanban/.claude-plugin/plugin.json` (0.2.0)

- [ ] **Step 1:** Write the docs as built.
- [ ] **Step 2: Run** `python3 -m unittest discover -s plugins/kanban/tests`, `plugins/kanban/tests/test-hooks.sh`, `claude plugin validate .` from the repo root — all pass.
- [ ] **Step 3: Commit** `kanban 0.2.0: what changed since you last looked`.

Publishing the page to the live board (Artifact publish with the new capabilities, then `page_version: 4` in `meta/board`) happens only after the owner says yes.
