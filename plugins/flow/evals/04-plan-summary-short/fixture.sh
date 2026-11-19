#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../_fixtures/lib.sh"
demo_repo
write_item "$FOOTER_ID" intake S none "Add a footer to the demo site home page with the contact address info@example.com."
