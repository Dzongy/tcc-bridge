#!/usr/bin/env python3
"""
Zenith Health Watchdog v1.2
Infinite loop monitoring all PM2 processes.
Auto-heals stopped/errored processes, memory leak protection,
restart flood detection, knowledge_base.json staleness check.
Runs as: pm2 start sovereignty/watchdog.py --name watchdog --interpreter python3
"""

import subprocess
import json
import os
import time
import datetime
import sys

# === CONFIG ===
CHECK_INTERVAL = 30
STATUS_WRITE_INTERVAL = 600
KB_CHECK_INTERVAL = 300
KB_STALE_THRESHOLD = 1800
MEMORY_LIMIT_MB = 500
RESTART_FLOOD_LIMIT = 50
RESTART_FLOOD_WINDOW = 3600

HEALTH_LOG = "sovereignty/health.log"
HEALTH_STATUS = "sovereignty/health_status.json"
KB_PATH = "knowledge_base.json"

MANAGED_PROCESSES = {
 "mega": {
  "script": "sovereignty/mega_harvester.py",
  "interpreter": "python3"
 },
 "agi": {
  "script": "sovereignty/zenith_agi_core.py",
  "interpreter": "python3"
 },
 "action": {
  "script": "sovereignty/action_dispatcher.py",
  "interpreter": "python3"
 },
 "patrol": {
  "script": "sovereignty/health_patrol.py",
  "interpreter": "python3"
 }
}

# === STATE ===
last_status_write = 0
last_kb_check = 0
last_kb_size = -1
last_kb_change_time = 0
restart_history = {}


def now_str():
 return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg, level="INFO"):
 line = "[%s] [%s] %s" % (now_str(), level, msg)
 print(line)
 try:
  with open(HEALTH_LOG, "a") as f:
   f.write(line + "\n")
 except Exception:
  pass


def get_pm2_list():
 try:
  result = subprocess.run(
   ["pm2", "jlist"],
   capture_output=True,
   text=True,
   timeout=15
  )
  if result.returncode != 0:
   log("pm2 jlist failed: " + str(result.stderr), "WARN")
   return None
  data = json.loads(result.stdout)
  return data
 except Exception as e:
  log("pm2 jlist exception: " + str(e), "ERROR")
  return None


def find_process(pm2_list, name):
 if pm2_list is None:
  return None
 for proc in pm2_list:
  pname = proc.get("name", "")
  if pname == name:
   return proc
 return None


def get_process_status(proc):
 try:
  env = proc.get("pm2_env", {})
  status = env.get("status", "unknown")
  return status
 except Exception:
  return "unknown"


def get_memory_mb(proc):
 try:
  monit = proc.get("monit", {})
  mem_bytes = monit.get("memory", 0)
  return mem_bytes / (1024 * 1024)
 except Exception:
  return 0


def get_restart_count(proc):
 try:
  env = proc.get("pm2_env", {})
  return env.get("restart_time", 0)
 except Exception:
  return 0


def get_uptime_ms(proc):
 try:
  env = proc.get("pm2_env", {})
  uptime = env.get("pm_uptime", 0)
  if uptime > 0:
   return int(time.time() * 1000) - uptime
  return 0
 except Exception:
  return 0


def restart_process(name):
 log("Restarting process: " + name, "WARN")
 try:
  result = subprocess.run(
   ["pm2", "restart", name],
   capture_output=True,
   text=True,
   timeout=30
  )
  if result.returncode == 0:
   log("Process restarted OK: " + name)
   track_restart(name)
  else:
   log("Restart failed for " + name + ": " + str(result.stderr), "ERROR")
 except Exception as e:
  log("Restart exception for " + name + ": " + str(e), "ERROR")


def create_process(name, config):
 script = config["script"]
 interp = config["interpreter"]
 log("Creating process: " + name + " (" + script + ")", "WARN")
 try:
  result = subprocess.run(
   ["pm2", "start", script, "--name", name, "--interpreter", interp],
   capture_output=True,
   text=True,
   timeout=30
  )
  if result.returncode == 0:
   log("Process created OK: " + name)
  else:
   log("Create failed for " + name + ": " + str(result.stderr), "ERROR")
 except Exception as e:
  log("Create exception for " + name + ": " + str(e), "ERROR")


def track_restart(name):
 now = time.time()
 if name not in restart_history:
  restart_history[name] = []
 restart_history[name].append(now)
 cutoff = now - RESTART_FLOOD_WINDOW
 restart_history[name] = [t for t in restart_history[name] if t > cutoff]


def check_restart_flood(name):
 now = time.time()
 if name not in restart_history:
  return False
 cutoff = now - RESTART_FLOOD_WINDOW
 restart_history[name] = [t for t in restart_history[name] if t > cutoff]
 count = len(restart_history[name])
 if count >= RESTART_FLOOD_LIMIT:
  log(
   "CRITICAL: Process " + name + " restarted " + str(count) +
   " times in last hour! Possible crash loop.",
   "CRITICAL"
  )
  return True
 return False


