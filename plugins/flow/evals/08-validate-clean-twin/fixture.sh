#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../_fixtures/lib.sh"
mkdir -p samples && cp -R "$SAMPLES/demo-site" "$SAMPLES/deploy-done-line-clean" samples/
