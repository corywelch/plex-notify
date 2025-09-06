#!/usr/bin/env python3
"""
plex_watch.py
- Checks Plex health (process + HTTP endpoint)
- Auto-retries a restart once when DOWN (with restart backoff)
- Sends SMS via Twilio for: DOWN (after failed retry), UP (recovery), and auto-restart success/failure
- Suppresses repeated alerts after a failed retry for a configurable window, so you don't get spammed.
- Stores state in state.json beside this script.

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

BASE = pathlib.Path(__file__).resolve().parent
CFG_PATH = BASE / "config.json"
STATE_FILE = BASE / "state.json"

# -------- Utilities --------
def load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default

def save_json_atomic(path, obj):
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
    os.replace(tmp, path)

def now_ts():
    return int(time.time())

def iso_now():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def log(msg):
    print(f"[{iso_now()}] {msg}", flush=True)

# -------- Health checks --------
def plex_running_by_process(proc_name):
    try:
        res = subprocess.run(["pgrep", "-x", proc_name],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False

def plex_http_ok(url):
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return 200 <= r.status < 300
    except Exception:
        return False

# -------- Twilio SMS --------
def twilio_send_sms(cfg, body):
    account_sid = cfg["account_sid"]
    auth_token  = cfg["auth_token"]
    from_num    = cfg["from_number"]
    to_num      = cfg["to_number"]

    data = urllib.parse.urlencode({
        "To": to_num,
        "From": from_num,
        "Body": body
    }).encode("utf-8")

    req = urllib.request.Request(
        url=f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
        data=data,
        method="POST",
        headers={
            "Authorization": "Basic " + base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        r.read()

# -------- Main --------
def main():
    cfg = load_json(CFG_PATH, {})
    if not cfg:
        print("Missing config.json. Copy config.json.example to config.json and fill values.",
              file=sys.stderr)
        sys.exit(2)

    proc_name   = cfg.get("plex", {}).get("process_name", "Plex Media Server")
    health_url  = cfg.get("plex", {}).get("http_health_url", "http://127.0.0.1:32400/identity")
    alert_cd_s  = int(cfg.get("alert_cooldown_minutes", 60)) * 60
    suppress_s  = int(cfg.get("suppress_minutes_after_failed_retry", 120)) * 60
    restart_cd_s= int(cfg.get("retry_backoff_minutes", 15)) * 60

    state = load_json(STATE_FILE, {
        "last_alert_ts": 0,
        "was_down": False,
        "suppress_until_ts": 0,
        "last_restart_ts": 0
    })
    tnow = now_ts()

    running = plex_running_by_process(proc_name)
    http_ok = plex_http_ok(health_url)
    healthy = running and http_ok

    def send_alert(msg, use_cooldown=True):
        nonlocal state, tnow, alert_cd_s
        if (not use_cooldown or
            (tnow - state.get("last_alert_ts", 0) >= alert_cd_s) or
            (state.get("was_down") is False)):
            twilio_send_sms(cfg, msg)
            state["last_alert_ts"] = tnow
            return True
        return False

    if healthy:
        if state.get("was_down"):
            twilio_send_sms(cfg, f"[{iso_now()}] OK: Plex is back UP.")
        state["was_down"] = False
        state["suppress_until_ts"] = 0
        save_json_atomic(STATE_FILE, state)
        log("Healthy.")
        return 0

    # Not healthy
    state["was_down"] = True

    # Suppression window active?
    if tnow < int(state.get("suppress_until_ts", 0)):
        log("Down, but in suppression window. No alert/retry.")
        save_json_atomic(STATE_FILE, state)
        return 0

    # Eligible for auto-restart attempt?
    if tnow - int(state.get("last_restart_ts", 0)) >= restart_cd_s:
        log("Attempting auto-restart...")
        try:
            subprocess.run(["open", "-a", "Plex Media Server"], check=False)
        except Exception as e:
            log(f"Restart attempt error: {e}")

        time.sleep(8)

        running2 = plex_running_by_process(proc_name)
        http_ok2 = plex_http_ok(health_url)
        healthy2 = running2 and http_ok2

        state["last_restart_ts"] = tnow

        if healthy2:
            twilio_send_sms(cfg, f"[{iso_now()}] INFO: Plex was down but auto-restart succeeded.")
            state["was_down"] = False
            save_json_atomic(STATE_FILE, state)
            log("Auto-restart succeeded.")
            return 0
        else:
            send_alert(f"[{iso_now()}] ALERT: Plex is DOWN. Auto-restart attempted and FAILED.",
                       use_cooldown=False)
            state["suppress_until_ts"] = tnow + suppress_s
            save_json_atomic(STATE_FILE, state)
            log("Auto-restart failed; entering suppression window.")
            return 1
    else:
        sent = send_alert(f"[{iso_now()}] ALERT: Plex appears DOWN on Mac mini.",
                          use_cooldown=True)
        save_json_atomic(STATE_FILE, state)
        log("Down; restart backoff window active. Alert sent?" + ("yes" if sent else "no"))
        return 1

if __name__ == "__main__":
    sys.exit(main())
