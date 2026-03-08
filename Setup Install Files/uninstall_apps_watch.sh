#!/usr/bin/env bash
set -euo pipefail

USER_NAME="$(id -un)"
HOME_DIR="$HOME"
TARGET_DIR="$HOME_DIR/plex-notify"
PLIST_PATH="$HOME_DIR/Library/LaunchAgents/com.${USER_NAME}.appswatch.plist"

echo "Uninstalling apps_watch launchd job..."

if launchctl list | grep -q "com.${USER_NAME}.appswatch"; then
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    echo "Unloaded com.${USER_NAME}.appswatch"
fi

if [[ -f "$PLIST_PATH" ]]; then
    rm "$PLIST_PATH"
    echo "Removed $PLIST_PATH"
fi

echo "Done. (Note: config and app files remain in $TARGET_DIR)"
