#!/bin/sh
# kanban hook: records that a session started or ended.
# Usage: session-log.sh start|end   (the hook's JSON arrives on stdin)
#
# Rules, because SessionEnd hooks share a 1.5 s budget and must never
# break a session: plain sh, no jq, no python, no git, always exit 0,
# nothing on stderr. It appends one line to pending.jsonl. /kanban:sync
# does all the real work later.
exec 2>/dev/null

EV=$1
DATA=${KANBAN_DATA_DIR:-$CLAUDE_PLUGIN_DATA}
case "$EV" in start|end) ;; *) exit 0 ;; esac
[ -n "$DATA" ] || exit 0
# No config.json: /kanban:setup has not run. Do nothing.
[ -f "$DATA/config.json" ] || exit 0

DIR=${CLAUDE_PROJECT_DIR:-$PWD}

# --- Log one line -----------------------------------------------------
# Stdin is copied as it is: newlines removed, capped at 64 KB. Nothing is
# parsed here. A capped (so broken) line is handled by kanban-tool.
IN=$(head -c 65536 | tr -d '\n\r')
[ -n "$IN" ] || IN=null
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
ESC=$(printf %s "$DIR" | sed 's/\\/\\\\/g; s/"/\\"/g')
printf '{"ev":"%s","ts":"%s","dir":"%s","in":%s}\n' "$EV" "$TS" "$ESC" "$IN" >>"$DATA/pending.jsonl"

[ "$EV" = start ] || exit 0

# --- Session start: print the cards of this folder ---------------------
# Plain stdout of a SessionStart hook is added to Claude's context.
key() { printf %s "$1" | tr -c 'A-Za-z0-9' '-'; }

# A worktree counts as its main repo.
case "$DIR" in */.claude/worktrees/*) DIR=${DIR%%/.claude/worktrees/*} ;; esac

FOUND=
F="$DATA/context/exact/$(key "$DIR").txt"
if [ -f "$F" ]; then
  FOUND=$F
else
  # Walk up to the repo root. Never match the home folder or /.
  P=$DIR
  while [ -n "$P" ] && [ "$P" != / ] && [ "$P" != "$HOME" ]; do
    F="$DATA/context/tree/$(key "$P").txt"
    if [ -f "$F" ]; then FOUND=$F; break; fi
    case "$P" in */*) P=${P%/*} ;; *) break ;; esac
  done
fi
[ -n "$FOUND" ] && head -c 4000 "$FOUND"

# --- The nudge: sessions wait and the last sync is over 20 hours old ---
N=$(grep -c '"ev":"end"' "$DATA/pending.jsonl")
case "$N" in ''|*[!0-9]*) N=0 ;; esac
if [ "$N" -gt 0 ]; then
  if [ ! -f "$DATA/last-sync" ] || [ -n "$(find "$DATA/last-sync" -mmin +1200)" ]; then
    echo "kanban: $N sessions are not on the board yet. Tell the user once, in one line, that /kanban:sync updates it. Do not run it unasked."
  fi
fi
exit 0