def check_knowledge_base():
 global last_kb_size, last_kb_change_time
 try:
  if not os.path.exists(KB_PATH):
   log("knowledge_base.json not found", "WARN")
   return "missing"
  size = os.path.getsize(KB_PATH)
  now = time.time()
  if last_kb_size < 0:
   last_kb_size = size
   last_kb_change_time = now
   return "ok"
  if size != last_kb_size:
   last_kb_size = size
   last_kb_change_time = now
   return "growing"
  stale_seconds = now - last_kb_change_time
  if stale_seconds >= KB_STALE_THRESHOLD:
   log(
    "knowledge_base.json stale for " +
    str(int(stale_seconds)) + "s, restarting mega",
    "WARN"
   )
   last_kb_change_time = now
   return "stale"
  return "ok"
 except Exception as e:
  log("KB check error: " + str(e), "ERROR")
  return "error"


def determine_health(statuses):
 has_red = False
 has_yellow = False
 for name in statuses:
  s = statuses[name]
  if s.get("status") in ("stopped", "errored", "not_found"):
   has_red = True
  elif s.get("memory_mb", 0) > MEMORY_LIMIT_MB * 0.8:
   has_yellow = True
  elif s.get("restart_flood", False):
   has_red = True
 if has_red:
  return "RED"
 if has_yellow:
  return "YELLOW"
 return "GREEN"


def write_health_status(statuses):
 try:
  health = determine_health(statuses)
  doc = {
   "last_check": now_str(),
   "overall_health": health,
   "processes": statuses
  }
  tmp = HEALTH_STATUS + ".tmp"
  with open(tmp, "w") as f:
   json.dump(doc, f, indent=1)
  os.replace(tmp, HEALTH_STATUS)
  log("Health status written: " + health)
 except Exception as e:
  log("Failed to write health status: " + str(e), "ERROR")


def main_loop():
 global last_status_write, last_kb_check
 log("=== Zenith Watchdog v1.0 starting ===")
 log("Monitoring processes: " + ", ".join(MANAGED_PROCESSES.keys()))
 log("Check interval: " + str(CHECK_INTERVAL) + "s")
 log("Memory limit: " + str(MEMORY_LIMIT_MB) + "MB")

 while True:
  try:
   now = time.time()
   pm2_list = get_pm2_list()
   statuses = {}

   for name in MANAGED_PROCESSES:
    config = MANAGED_PROCESSES[name]
    proc = find_process(pm2_list, name)

    if proc is None:
     log("Process not found: " + name + ", creating it", "WARN")
     create_process(name, config)
     statuses[name] = {
      "status": "not_found",
      "action": "created",
      "memory_mb": 0,
      "restart_count": 0,
      "uptime_ms": 0,
      "restart_flood": False
     }
     continue

    status = get_process_status(proc)
    mem_mb = round(get_memory_mb(proc), 1)
    restarts = get_restart_count(proc)
    uptime = get_uptime_ms(proc)
    flood = check_restart_flood(name)
    action = "none"

    if status in ("stopped", "errored"):
     log(
      "Process " + name + " is " + status + ", restarting",
      "WARN"
     )
     if not flood:
      restart_process(name)
      action = "restarted"
     else:
      action = "skipped_flood"
      log(
       "Skipping restart for " + name +
       " due to restart flood",
       "CRITICAL"
      )

    elif mem_mb > MEMORY_LIMIT_MB:
     log(
      "Process " + name + " using " + str(mem_mb) +
      "MB (limit " + str(MEMORY_LIMIT_MB) +
      "MB), restarting",
      "WARN"
     )
     if not flood:
      restart_process(name)
      action = "restarted_memory"
     else:
      action = "skipped_flood"

    statuses[name] = {
     "status": status,
     "action": action,
     "memory_mb": mem_mb,
     "restart_count": restarts,
     "uptime_ms": uptime,
     "restart_flood": flood
    }

   # Knowledge base staleness check
   if now - last_kb_check >= KB_CHECK_INTERVAL:
    kb_status = check_knowledge_base()
    if kb_status == "stale":
     mega_info = statuses.get("mega", {})
     if not mega_info.get("restart_flood", False):
      restart_process("mega")
    last_kb_check = now

   # Write health status every 10 minutes
   if now - last_status_write >= STATUS_WRITE_INTERVAL:
    write_health_status(statuses)
    last_status_write = now

  except KeyboardInterrupt:
   log("Watchdog stopped by user")
   break
  except Exception as e:
   log("Main loop error: " + str(e), "ERROR")

  try:
   time.sleep(CHECK_INTERVAL)
  except KeyboardInterrupt:
   log("Watchdog stopped by user")
   break


if __name__ == "__main__":
 main_loop()
