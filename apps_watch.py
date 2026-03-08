#!/usr/bin/env python3
"""
apps_watch.py
- Checks application health (process + HTTP endpoint) for multiple services
- Auto-retries a restart once when DOWN (with restart backoff) per service
- Sends SMS via Twilio for: DOWN (after failed retry), UP (recovery), and auto-restart success/failure
- Stores state in state.json beside this script.

Run: /usr/bin/python3 apps_watch.py
"""

import os
import sys
import json
import time
import subprocess
import base64
import urllib.request
import urllib.parse
import datetime
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
STATE_FILE = BASE_DIR / "state.json"

# -------- Utilities --------
def load_json(path, default_value: dict) -> dict:
    try:
        with open(path, "r") as json_file:
            data = json.load(json_file)
            if isinstance(data, dict):
                return data
            return default_value
    except Exception:
        return default_value

def save_json_atomic(path, obj):
    temp_path = path.with_suffix(".tmp")
    with open(temp_path, "w") as temp_file:
        json.dump(obj, temp_file, indent=2, sort_keys=True)
    os.replace(temp_path, path)

def get_current_timestamp():
    return int(time.time())

def get_iso_timestamp():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def log_message(app_name, message):
    print(f"[{get_iso_timestamp()}] [{app_name}] {message}", flush=True)

# -------- Health checks --------
def is_process_running(process_name):
    try:
        result = subprocess.run(["pgrep", "-x", process_name],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        return result.returncode == 0
    except Exception:
        return False

def is_http_endpoint_ok(url):
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            return 200 <= response.status < 300
    except Exception:
        return False

# -------- Twilio SMS --------
def send_twilio_sms(twilio_config, body_text):
    account_sid = twilio_config.get("account_sid")
    auth_token  = twilio_config.get("auth_token")
    from_number = twilio_config.get("from_number")
    to_number   = twilio_config.get("to_number")

    if not all([account_sid, auth_token, from_number, to_number]):
        print(f"[{get_iso_timestamp()}] Twilio config incomplete. Skipping SMS.")
        return

    data = urllib.parse.urlencode({
        "To": to_number,
        "From": from_number,
        "Body": body_text
    }).encode("utf-8")

    request_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    request = urllib.request.Request(
        url=request_url,
        data=data,
        method="POST",
        headers={
            "Authorization": "Basic " + base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        response.read()

# -------- Main --------
def main():
    config = load_json(CONFIG_PATH, {})
    if not config:
        print("Missing config.json. Copy config.json.example to config.json and fill values.",
              file=sys.stderr)
        sys.exit(2)

    global_settings = config.get("global_settings", {})
    applications_config = config.get("applications", {})
    twilio_config = config.get("twilio", {})

    if not applications_config:
        print("No applications defined in config. Exiting.", file=sys.stderr)
        return 0

    alert_cooldown_sec = int(global_settings.get("alert_cooldown_minutes", 60)) * 60
    suppress_duration_sec = int(global_settings.get("suppress_minutes_after_failed_retry", 120)) * 60
    restart_backoff_sec = int(global_settings.get("retry_backoff_minutes", 15)) * 60

    # state.json structure is now: { "plex": { "was_down": ... }, "sabnzbd": { ... } }
    state: dict = load_json(STATE_FILE, {})
    current_time = get_current_timestamp()

    overall_exit_code = 0

    for app_name, app_config in applications_config.items():
        if not app_config.get("enabled", False):
            continue

        process_name = app_config.get("process_name", app_name)
        health_url = app_config.get("http_health_url")
        enable_auto_restart = app_config.get("auto_restart", False)
        enable_text_notify = app_config.get("text_notify", False)

        if app_name not in state:
            state[app_name] = {
                "last_alert_ts": 0,
                "was_down": False,
                "suppress_until_ts": 0,
                "last_restart_ts": 0
            }

        app_state = state[app_name]

        is_running = is_process_running(process_name)
        
        # If no URL is provided, we just rely on process check
        is_http_ok = is_http_endpoint_ok(health_url) if health_url else True
        is_healthy = is_running and is_http_ok

        def send_alert(message_body, apply_cooldown=True):
            if not enable_text_notify:
                return False

            if (not apply_cooldown or
                (current_time - app_state.get("last_alert_ts", 0) >= alert_cooldown_sec) or
                (app_state.get("was_down") is False)):
                send_twilio_sms(twilio_config, message_body)
                app_state["last_alert_ts"] = current_time
                return True
            return False

        if is_healthy:
            if app_state.get("was_down"):
                send_alert(f"[{get_iso_timestamp()}] OK: {app_name} is back UP.")
            app_state["was_down"] = False
            app_state["suppress_until_ts"] = 0
            log_message(app_name, "Healthy.")
            continue

        # Not healthy
        app_state["was_down"] = True
        overall_exit_code = 1

        # Suppression window active?
        if current_time < int(app_state.get("suppress_until_ts", 0)):
            log_message(app_name, "Down, but in suppression window. No alert/retry.")
            continue

        # Eligible for auto-restart attempt?
        if enable_auto_restart and (current_time - int(app_state.get("last_restart_ts", 0)) >= restart_backoff_sec):
            log_message(app_name, "Attempting auto-restart...")
            try:
                subprocess.run(["open", "-a", process_name], check=False)
            except Exception as error:
                log_message(app_name, f"Restart attempt error: {error}")

            time.sleep(8)

            is_running_retry = is_process_running(process_name)
            is_http_ok_retry = is_http_endpoint_ok(health_url) if health_url else True
            is_healthy_retry = is_running_retry and is_http_ok_retry

            app_state["last_restart_ts"] = current_time

            if is_healthy_retry:
                send_alert(f"[{get_iso_timestamp()}] INFO: {app_name} was down but auto-restart succeeded.")
                app_state["was_down"] = False
                log_message(app_name, "Auto-restart succeeded.")
                continue
            else:
                send_alert(f"[{get_iso_timestamp()}] ALERT: {app_name} is DOWN. Auto-restart attempted and FAILED.",
                           apply_cooldown=False)
                app_state["suppress_until_ts"] = current_time + suppress_duration_sec
                log_message(app_name, "Auto-restart failed; entering suppression window.")
                continue
        else:
            alert_sent = send_alert(f"[{get_iso_timestamp()}] ALERT: {app_name} appears DOWN.",
                                    apply_cooldown=True)
            log_message(app_name, "Down; restart backoff window active (or restart disabled). Alert sent? " + ("yes" if alert_sent else "no"))

    save_json_atomic(STATE_FILE, state)
    return overall_exit_code

if __name__ == "__main__":
    sys.exit(main())
