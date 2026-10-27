#!/usr/bin/env bash
# Build the site and run the test suite. Local verification only.
set -euo pipefail
cd "$(dirname "$0")"

echo "== build =="
python3 build.py

echo "== tests =="
python3 -m unittest discover -s tests -v

echo "OK: build + tests passed"
