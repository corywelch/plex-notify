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
```
plex-notify/
├── plex_watch.py               # Main monitoring + notification script
├── config.json.example         # Sample config (copy to config.json and fill in)
├── state.json                  # Runtime state (auto-created, do not edit)
├── Setup Install Files/
│   ├── install_launchd.sh      # Installer script for macOS launchd job
│   └── com.USER.plexwatch.plist.template
```

---

## ⚙️ Requirements
- macOS with `launchd`
- Python 3.9+ (built into macOS or installed via Homebrew)
- A Twilio account + SMS-enabled phone number

---

## 🚀 Installation
1. **Clone repo**  
   ```bash
   git clone https://github.com/<your-username>/plex-notify.git
   cd plex-notify/Setup\ Install\ Files
   ```

2. **Prepare config**  
   ```bash
   cp ../config.json.example ../config.json
   nano ../config.json
   ```
   Fill in:
   - `account_sid`
   - `auth_token`
   - `from_number` (your Twilio number)
   - `to_number` (your cell phone)

3. **Install launchd job**  
   ```bash
   chmod +x install_launchd.sh
   ./install_launchd.sh
   ```

4. **Verify it’s running**  
   ```bash
   launchctl list | grep plexwatch
   tail -n 10 -f ~/plex-notify/plexwatch.out.log
   ```

---

## 🧪 Manual Testing
Run once manually:
```bash
/usr/bin/env python3 ~/plex-notify/plex_watch.py
```
- If Plex is running → log shows `Healthy.`  
- If Plex is down → SMS alert, auto-restart attempt, and either success or failure notice.  

---

## 🔧 Configuration
- All settings are in `config.json`.
- Changes take effect on the **next run** (no need to reload launchd).
- Example keys:
  ```json
  {
    "alert_cooldown_minutes": 60,
    "suppress_minutes_after_failed_retry": 120,
    "retry_backoff_minutes": 15
  }
  ```

---

## 📜 Logs
- `~/plex-notify/plexwatch.out.log` → normal logs  
- `~/plex-notify/plexwatch.err.log` → error logs  

Follow logs live:
```bash
tail -n 10 -f ~/plex-notify/plexwatch.out.log
```

---

## 🔐 Security
- **Never commit `config.json`** — it contains your Twilio SID and Auth Token.
- Use the provided `.gitignore` (gitignore.example).

---

## 🤝 Contributing
Feel free to fork, open issues, or submit PRs. This is a hobby project to improve Plex reliability with lightweight monitoring.

---

## 📄 License
MIT
