#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../_fixtures/lib.sh"
mkdir -p samples/demo-site
cp -R "$SAMPLES/demo-site/." samples/demo-site/
sed -i.bak "s|href=\"/about.html\">About|href=\"/abuot.html\">About|" samples/demo-site/site/about.html && rm samples/demo-site/site/about.html.bak
cp -R "$(dirname "${BASH_SOURCE[0]}")/bugfix-about-link" samples/
