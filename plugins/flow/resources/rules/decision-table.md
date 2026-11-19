# The decision table

Source: design section 7. All design decisions of an item go into one table. The rows live in
`decisions.md` (template: `resources/templates/decisions.md`). The chat shows the table at a stop.

## Kinds of row

| Kind | Meaning | "ok" accepts it? |
|---|---|---|
| ⚠ | An option changes the request or the scope | No. The owner answers it by name |
| Recommended | A real choice; the session recommends one option | Yes |
| Made by me | A call the session made and states, so the owner can reject it | Yes |
| Owner | A decision the owner already gave (in the goal or a reply) | Already decided |

Process steps are the session's calls: where files go, how to show something, looking further. Do them
and say so. A default the owner never heard is one they could not reject, so it goes in as a row "made
by me".

## When a row gets ⚠

Ask two questions for every row and write the answers in `decisions.md`:

| # | Question |
|---|---|
| K1 | Does an option change the request, so that the owner gets a different outcome than the goal says? This includes doing only part of the goal, and going against a decision the owner already gave. |
| K2 | Does an option go outside the scope: work, repos, systems, people or dependencies that the goal does not name? |

- "Yes" to either: the row gets ⚠ and the line "⚠ changes the request" or "⚠ changes the scope".
- Not sure: the row gets "⚠ may change the scope", with the reason. Still give a recommendation.
- A row without K1 and K2 answers is invalid.

## Guards against a missing ⚠

1. Every row in `decisions.md` has its K1 and K2 answers.
2. Every "In" line and every Areas entry in the spec traces to the goal or to a `D#`. A line with no
   trace is a hidden decision. The validator flags it.
3. The validator checks the rows again. A row it finds should have ⚠ gets one.
4. During the build (later stages), a decision that would get ⚠ by this test stops the session.

## What makes a good row

- Every row has a recommendation.
- A ⚠ row says in one line what it changes against the goal. Each option says what the owner gets and
  when it fails.
- A recommended row says why, and what the other option does.
- A row "made by me" says what, why, and the cost if wrong.
- A row that accepts a limitation says how broadly it bites, not only that it exists.
- Each row explains enough for the owner to choose. If the owner would say "I don't know what to pick",
  the row is too thin.
- Evidence (facts, file lines, links) stays in `decisions.md`, not in the chat.

## The table in the chat

One table per stop. A markdown table, never a picker dialog. Leave out an empty group. Leave out the
"Owner" rows; they are already decided.

**Show in full:** every ⚠ row, and every other open row about what gets built.

**Fold into one line** the other open rows: rows with `About: check` (how a Done line checks), and
small validator fixes (kind "made by me", `Source: validator V#`). A ⚠ row is never folded. The line:

`Also <n> check details and <m> small validator fixes. "ok" accepts them. Say "show" to list them.`

Leave out a part with a count of 0. On "show", list the folded rows in the same table format. A row with
no `About:` line counts as `About: build`. It is shown in full and is still valid.
`decisions.md` keeps every row in full. Reason: most of these rows are about the mechanics of a check,
and a long table hides the rows that change what gets built.

```
Decisions: 1 to check, 2 recommended, 3 made by me.
Answer the ⚠ rows by name, then reply "ok". Ask "explain D2" for more on any row.

⚠ Check these. They change your request or the scope.
| #  | Decision | Recommended | ⚠ What it changes | Other options |
|----|----------|-------------|-------------------|---------------|
| D1 | <question> | <choice> — <why> | <what changes against your goal> | B: <option>. You get <x>. Fails when <y>. |

Recommended. "ok" accepts these.
| #  | Decision | Recommended | Why | Other option |
|----|----------|-------------|-----|--------------|
| D2 | <question> | <choice> | <one line> | <option>: <effect> |

Made by me. Give the number to change one.
| #  | Decision | Why | Cost if wrong |
|----|----------|-----|---------------|
| D4 | <what I decided> | <one line> | <one line> |
```

## Reply rules

- "ok" accepts the recommended rows and the rows "made by me", also the folded ones. It does not accept a
  ⚠ row.
- "ok" with open ⚠ rows: name them in one line and wait.
- A ⚠ row is answered by name: "D1 ok" accepts the recommendation; "D1 B" picks option B.
- "D4: <text>" changes a row "made by me".
- "Explain D2", or any question about a row, starts a short discussion. The table stays open.
- "You choose" on a ⚠ row takes the recommendation and records "delegated by owner".
- An answer that creates a new ⚠ row adds it to the next table.
- Record every answer in `decisions.md`: `Answer: <text> — owner — <date>`.
