# Card review, 2026-11-20

The first sync (2026-11-19) made 20 cards from 111 sessions. The owner went through them one by one.
This file records each change, the owner's reason in their words, and what sync should have done
differently. It is the input for the next change to the sync rules, the card schema and the board page.

Board: https://claude.ai/artifact/4dDncnh9TGbSFk1HTvpnSa. Changes were made by hand (the `kanban:board`
path: `ArtifactData` writes pinned with `if_version`), so sync's hand-edit rules apply to them.

Labels for "what sync should have done":
`grouping` (sessions on the wrong card, or one card that should be two), `granularity` (card too big or
too small), `title`, `status` (wrong or stale), `summary`, `next-step`, `links` (missing or wrong),
`noise` (should have been skipped), `scratch` (scratch-workspace sessions grouped badly), `schema`
(a field or column is missing), `page` (the board page).

## Observations before the review

- Three cards have no sessions: "Crown & Blight game concept", "Homelab firewall and guardrails",
  "Idea discovery loop". To check with the owner where they came from.
- "Kanban board plugin" is already stale: its summary says the branch is not pushed, but it was merged
  to main (93a5537) and installed the same evening.

## General feedback

Given while card 1 was on screen; it applies to every card.

| # | Owner's words | Label | What to change |
|---|---|---|---|
| G1 | "The where it stands has quite alot of text in it, we should limit it somehow so that there is a few bullet points that I can quickly scan through. The text is made for human consumption where I might read multiple cards." | `summary`, `schema` | `summary` as 2 to 4 short bullets, not a paragraph of up to 600 characters |
| G2 | "It would be nice to get some link to the session where this was discussed, as I might have many sessions and I might want to return to one." | `links`, `page` | A way back to each session from the card (today only a "Copy resume command" button in the session list) |
| G3 | "We should have the 'Done' column clear over time, as overtime it will have alot of information." | `status`, `page` | Done cards leave the column sooner than the 30 days of today |

## Changes the owner made on the page

Made on the page before the review, between 2026-11-20 16:17 and 16:20 UTC. Found by comparing the
cards with the copy read at the start of this session.

| Card | Change | What it says about sync |
|---|---|---|
| New MacBook setup | Deleted | Reason to ask (below) |
| Abloy key model | Doing → Won't do | Reason to ask when the card comes up |
| 3D apartment map | Next step "Take photos of one room and start a session that builds it with a Blender script." → "Find a connector for claude to do models". Note: "Images are taken" | Progress happened outside Claude. The owner wrote it in `notes`; sync does not read `notes` |
| Accounting product plan and design | Note: "The pitch deck is something that is not part of this anymore, it was a one off fun test." | `grouping`, `noise`: a one-off test session was put on a lasting card |
| Vinyl record holder | Note: "I have ordered a 3d printer." | The fact belongs to "3D printer purchase" too: one fact moves two cards |
| 11 cards | `is_new` cleared (opened on the page) | none |

## Cards

After card 2 the owner changed the method: "I dont want to check by card, I will check all of the
cards my self and report here." From then on the owner reviews the cards on the page and reports. Each
report, and every change found by comparing the board with the copy from the start of this session
(`board2`, read 2026-11-20 ~16:25 UTC), is logged below.

<!-- One section per card, in the order reviewed. -->

### 3D printer purchase

