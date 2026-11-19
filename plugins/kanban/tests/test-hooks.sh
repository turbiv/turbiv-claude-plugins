#!/bin/sh
# Tests for hooks/session-log.sh. Run: sh plugins/kanban/tests/test-hooks.sh
# Prints one ok/FAIL line per check. Exits 1 when a check fails.

HERE=$(cd "$(dirname "$0")" && pwd)
HOOK="$HERE/../hooks/session-log.sh"
TMP=$(mktemp -d)
# macOS: /var is a link to /private/var. Use the real path, as the hook sees it.
TMP=$(cd "$TMP" && pwd -P)
trap 'chmod -R u+w "$TMP" 2>/dev/null; rm -rf "$TMP"' EXIT
FAILS=0
SAMPLE='{"session_id":"abc-123","transcript_path":"/tmp/t.jsonl","cwd":"/tmp/proj","hook_event_name":"SessionEnd","reason":"other"}'

ok()   { echo "ok   $1"; }
fail() { echo "FAIL $1"; FAILS=$((FAILS + 1)); }
check() { # check <name> <command...>
  name=$1; shift
  if "$@" >/dev/null 2>&1; then ok "$name"; else fail "$name"; fi
}
key() { printf %s "$1" | tr -c 'A-Za-z0-9' '-'; }

# run <data dir> <project dir> <event> : stdin is passed on.
# Leaves stdout in $TMP/out, stderr in $TMP/err, the exit code in $TMP/rc.
# (A file, not a variable: "echo x | run" runs the function in a subshell.)
run() {
  d=$1; p=$2; e=$3
  ( cd "$p" 2>/dev/null || cd /
    env -u CLAUDE_PLUGIN_DATA -u CLAUDE_PROJECT_DIR KANBAN_DATA_DIR="$d" HOME="$FAKEHOME" \
      sh "$HOOK" "$e" >"$TMP/out" 2>"$TMP/err"
    echo $? >"$TMP/rc" )
}
rc0() { [ "$(cat "$TMP/rc")" = 0 ]; }
quiet() { rc0 && [ ! -s "$TMP/out" ] && [ ! -s "$TMP/err" ]; }
quiet_err() { rc0 && [ ! -s "$TMP/err" ]; }
newdata() { D="$TMP/data$1"; mkdir -p "$D"; [ "$2" = "noconfig" ] || echo '{}' >"$D/config.json"; }

FAKEHOME="$TMP/home"; mkdir -p "$FAKEHOME"
PROJ="$FAKEHOME/git/proj"; mkdir -p "$PROJ/sub/deep" "$PROJ/.claude/worktrees/x"

# 1. No config: nothing happens.
newdata 1 noconfig
echo "$SAMPLE" | run "$D" "$PROJ" end
check "no config: end is quiet" quiet
check "no config: end writes no log" test ! -e "$D/pending.jsonl"
echo "$SAMPLE" | run "$D" "$PROJ" start
check "no config: start is quiet" quiet
check "no config: start writes no log" test ! -e "$D/pending.jsonl"

# 2. With config: one valid line.
newdata 2
echo "$SAMPLE" | run "$D" "$PROJ" end
check "end: exit 0, no output" quiet
check "end: one line" test "$(wc -l <"$D/pending.jsonl" | tr -d ' ')" = 1
check "end: line is JSON with ev, ts, dir and in" python3 -c '
import json, sys
d = json.loads(open(sys.argv[1]).read())
assert d["ev"] == "end", d
assert d["in"]["session_id"] == "abc-123", d
assert d["dir"] == sys.argv[2], d
assert d["ts"].endswith("Z") and len(d["ts"]) == 20, d
' "$D/pending.jsonl" "$PROJ"

# 3. Pretty-printed stdin becomes one line.
newdata 3
printf '{\n  "session_id": "multi",\n  "cwd": "/x"\n}\n' | run "$D" "$PROJ" end
check "multi-line stdin: one valid line" python3 -c '
import json, sys
lines = open(sys.argv[1]).read().splitlines()
assert len(lines) == 1
assert json.loads(lines[0])["in"]["session_id"] == "multi"
' "$D/pending.jsonl"

# 4. Empty stdin.
newdata 4
run "$D" "$PROJ" end </dev/null
check "empty stdin: in is null" python3 -c '
import json, sys
assert json.loads(open(sys.argv[1]).read())["in"] is None
' "$D/pending.jsonl"
check "empty stdin: quiet" quiet

# 5. A 5 MB stdin.
newdata 5
START=$(python3 -c 'import time; print(time.time())')
head -c 5000000 /dev/zero | tr '\0' 'a' | run "$D" "$PROJ" end
check "5 MB stdin: quiet" quiet
check "5 MB stdin: one line" test "$(wc -l <"$D/pending.jsonl" | tr -d ' ')" = 1
check "5 MB stdin: under 1 s" python3 -c "import time, sys; sys.exit(0 if time.time() - $START < 1 else 1)"
check "5 MB stdin: line is capped" test "$(wc -c <"$D/pending.jsonl" | tr -d ' ')" -lt 70000

# 6. A folder name with a quote and a backslash still gives valid JSON.
newdata 6
ODD="$FAKEHOME/od\"d\\dir"; mkdir -p "$ODD"
echo "$SAMPLE" | run "$D" "$ODD" end
check "odd folder name: valid JSON" python3 -c '
import json, sys
assert json.loads(open(sys.argv[1]).read())["dir"] == sys.argv[2]
' "$D/pending.jsonl" "$ODD"

