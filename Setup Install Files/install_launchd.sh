#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_NAME="$(id -un)"
HOME_DIR="$HOME"
TARGET_DIR="$HOME_DIR/plex-notify"
PLIST_PATH="$HOME_DIR/Library/LaunchAgents/com.${USER_NAME}.appswatch.plist"

echo "Installing Apps Watch to: $TARGET_DIR"
mkdir -p "$TARGET_DIR"

# Copy python script from the parent folder of SCRIPT_DIR
cp -f "$SCRIPT_DIR/../apps_watch.py" "$TARGET_DIR/apps_watch.py"
chmod +x "$TARGET_DIR/apps_watch.py"

if [[ ! -f "$TARGET_DIR/config.json" ]]; then
  cp -n "$SCRIPT_DIR/config.json.example" "$TARGET_DIR/config.json"
  echo "Created $TARGET_DIR/config.json (fill in your Twilio creds and phone numbers)."
else
  echo "Preserving existing $TARGET_DIR/config.json"
fi

mkdir -p "$HOME_DIR/Library/LaunchAgents"
sed "s|__USER__|${USER_NAME}|g; s|__DIR__|${TARGET_DIR}|g" \
  "$SCRIPT_DIR/com.USER.appswatch.plist.template" > "$PLIST_PATH"

echo "Loading launchd job: $PLIST_PATH"
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load -w "$PLIST_PATH"

echo "Run a manual test:"
echo "  /usr/bin/python3 \"$TARGET_DIR/apps_watch.py\""
echo "Check logs at:"
echo "  $TARGET_DIR/appswatch.out.log"
echo "  $TARGET_DIR/appswatch.err.log"
