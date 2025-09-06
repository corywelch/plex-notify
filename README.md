# Plex Notify (Twilio SMS + Auto-Restart)

A lightweight macOS utility that monitors your Plex Media Server, alerts you by SMS if it goes down, and optionally auto-restarts the service. Notifications are sent through [Twilio](https://www.twilio.com/).

---

## ✨ Features
- **Health monitoring**: checks both Plex process and HTTP API.
- **SMS alerts**: instant text if Plex is down.
- **Auto-restart**: attempts one restart when Plex goes down.
- **Cool-downs**:
  - `alert_cooldown_minutes` → minimum time between repeated "DOWN" alerts.
  - `retry_backoff_minutes` → minimum time between restart attempts.
  - `suppress_minutes_after_failed_retry` → silence window after a failed restart (prevents spam).
- **Recovery notice**: one-time SMS when Plex comes back up.
- **Timezone**: configurable (default UTC, can be set to ET with `zoneinfo`).

---

## 📂 Directory Structure
plex-notify/
├── plex_watch.py # Main monitoring + notification script
├── config.json.example # Sample config (copy to config.json and fill in)
├── state.json # Runtime state (auto-created, do not edit)
├── Setup Install Files/
│ ├── install_launchd.sh # Installer script for macOS launchd job
│ └── com.USER.plexwatch.plist.template

---

## ⚙️ Requirements
- macOS with `launchd`
- Python 3.9+ (built into macOS or installed via Homebrew)
- A Twilio account + SMS-enabled phone number

---

## 🚀 Installation
1. **Clone repo**  


2.