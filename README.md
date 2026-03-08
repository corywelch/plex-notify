# Plex Notify (Twilio SMS + Auto-Restart)

A lightweight macOS utility that monitors your Plex Media Server and other applications. It alerts you by SMS if a service goes down, and optionally attempts an auto-restart. Notifications are sent through [Twilio](https://www.twilio.com/).

---

## Features
- **Health monitoring**: Checks both process and HTTP API.
- **SMS alerts**: Instant text if an application is down.
- **Auto-restart**: Attempts one restart when an application goes down.
- **Multi-App Support**: Monitor Plex, SABnzbd, Prowlarr, Radarr, Sonarr, and more simultaneously.
- **Cool-downs**:
  - `alert_cooldown_minutes`: Minimum time between repeated "DOWN" alerts.
  - `retry_backoff_minutes`: Minimum time between restart attempts.
  - `suppress_minutes_after_failed_retry`: Silence window after a failed restart (prevents spam).
- **Recovery notice**: One-time SMS when an application comes back up.
- **Timezone**: Configurable (default UTC, can be set to ET with `zoneinfo`).

---

## Directory Structure
```text
plex-notify/
├── apps_watch.py               # Multi-app monitoring script
├── plex_watch.py               # Legacy Plex-only monitoring script
├── config_migration_guide.txt  # Guide for updating old config formats
├── Setup Install Files/
│   ├── config.json.example     # Sample config (copy to config.json and fill in)
│   ├── install_launchd.sh      # Installer script for macOS launchd job (apps_watch)
│   ├── install_legacy_plex_launchd.sh # Legacy Installer script for plex_watch
│   ├── uninstall_apps_watch.sh # Uninstall script for apps_watch
│   ├── uninstall_plex_watch.sh # Uninstall script for plex_watch
│   ├── com.USER.appswatch.plist.template
│   └── com.USER.plexwatch.plist.template
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
- If an application is down: You will receive an SMS alert, an auto-restart attempt is made, followed by a success or failure notice.  

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
