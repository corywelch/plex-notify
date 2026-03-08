# Plex Notify (Twilio SMS + Auto-Restart)

A lightweight macOS utility that monitors your Plex Media Server and other applications. It alerts you by SMS if a service goes down, and optionally attempts an auto-restart. Notifications are sent through [Twilio](https://www.twilio.com/).

---

## Features
- **Health monitoring**: Checks both the system process and the HTTP API (if configured). For web endpoints, it smartly treats both `2xx` success codes and `4xx` client errors (like 401 Unauthorized) as healthy, since hitting a 4xx error means the app server is up and responding; only true `5xx` server crashes or timeouts are flagged as down.
- **SMS alerts**: Instant text via Twilio if an application goes down.
- **Auto-restart**: Attempts an automated open command to restart applications when they are detected as down.
- **Multi-App Support**: Monitor Plex, SABnzbd, Prowlarr, Radarr, Sonarr, Lidoarr, and others simultaneously.
- **Cool-downs & Throttling**:
  - `alert_cooldown_minutes`: Minimum time between repeated "DOWN" alerts being sent to Twilio.
  - `retry_backoff_minutes`: Minimum time between auto-restart attempts.
  - `suppress_minutes_after_failed_retry`: Silence window after a failed restart (prevents spam and runaway loops).
- **Recovery notice**: One-time SMS alert sent when an application comes back online after being down.
- **Timezone Support**: Configurable timestamp outputs (default UTC, can be set to local time easily).

---

## Directory Structure
```text
plex-notify/
├── apps_watch.py               # Multi-app monitoring script
├── plex_watch.py               # Legacy Plex-only monitoring script
├── Setup Install Files/
│   ├── config.json.example     # Sample config (copy to config.json and fill in)
│   ├── install_launchd.sh      # Installer script for macOS launchd job (apps_watch)
│   ├── install_legacy_plex_launchd.sh # Legacy Installer script for plex_watch
│   ├── uninstall_apps_watch.sh # Uninstall script for apps_watch
│   ├── uninstall_plex_watch.sh # Uninstall script for plex_watch
│   ├── com.USER.appswatch.plist.template
│   ├── com.USER.plexwatch.plist.template
│   └── config_migration_guide.txt  # Guide for updating old config formats
```

*Note: Runtime state files like `state.json` are auto-created by the scripts. Do not edit them.*

---

## Requirements
- macOS with `launchd`
- Python 3.9+ (built into macOS or installed via Homebrew)
- A Twilio account and an SMS-enabled phone number

---

## Installation
1. **Clone repo**  
   ```bash
   git clone https://github.com/<your-username>/plex-notify.git
   cd plex-notify/Setup\ Install\ Files
   ```

2. **Prepare config**  
   ```bash
   cp config.json.example ../config.json
   nano ../config.json
   ```
   Fill in the `twilio` block, adjust `global_settings`, and enable desired `applications`.

3. **Install launchd job**  
   ```bash
   chmod +x install_launchd.sh
   ./install_launchd.sh
   ```

4. **Verify it is running**  
   ```bash
   launchctl list | grep appswatch
   tail -n 10 -f ~/plex-notify/appswatch.out.log
   ```

---

## Uninstallation & Legacy Setup
- To uninstall `apps_watch`, simply run `./uninstall_apps_watch.sh`.
- To uninstall an existing `plex_watch` installation (useful if migrating), run `./uninstall_plex_watch.sh`.
- If you prefer to use the legacy plex-only script (`plex_watch.py`), use `./install_legacy_plex_launchd.sh` to install it.

---

## Manual Testing
Run the script once manually:
```bash
/usr/bin/env python3 ~/plex-notify/apps_watch.py
```
- If applications are healthy: Log shows `Healthy.`  
- If an application is down: You will receive an SMS alert, an auto-restart attempt is made, followed by a success or failure notice based on the config settings. 

---

## How `launchd` Works (Background Service)
macOS uses a background service manager called `launchd`. The installation script creates a Property List (`.plist`) file containing the instructions on what script to run, and how often to run it (default is every 300 seconds, or 5 minutes).

Because the `.plist` instructs `launchd` to invoke `apps_watch.py` on a timer, **the script does not run a continuous `while True:` loop.** Instead, it is executed, completes its checks, saves its state to `state.json`, and exits. Five minutes later, `launchd` starts it again.

### Applying Configuration or Code Changes
If you modify `config.json` or update `apps_watch.py` directly, the changes will take effect automatically on the very next 5-minute interval! There is generally no need to restart anything.

However, if you edit `com.USER.appswatch.plist.template` or the interval settings, you must reload `launchctl` to apply the background task changes:
```bash
launchctl unload ~/Library/LaunchAgents/com.$(id -un).appswatch.plist
launchctl load -w ~/Library/LaunchAgents/com.$(id -un).appswatch.plist
```

---

## Configuration
- All settings are defined in `config.json`.
- Changes take effect on the next run.
- Review `config_migration_guide.txt` if upgrading from an older version.

---

## Logs
- Normal logs: `~/plex-notify/appswatch.out.log`
- Error logs: `~/plex-notify/appswatch.err.log`

Follow logs live:
```bash
tail -n 10 -f ~/plex-notify/appswatch.out.log
```

---

## Security
- **Never commit `config.json`** — it contains your Twilio SID and Auth Token.
- Use the provided `.gitignore` file (`gitignore.example`).

---

## Contributing
Feel free to fork, open issues, or submit PRs. This project provides a lightweight monitoring solution for home server applications.

---

## License
MIT
