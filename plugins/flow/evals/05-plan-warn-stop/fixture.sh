#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../_fixtures/lib.sh"
demo_repo
ID=20261118-deploy-fix
write_item "$ID" researched S quick "The demo site deploy fails since Monday. Make make deploy work again."
mkdir -p "work-items/$ID/research"
sed "s|@WS@|$WS|g" "$(dirname "${BASH_SOURCE[0]}")/notes.md" > "work-items/$ID/research/notes.md"
