# Sizes

Source: design section 4. The limits are starting values, to be tuned after real use.

## How to size

- The size comes from what the goal asks for, not from the length of the text. "Lets fix the importer" can
  be S or L.
- When a short goal leaves the size unclear, read the code first, then size.
- State the size and one reason. The owner can change it in any reply.
- When the work grows during a stage, say so and step up a size.

| Size | Typical task | Research default | Spec |
|---|---|---|---|
| S | One repo. The goal names the change. One pull request. No design choice. | quick | Short: Goal, Scope, Done when, Areas |
| M | One repo. Design choices exist. Up to 3 pull requests. | quick | Full |
| L | Several repos, an area the session does not know, or more than 3 pull requests | deep | Full. The plan can propose a split into child items |

## Rules for every size

- The spec writer runs for every size.
- The validator runs for every size.
- One work item per run. When a goal holds several independent projects, say so, agree an order with
  the owner, and run them one at a time. A split into child items is a later design.

## Research depth

| Depth | What runs | Output |
|---|---|---|
| none | No research step. The plan uses the goal and the files the goal names. | — |
| quick | The main session reads the code. At most one Explore subagent. | `research/notes.md`, one page or less |
| deep | The main session writes `research/questions.md`. Then the repo researcher and the outside researcher run in parallel. | `research/questions.md`, `research/repo.md`, `research/outside.md` |

- The owner can set the depth at intake (`depth=none|quick|deep`) or in any reply.
- Deep research needs the owner's yes at intake, because it costs more and takes longer.

## Subagent count

S and M run 2 or 3 subagents (spec writer, validator, maybe one Explore). L runs about 4. The tracker
connector adds 1 when the item has a tracker key.
