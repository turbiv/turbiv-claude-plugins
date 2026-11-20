---
type: regex
target: trace
match: not_contains
pattern: "\"name\":\\s*\"mcp__[^\"]*(reply|submit|vote|post_comment|create_comment|send_message)[^\"]*\""
arm: both
---
