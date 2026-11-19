#!/usr/bin/env bash
# Static checks for the flow plugin. No model calls, no cost.
# Usage: plugins/flow/evals/static/check.sh   (from any folder)
# Exit 0 when every check passes, 1 when one fails.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 1
fails=0

pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; fails=$((fails + 1)); }

# Value of one front-matter key in a Markdown file (first front-matter block only).
fm() { awk -v k="$2" 'NR==1 && $0!="---"{exit} /^---$/{n++; if(n==2) exit; next} n==1 && index($0, k":")==1 {sub("^" k ":[ ]*", ""); print; exit}' "$1"; }

# Sorted, one-per-line tool list of an agent file.
tools_of() { fm "$1" tools | tr ',' '\n' | sed 's/^ *//; s/ *$//' | grep -v '^$' | sort; }

expect_tools() {  # agent, expected tools (space separated)
  local agent="$1"; shift
  local want got
  want="$(printf '%s\n' "$@" | sort)"
  got="$(tools_of "agents/$agent.md")"
  if [ "$want" = "$got" ]; then pass "$agent tools are exactly: $*"
  else fail "$agent tools are '$(echo $got)', expected '$*'"; fi
}

# 1. plugin.json lists every agent file, and every listed file exists.
listed="$(grep -o '"\./agents/[^"]*"' .claude-plugin/plugin.json | tr -d '"' | sed 's|^\./||' | sort)"
present="$(ls agents/*.md | sort)"
if [ "$listed" = "$present" ]; then pass "plugin.json lists every agent, and only existing ones"
else fail "plugin.json agents differ from agents/*.md: listed [$(echo $listed)] present [$(echo $present)]"; fi

# 2. Agent tool lists (design section 9).
expect_tools spec-validator Read Glob Grep
expect_tools spec-writer Read Glob Grep Write
expect_tools repo-researcher Read Glob Grep

if [ "$(fm agents/spec-validator.md omitClaudeMd)" = "true" ]; then pass "spec-validator has omitClaudeMd: true"
else fail "spec-validator lacks omitClaudeMd: true"; fi

# tracker-jira: Read, Write and the three Jira read tools under the two server prefixes. Nothing else.
tj_bad="$(tools_of agents/tracker-jira.md | grep -v -x -E 'Read|Write|mcp__(atlassian|claude_ai_Atlassian)__(getAccessibleAtlassianResources|getJiraIssue|listJiraIssueComments)')"
tj_count="$(tools_of agents/tracker-jira.md | grep -c '^mcp__')"
if [ -z "$tj_bad" ] && [ "$tj_count" = "6" ]; then pass "tracker-jira has Read, Write and 6 Jira read tools only"
else fail "tracker-jira tools: unexpected [$(echo $tj_bad)], Jira tool count $tj_count (expected 6)"; fi

# outside-researcher: web and Atlassian read tools only. No shell, no file writes, no Atlassian write.
or_bad="$(tools_of agents/outside-researcher.md | grep -v -x -E 'WebSearch|WebFetch|mcp__[A-Za-z_-]+__(search|searchJiraIssuesUsingJql|searchConfluenceUsingCql|searchConfluence|getJiraIssue|getConfluencePage|getConfluenceContent|getAccessibleAtlassianResources|fetch)')"
if [ -z "$or_bad" ]; then pass "outside-researcher has web and Atlassian read tools only"
else fail "outside-researcher has other tools: $(echo $or_bad)"; fi

# 3. No Jira or Confluence write tool name anywhere in the plugin's runtime text (version 1 reads only).
write_names='createJiraIssue|editJiraIssue|addCommentToJiraIssue|addOrEditJiraIssueComment|transitionJiraIssue|addWorklogToJiraIssue|uploadAttachmentToJiraIssue|executeWrite|executeDestructive|createConfluencePage|updateConfluencePage|createConfluenceContent|updateConfluenceContent|createConfluenceFooterComment|createConfluenceInlineComment'
hits="$(grep -rn -E "$write_names" skills agents resources .claude-plugin 2>/dev/null)"
if [ -z "$hits" ]; then pass "no Jira or Confluence write tool is named in skills, agents or resources"
else fail "Jira or Confluence write tool named: $hits"; fi

# 4. mirror push is a stub in version 1.
if grep -q 'Push to Jira comes in version 2' skills/mirror/SKILL.md; then pass "mirror push is the version 2 stub"
else fail "skills/mirror/SKILL.md lacks the 'Push to Jira comes in version 2' stub"; fi

# 5. No picker dialogs: every line that names AskUserQuestion forbids it.
# A wrapped sentence can put the prohibition on the line before, so look at both lines.
ask_bad="$(find skills agents resources -name '*.md' -exec awk '
  /AskUserQuestion/ { if (tolower($0 " " prev) !~ /never|not |no picker/) print FILENAME ":" FNR ": " $0 }
  { prev = $0 }' {} +)"
if [ -z "$ask_bad" ]; then pass "AskUserQuestion is named only to forbid it"
else fail "AskUserQuestion named without a prohibition: $ask_bad"; fi

# 6. Skills: front matter, size, invocation.
for f in skills/*/SKILL.md; do
  name="$(fm "$f" name)"; desc="$(fm "$f" description)"
  dir="$(basename "$(dirname "$f")")"
  if [ "$name" != "$dir" ]; then fail "$f: name '$name' differs from its folder"; fi
  if [ -z "$desc" ] || [ "${#desc}" -gt 1024 ]; then fail "$f: description empty or over 1024 characters"; fi
  size="$(wc -c < "$f" | tr -d ' ')"
  # Claude Code re-attaches an invoked skill cut at 20,000 characters after compaction.
  if [ "$size" -ge 20000 ]; then fail "$f is $size bytes (limit 20000)"; fi
  dmi="$(fm "$f" disable-model-invocation)"
  if [ "$dir" != "start" ] && [ "$dmi" = "true" ]; then
    fail "$f has disable-model-invocation: true, but start calls it with the Skill tool"
  fi
done
pass "skills: names match folders, descriptions set, each under 20000 bytes, stage skills model-invocable"

if [ "$(fm skills/start/SKILL.md disable-model-invocation)" = "true" ]; then pass "start has disable-model-invocation: true (owner decision M4)"
else fail "start lacks disable-model-invocation: true"; fi

# 7. No scenario or development files inside skills/ (agents read them as live instructions).
dev="$(find skills -type f \( -name 'CREATION-LOG.md' -o -name 'test-*' -o -name '*.eval.*' -o -path '*/evals/*' \))"
if [ -z "$dev" ]; then pass "no test scenarios or creation logs inside skills/"
else fail "development files inside skills/: $dev"; fi

# 8. Every resource path named with ${CLAUDE_PLUGIN_ROOT} exists.
missing=""
while IFS= read -r p; do
  rel="${p#\$\{CLAUDE_PLUGIN_ROOT\}/}"
  rel="${rel%%[\`\)\,\.:]}"
  [ -e "$rel" ] || missing="$missing $rel"
done < <(grep -rhoE '\$\{CLAUDE_PLUGIN_ROOT\}/[A-Za-z0-9_./-]+' skills agents | sed 's/[.,:]$//' | sort -u)
if [ -z "$missing" ]; then pass "every \${CLAUDE_PLUGIN_ROOT} path in skills and agents exists"
else fail "missing resource paths:$missing"; fi

# 9. The plan summary template fits the 10-line limit and ends with "More: plan.md".
tpl_lines="$(grep -v '^<!--' resources/templates/plan-summary.md | grep -c .)"
tpl_last="$(grep -v '^<!--' resources/templates/plan-summary.md | grep . | tail -1)"
if [ "$tpl_lines" -le 10 ] && [ "$tpl_last" = "More: plan.md" ]; then pass "plan summary template: $tpl_lines lines, ends with More: plan.md"
else fail "plan summary template: $tpl_lines lines, last line '$tpl_last'"; fi

# 10. No eval cases inside the plugin's runtime folders (a run must not see them).
if [ -z "$(find skills agents resources -name 'prompt.md' -o -name 'case.yaml' 2>/dev/null)" ]; then pass "no eval case files outside evals/"
else fail "eval case files outside evals/"; fi

echo
if [ "$fails" -eq 0 ]; then echo "All static checks passed."; exit 0
else echo "$fails static check(s) failed."; exit 1; fi