# 7. Awkward data folders.
D="$TMP/data with space"; mkdir -p "$D"; echo '{}' >"$D/config.json"
echo "$SAMPLE" | run "$D" "$PROJ" end
check "space in data path: quiet" quiet
check "space in data path: logged" test -s "$D/pending.jsonl"
echo "$SAMPLE" | run "$D" "$PROJ" start
check "space in data path: start exit 0" rc0

newdata 7; chmod a-w "$D"
echo "$SAMPLE" | run "$D" "$PROJ" end
check "read-only data folder: end quiet" quiet
echo "$SAMPLE" | run "$D" "$PROJ" start
check "read-only data folder: start exit 0, no stderr" quiet_err
chmod u+w "$D"

echo "$SAMPLE" | run "$TMP/does-not-exist" "$PROJ" end
check "missing data folder: end quiet" quiet
echo "$SAMPLE" | run "$TMP/does-not-exist" "$PROJ" start
check "missing data folder: start quiet" quiet

( cd "$PROJ" && echo "$SAMPLE" | env -u CLAUDE_PLUGIN_DATA -u KANBAN_DATA_DIR sh "$HOOK" end >"$TMP/out" 2>"$TMP/err"; echo $? >"$TMP/rc" )
check "no data variable: quiet" quiet
( cd "$PROJ" && echo "$SAMPLE" | env -u CLAUDE_PLUGIN_DATA -u KANBAN_DATA_DIR sh "$HOOK" >"$TMP/out" 2>"$TMP/err"; echo $? >"$TMP/rc" )
check "no event argument: quiet" quiet

# 8. CLAUDE_PLUGIN_DATA is used when KANBAN_DATA_DIR is not set; CLAUDE_PROJECT_DIR wins over the cwd.
newdata 8
( cd / && echo "$SAMPLE" | env -u KANBAN_DATA_DIR CLAUDE_PLUGIN_DATA="$D" CLAUDE_PROJECT_DIR="$PROJ" HOME="$FAKEHOME" sh "$HOOK" end )
check "CLAUDE_PLUGIN_DATA and CLAUDE_PROJECT_DIR are used" python3 -c '
import json, sys
assert json.loads(open(sys.argv[1]).read())["dir"] == sys.argv[2]
' "$D/pending.jsonl" "$PROJ"

# 9. Start prints the context of the folder.
newdata 9
touch "$D/last-sync"
mkdir -p "$D/context/tree" "$D/context/exact"
echo "CARD-FOR-PROJ" >"$D/context/tree/$(key "$PROJ").txt"
echo "$SAMPLE" | run "$D" "$PROJ" start
check "start: prints the tree context" grep -q CARD-FOR-PROJ "$TMP/out"
check "start: logs a start line" grep -q '"ev":"start"' "$D/pending.jsonl"
echo "$SAMPLE" | run "$D" "$PROJ/sub/deep" start
check "start in a subfolder: prints the tree context" grep -q CARD-FOR-PROJ "$TMP/out"
echo "$SAMPLE" | run "$D" "$PROJ/.claude/worktrees/x" start
check "start in a worktree: prints the main repo's context" grep -q CARD-FOR-PROJ "$TMP/out"
check "start: no nudge after a fresh sync" sh -c "! grep -q 'not on the board' '$TMP/out'"

echo "EXACT-GIT" >"$D/context/exact/$(key "$FAKEHOME/git").txt"
echo "$SAMPLE" | run "$D" "$FAKEHOME/git" start
check "exact context: printed in that folder" grep -q EXACT-GIT "$TMP/out"
mkdir -p "$FAKEHOME/git/other"
echo "$SAMPLE" | run "$D" "$FAKEHOME/git/other" start
check "exact context: not printed in a subfolder" sh -c "! grep -q EXACT-GIT '$TMP/out'"

echo "HOME-CARD" >"$D/context/tree/$(key "$FAKEHOME").txt"
echo "$SAMPLE" | run "$D" "$FAKEHOME/git/other" start
check "home context: never printed below home" sh -c "! grep -q HOME-CARD '$TMP/out'"

# 10. The nudge.
newdata 10
echo "$SAMPLE" | run "$D" "$PROJ" end
echo "$SAMPLE" | run "$D" "$PROJ" end
echo "$SAMPLE" | run "$D" "$PROJ" start
check "nudge: names 2 sessions when never synced" grep -q 'kanban: 2 sessions are not on the board yet' "$TMP/out"
touch "$D/last-sync"
echo "$SAMPLE" | run "$D" "$PROJ" start
check "nudge: silent after a fresh sync" sh -c "! grep -q 'not on the board' '$TMP/out'"
touch -t 202001010000 "$D/last-sync"
echo "$SAMPLE" | run "$D" "$PROJ" start
check "nudge: back when the sync is old" grep -q 'not on the board yet' "$TMP/out"
newdata 11
touch -t 202001010000 "$D/last-sync"
echo "$SAMPLE" | run "$D" "$PROJ" start
check "nudge: silent with nothing pending" sh -c "! grep -q 'not on the board' '$TMP/out'"

# 11. Timing: 50 end runs.
newdata 12
START=$(python3 -c 'import time; print(time.time())')
i=0
while [ $i -lt 50 ]; do echo "$SAMPLE" | run "$D" "$PROJ" end; i=$((i + 1)); done
TOOK=$(python3 -c "import time; print(round(time.time() - $START, 2))")
check "timing: 50 end runs under 5 s (took ${TOOK} s)" python3 -c "import sys; sys.exit(0 if $TOOK < 5 else 1)"
check "timing: 50 lines logged" test "$(wc -l <"$D/pending.jsonl" | tr -d ' ')" = 50

echo
if [ "$FAILS" -eq 0 ]; then echo "all hook tests passed"; else echo "$FAILS hook tests FAILED"; exit 1; fi