- **Before:** doing. 3 scratch sessions on 2026-11-18 (two "Best value 3D printer", one "Creality
  Ender-3 V3 K vs Bambu Lab A1 mini"). Summary: the pick is the Bambu Lab A1; "Nothing is recorded as
  ordered." Next step: "Check the Black Friday price of the A1 and order the printer with the three
  filaments."
- **Owner:** "I think its something that cant really be tracked, or I guess it can but its a thing that
  I might ask you for a bit, ask another agent, ask my friend and then just buy it without tell you. So
  this type of tasks shouldnt be really counted."
- **Facts:** the purchase happened outside Claude: the owner's note on "Vinyl record holder" says "I have
  ordered a 3d printer." The card would have stayed in Doing forever.
- **What sync should have done:** `noise`, `granularity`. Purchase research (compare products, pick
  one, buy) is a one-off decision, not a work stream: put it in `skip`, even when it spans several
  sessions. The decision ends outside Claude, so sync can never see it close.
- **After:** deleted on the owner's word ("Delete it"), 2026-11-20 ~16:50 UTC, pinned to version 2
  (the page had cleared `is_new`). Its 3 sessions stay in `meta/synced`, so sync will not bring it back.

### Home Assistant lights and plugs

- **Before:** doing. 5 scratch sessions (2026-11-18 and 19): pairing the GRILLPLATS plug for the plant
  lamp, the office light schedule, and the GPS jump that turned all lights off. Next step: "Set the area
  and tidy the entity ids of the new plug, then look at the Home view in a browser."
- **Owner:** "if I'm asking you to set up my home lights, I'm going to be asking you when it fails
  because well, it failed. I need your help, or when I'm trying to assign it to do something new. [...]
  the plant lamp. I asked that, can you set it up for me in Home Assistant and so on, and that was done.
  [...] we did the lamp, and then there's like the thing is done. So anything new that is created from
  that should be more like a to do, I guess, and not doing."
- **What this card is:** an upkeep area, not a project. Work comes in as separate requests (a fix when
  something fails, a new device or automation). Each request is usually finished in its session.
- **What sync should have done:** `status`. When the last request on the card was finished and only
  small follow-ups are left (set the plug's area, tidy entity ids, look at the view), the card is
  `todo`, not `doing`. `doing` is for work left in the middle. The follow-ups go in `next_step`.
- **Grouping:** the owner accepts one card for the area (no split asked for).
- **After:** no change by hand. The owner chose "Leave it as a test": once the rule is built, sync
  should move this card to Todo on its own.

### 1. Kanban board plugin

- **Before:** doing. Summary says the branch is not pushed; next step "Go over the 20 cards on the
  board, then decide whether to push the branch and open a PR."
- **Facts:** the branch was merged to main (93a5537) and the plugin is installed. The summary was
  stale within hours.
- **Owner:** no change asked for this card; gave G1 to G3 instead.
- **Label:** `summary` (long paragraph, hard to scan), `status` (stale the same day).

### Sauna dashboard (asked about out of turn)

- **Owner:** "Why is 'Sauna dashboard' not done? I thought its done, whats left there to have it as
  done?"
- **Before:** doing. Summary: "...The owner asked for a hottest-days leaderboard in place of the 30-day
  daily-max graph. ADR-0032 ... is committed on main as 86440fd, not pushed." Next step: "Check the
  sauna section on the dashboard and push commit 86440fd."
- **Facts from the session:** the leaderboard was built and checked in the browser at desktop and phone
  width. The ready alert moved to 60 °C. The only open item is that 86440fd is not pushed
  (homelab-knowledge-base is ahead 1, behind 3). ADR-0032 is about Claude's permission to edit HA
  dashboards, not about the sauna.
- **What sync got wrong:** `summary` reported a request as open when the session had built it (the
  digest kept the ask, not the outcome). `status`: an unpushed commit kept the card in Doing; the
  rules allow a done card to keep a small loose end as its next step. `grouping`: the ADR is general
  homelab work, not sauna work.
- **Later:** the owner pushed 86440fd from the sauna session itself (resumed 2026-11-20 16:24 UTC).
- **After:** no change by hand. The owner: "Dont mark it as done, i want the plugin to do that for me
  automatically."
- **Wish (G4):** sync moves a card to Done when the work is finished. Today the rule is "Sync never sets
  done". Label: `status`. The hand-edit rule (a status set by hand stays until newer work) can stay.
- **Test case for Part 2:** the next sync sees the new part of the sauna session (the push). With G4,
  that should move the card to Done.

## Side finding: the session-end hook in the desktop app

- **Owner:** "how will the hook post when a session ends? I dont usually close sessions on my claude
  desktop like I would in claude cli?"
- **Facts:** `pending.jsonl` for 2026-11-20 has 4 `start` lines and 1 `end` line. The one `end` is from a
  short tool session in a temp folder. The desktop sessions the owner used today logged only `start`.
- **Effect on sync:** none. Sync finds sessions by scanning `~/.claude/projects` by file time, and a
  synced session that went on is taken again from its last synced end (the sauna push will show up at
  the next sync as new work on that card).
- **Effect on the nudge:** the session-start note counts only `end` lines. With desktop sessions that
  stay open, the count stays near 0, so the "sessions are not on the board yet" note may never appear.
- **Label:** `hook`. To fix in Part 2: count sessions (start or end, by session id), not `end` lines.

### Changes found on the page after the owner's own review

The owner: "Ok I think all is done now here." Comparing the board (read ~18:40 UTC) with the copy from
the start of the review found these edits by hand:

| Card | Change | Owner's reason |
|---|---|---|
| Trackpad weight scale app | Doing → Won't do (16:58 UTC) | not given yet |
| Wii homebrew setup | Doing → Todo (17:00). Next step "Get a USB hard drive or SSD, format it as FAT32 with Master Boot Record and install a USB loader." → "Find a rom to install". Note: "Wii is now homebrewed, no roms have been installed which was the goal" | In the note: the homebrew step is finished, the goal (a game running) is not. Same pattern as Home Assistant: a finished step with a new thing left is `todo`, not `doing`. Progress again written in `notes` |
| Sauna dashboard | Dragged in its column (`order` set) | none needed |
| Abloy key model (before the review) | Doing → Won't do | not given yet |
| New MacBook setup (before the review) | Deleted | not given yet |

## Patterns

1. **Status is the weakest field.** 4 of 6 cards looked at closely had the wrong status, all `doing`:
   Sauna (finished), Home Assistant (request finished, follow-ups left), Wii (step finished, next thing
   not begun), 3D printer (decided, bought outside Claude). Sync uses `doing` for "touched lately".
   The owner wants `doing` only for work left in the middle, `todo` for "something is left but nobody is
   on it", and Done set by sync, not by hand (G4).
2. **Progress happens outside Claude, and the owner writes it in `notes`.** "Images are taken",
   "I have ordered a 3d printer", "Wii is now homebrewed". Sync does not see `notes` (`card_index` sends
   title, status, summary, next step, session titles), so the next sync would write the old next step
   back.
3. **Summaries are too long and sometimes wrong.** A paragraph of up to 600 characters is hard to scan
   across many cards (G1). The Sauna summary kept a request ("the owner asked for a leaderboard") and
   missed that it was built.
4. **Not everything is a work stream.** Shopping research (3D printer) and one-off tests (the pitch deck
   on Accounting product plan) became cards or card content. Upkeep areas (Home Assistant) are fine as
   one card, but are never "done".
5. **A way back to the session is missing** (G2). The page has only "Copy resume command".
6. **Done should clear sooner** (G3). Today: archived after 30 days.
7. **The reminder note at session start rarely shows** in the desktop app (side finding above).
