#!/usr/bin/env bash
# Runs the eval cases one at a time (live cases must not run in parallel: Arctic Shift is run by
# volunteers). Each case gets its own command, because only find-post is granted WebSearch and only
# injection-exfil runs its scaffold.
# Usage, from plugins/reddit:  evals/run-suite.sh [case ...]   (no argument: every case)
# Results: evals/results/<timestamp>/ per case, and a summary line per case in evals/results/suite.log.
set -u
cd "$(dirname "$0")/.."
cases=("$@")
if [ ${#cases[@]} -eq 0 ]; then
  cases=(write-refusal today-top no-such-sub injection injection-comment injection-hidden
         injection-shell injection-fetch injection-exfil archive-down
         share-link global-search find-subs search-syntax read-post thread-follow-up
         most-discussed trending keyboard find-post)
fi
mkdir -p evals/results
for c in "${cases[@]}"; do
  tools=("mcp__plugin_reddit_reddit__*")
  extra=()
  [ "$c" = "find-post" ] && tools+=(WebSearch)
  [ "$c" = "injection-exfil" ] && extra+=(--scaffold)  # writes a FAKE .env (see the case's fixture.sh)
  echo "=== $c $(date -u +%FT%TZ)" | tee -a evals/results/suite.log
  claude plugin eval . --case "$c" --allow-real-servers --allow-tools "${tools[@]}" \
    --trust-plugin --no-publish --judge-model sonnet --concurrency 1 ${extra[@]+"${extra[@]}"} \
    --json "evals/results/$c.json" > "evals/results/$c.log" 2>&1
  echo "exit $? $(date -u +%FT%TZ)" | tee -a evals/results/suite.log
  tail -25 "evals/results/$c.log" >> evals/results/suite.log
done
