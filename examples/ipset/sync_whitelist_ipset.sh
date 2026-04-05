#!/usr/bin/env sh
set -eu

# Example:
#   python -m google_apple_whitelist fetch --output-dir ./whitelist_output
#   python -m google_apple_whitelist render --input-dir ./whitelist_output --output-dir ./rendered_assets
#   sudo ./examples/ipset/sync_whitelist_ipset.sh ./rendered_assets/ipset/combined_google_services_plus_apple.restore

RESTORE_FILE=${1:-./rendered_assets/ipset/combined_google_services_plus_apple.restore}

if [ ! -f "$RESTORE_FILE" ]; then
  echo "restore file not found: $RESTORE_FILE" >&2
  exit 1
fi

ipset restore -exist < "$RESTORE_FILE"
echo "Applied ipset rules from: $RESTORE_FILE"
