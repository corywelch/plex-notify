#!/usr/bin/env python3
"""
plex_watch.py
- Checks Plex health (process + HTTP endpoint) [legacy script, Plex only]
- Auto-retries a restart once when DOWN (with restart backoff)
- Sends SMS via Twilio for: DOWN (after failed retry), UP (recovery), and auto-restart success/failure
- Suppresses repeated alerts after a failed retry for a configurable window, so you don't get spammed.
- Stores state in state_plex.json beside this script.

Run: /usr/bin/python3 plex_watch.py
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
STATE_FILE = BASE_DIR / "state_plex.json"

# -------- Utilities --------
def load_json(path, default_value):
    try:
        with open(path, "r") as json_file:
            return json.load(json_file)
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

def log_message(message):
    print(f"[{get_iso_timestamp()}] {message}", flush=True)

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
        log_message("Twilio configuration is incomplete. Skipping SMS.")
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

    plex_config = applications_config.get("plex")
    if not plex_config or not plex_config.get("enabled", False):
        log_message("Plex is not configured or not enabled. Exiting.")
        return 0

    process_name = plex_config.get("process_name", "Plex Media Server")
    health_url = plex_config.get("http_health_url", "http://127.0.0.1:32400/identity")
    enable_auto_restart = plex_config.get("auto_restart", False)
    enable_text_notify = plex_config.get("text_notify", False)
    
    alert_cooldown_sec = int(global_settings.get("alert_cooldown_minutes", 60)) * 60
    suppress_duration_sec = int(global_settings.get("suppress_minutes_after_failed_retry", 120)) * 60
    restart_backoff_sec = int(global_settings.get("retry_backoff_minutes", 15)) * 60

    state = load_json(STATE_FILE, {
        "last_alert_ts": 0,
        "was_down": False,
        "suppress_until_ts": 0,
        "last_restart_ts": 0
    })
    
    current_time = get_current_timestamp()

    is_running = is_process_running(process_name)
    is_http_ok = is_http_endpoint_ok(health_url)
    is_healthy = is_running and is_http_ok

    def send_alert(message_body, apply_cooldown=True):
        nonlocal state, current_time, alert_cooldown_sec, enable_text_notify
        if not enable_text_notify:
            return False

        if (not apply_cooldown or
            (current_time - state.get("last_alert_ts", 0) >= alert_cooldown_sec) or
            (state.get("was_down") is False)):
            send_twilio_sms(twilio_config, message_body)
            state["last_alert_ts"] = current_time
            return True
        return False

    if is_healthy:
        if state.get("was_down"):
            send_alert(f"[{get_iso_timestamp()}] OK: Plex is back UP.")
        state["was_down"] = False
        state["suppress_until_ts"] = 0
        save_json_atomic(STATE_FILE, state)
        log_message("Plex is Healthy.")
        return 0

    # Not healthy
    state["was_down"] = True

    # Suppression window active?
    if current_time < int(state.get("suppress_until_ts", 0)):
        log_message("Plex is Down, but in suppression window. No alert/retry.")
        save_json_atomic(STATE_FILE, state)
        return 0

    # Eligible for auto-restart attempt?
    if enable_auto_restart and (current_time - int(state.get("last_restart_ts", 0)) >= restart_backoff_sec):
        log_message("Attempting auto-restart for Plex...")
        try:
            subprocess.run(["open", "-a", process_name], check=False)
        except Exception as error:
            log_message(f"Restart attempt error: {error}")

        time.sleep(8)

        is_running_retry = is_process_running(process_name)
        is_http_ok_retry = is_http_endpoint_ok(health_url)
        is_healthy_retry = is_running_retry and is_http_ok_retry

        state["last_restart_ts"] = current_time

        if is_healthy_retry:
            send_alert(f"[{get_iso_timestamp()}] INFO: Plex was down but auto-restart succeeded.")
            state["was_down"] = False
            save_json_atomic(STATE_FILE, state)
            log_message("Auto-restart succeeded for Plex.")
            return 0
        else:
            send_alert(f"[{get_iso_timestamp()}] ALERT: Plex is DOWN. Auto-restart attempted and FAILED.",
                       apply_cooldown=False)
            state["suppress_until_ts"] = current_time + suppress_duration_sec
            save_json_atomic(STATE_FILE, state)
            log_message("Auto-restart failed for Plex; entering suppression window.")
            return 1
    else:
        alert_sent = send_alert(f"[{get_iso_timestamp()}] ALERT: Plex appears DOWN.",
                                apply_cooldown=True)
        save_json_atomic(STATE_FILE, state)
        log_message("Plex is Down; restart backoff window active (or restart disabled). Alert sent? " + ("yes" if alert_sent else "no"))
        return 1

if __name__ == "__main__":
    sys.exit(main())
