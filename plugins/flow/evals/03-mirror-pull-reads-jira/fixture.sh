#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../_fixtures/lib.sh"
demo_repo
write_item "$FOOTER_ID" intake S none "$FOOTER_GOAL" TEST-1
