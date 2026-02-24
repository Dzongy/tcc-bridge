#!/usr/bin/env python3
"""
Zenith Health Patrol v1.0
Comprehensive on-device health monitoring -- replaces Twin scheduled checks.
Runs every 10 minutes, checks ALL system components, auto-heals issues.
Pure Python, zero pip dependencies.
Runs as: pm2 start sovereignty/health_patrol.py --name patrol --interpreter python3
"""

import subprocess
import json
import os
import time
import datetime
import shutil

# === CONFIG ===
PATROL_INTERVAL = 600
REPORT_PATH = "sovereignty/patrol_report.json"
LOG_PATH = "sovereignty/patrol_log.json"
LOG_MAX_ENTRIES = 100
KB_PATH = "knowledge_base.json"
AQ_PATH = "sovereignty/action_queue.json"
AGI_PATH = "sovereignty/zenith_agi_core.py"
ENV_PATH = ".env"
DISK_MIN_MB = 100
MEMORY_MAX_MB = 400
KB_STALE_MINUTES = 30
EXPECTED_PROCESSES = ["mega", "agi", "action", "watchdog"]

# === STATE ===
last_kb_size = -1
last_kb_check_time = 0


def now_iso():
 return datetime.datetime.now().isoformat()


def now_str():
 return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_print(msg, level="INFO"):
 print("[%s] [%s] %s" % (now_str(), level, msg))


def run_cmd(cmd, timeout=15):
 """Run a shell command, return (success, stdout, stderr)."""
 try:
  r = subprocess.run(
   cmd, capture_output=True, text=True, timeout=timeout
  )
  return (r.returncode == 0, r.stdout, r.stderr)
 except Exception as e:
  return (False, "", str(e))


def get_pm2_processes():
 """Get PM2 process list as dict {name: {status, memory_mb}}."""
 ok, out, err = run_cmd(["pm2", "jlist"])
 if not ok:
  return None
 try:
  data = json.loads(out)
  result = {}
  for p in data:
   name = p.get("name", "")
   status = "unknown"
   mem_mb = 0
   env = p.get("pm2_env", {})
   if env:
    status = env.get("status", "unknown")
   monit = p.get("monit", {})
   if monit:
    mem_bytes = monit.get("memory", 0)
    mem_mb = round(mem_bytes / (1024 * 1024), 1)
   result[name] = {"status": status, "memory_mb": mem_mb}
  return result
 except Exception as e:
  log_print("PM2 parse error: %s" % str(e), "ERROR")
  return None


def check_processes(pm2_data):
 """Check all expected processes are online. Auto-restart dead ones."""
 statuses = {}
 actions = []
 issues = []
 for name in EXPECTED_PROCESSES:
  if pm2_data is None:
   statuses[name] = "unknown"
   issues.append("PM2 unavailable, cannot check %s" % name)
   continue
  info = pm2_data.get(name)
  if info is None:
   statuses[name] = "missing"
   issues.append("%s not found in PM2" % name)
   log_print("Process %s missing from PM2, attempting start" % name, "WARN")
   script_map = {
    "mega": "sovereignty/mega_harvester.py",
    "agi": "sovereignty/zenith_agi_core.py",
    "action": "sovereignty/action_dispatcher.py",
    "watchdog": "sovereignty/watchdog.py",
   }
   script = script_map.get(name)
   if script and os.path.exists(script):
    ok, _, _ = run_cmd([
     "pm2", "start", script,
     "--name", name,
     "--interpreter", "python3"
    ])
    if ok:
     actions.append("started %s" % name)
     statuses[name] = "started"
    else:
     actions.append("failed to start %s" % name)
     statuses[name] = "start_failed"
   else:
    statuses[name] = "script_missing"
  elif info["status"] != "online":
   statuses[name] = info["status"]
   issues.append("%s is %s" % (name, info["status"]))
   log_print("Process %s is %s, restarting" % (name, info["status"]), "WARN")
   ok, _, _ = run_cmd(["pm2", "restart", name])
   if ok:
    actions.append("restarted %s" % name)
   else:
    actions.append("failed to restart %s" % name)
  else:
   statuses[name] = "online"
 return statuses, actions, issues


def check_memory(pm2_data):
 """Check memory usage of all processes."""
 issues = []
 if pm2_data is None:
  return issues
 for name, info in pm2_data.items():
  mb = info.get("memory_mb", 0)
  if mb > MEMORY_MAX_MB:
   issues.append("%s using %.0f MB (limit %d MB)" % (name, mb, MEMORY_MAX_MB))
   log_print("HIGH MEMORY: %s at %.0f MB" % (name, mb), "WARN")
 return issues


def check_knowledge_base():
 """Check knowledge_base.json exists and is growing."""
 global last_kb_size, last_kb_check_time
 kb_size = 0
 growing = True
 now = time.time()
 issues = []
 if not os.path.exists(KB_PATH):
  issues.append("knowledge_base.json missing")
  return 0, False, issues
 try:
  kb_size = os.path.getsize(KB_PATH)
 except Exception:
  issues.append("Cannot read knowledge_base.json size")
  return 0, False, issues
 if last_kb_size < 0:
  last_kb_size = kb_size
  last_kb_check_time = now
 elif kb_size != last_kb_size:
  last_kb_size = kb_size
  last_kb_check_time = now
 else:
  stale_min = (now - last_kb_check_time) / 60.0
  if stale_min >= KB_STALE_MINUTES:
   growing = False
   issues.append(
    "knowledge_base.json unchanged for %.0f min" % stale_min
   )
 return round(kb_size / 1024, 1), growing, issues


def check_action_queue():
 """Check action_queue.json exists and is valid JSON."""
 issues = []
 if not os.path.exists(AQ_PATH):
  issues.append("action_queue.json missing")
  return issues
 try:
  with open(AQ_PATH, "r") as f:
   json.load(f)
 except json.JSONDecodeError:
  issues.append("action_queue.json is invalid JSON")
 except Exception as e:
  issues.append("action_queue.json read error: %s" % str(e))
 return issues


def check_zero_sleep():
 """Verify AGI core has time.sleep(0) not time.sleep(300)."""
 actions = []
 issues = []
 locked = True
 if not os.path.exists(AGI_PATH):
  issues.append("zenith_agi_core.py not found")
  return False, actions, issues
 try:
  with open(AGI_PATH, "r") as f:
   content = f.read()
  if "time.sleep(300)" in content:
   locked = False
   issues.append("AGI core has time.sleep(300) -- reverting to zero-sleep")
   log_print("ZERO-SLEEP VIOLATION DETECTED, auto-fixing", "WARN")
   ok, _, _ = run_cmd([
    "sed", "-i",
    "s/time.sleep(300)/time.sleep(0)/g",
    AGI_PATH
   ])
   if ok:
    actions.append("fixed zero-sleep in AGI core")
    rok, _, _ = run_cmd(["pm2", "restart", "agi"])
    if rok:
     actions.append("restarted agi after zero-sleep fix")
    locked = True
   else:
    actions.append("failed to fix zero-sleep")
  elif "time.sleep(0)" in content:
   locked = True
  else:
   locked = True
 except Exception as e:
  issues.append("Cannot read AGI core: %s" % str(e))
  locked = False
 return locked, actions, issues


def check_env():
 """Check .env exists and is not empty."""
 issues = []
 if not os.path.exists(ENV_PATH):
  issues.append(".env file missing")
  return issues
 try:
  size = os.path.getsize(ENV_PATH)
  if size == 0:
   issues.append(".env file is empty")
 except Exception:
  issues.append("Cannot read .env")
 return issues


def check_disk():
 """Check available disk space."""
 issues = []
 free_mb = 0
 try:
  usage = shutil.disk_usage(".")
  free_mb = round(usage.free / (1024 * 1024), 0)
  if free_mb < DISK_MIN_MB:
   issues.append("Low disk: %d MB free (min %d)" % (free_mb, DISK_MIN_MB))
   log_print("LOW DISK: %d MB" % free_mb, "WARN")
 except Exception as e:
  issues.append("Disk check failed: %s" % str(e))
 return free_mb, issues


def check_internet():
 """Quick HTTP check to verify connectivity."""
 try:
  import urllib.request
  req = urllib.request.Request(
   "http://httpbin.org/status/200",
   method="HEAD"
  )
  req.add_header("User-Agent", "ZenithPatrol/1.0")
  urllib.request.urlopen(req, timeout=10)
  return True, []
 except Exception as e:
  return False, ["Internet check failed: %s" % str(e)]


def determine_status(issues, actions):
 """GREEN = no issues. YELLOW = issues but auto-fixed. RED = unresolved."""
 if len(issues) == 0:
  return "GREEN"
 fixed_count = len(actions)
 if fixed_count >= len(issues):
  return "YELLOW"
 return "RED"


def write_report(report):
 """Write patrol_report.json."""
 try:
  os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
  with open(REPORT_PATH, "w") as f:
   json.dump(report, f, indent=1)
 except Exception as e:
  log_print("Cannot write report: %s" % str(e), "ERROR")


def append_log(report):
 """Append to patrol_log.json, keep last N entries."""
 entries = []
 if os.path.exists(LOG_PATH):
  try:
   with open(LOG_PATH, "r") as f:
    entries = json.load(f)
   if not isinstance(entries, list):
    entries = []
  except Exception:
   entries = []
 entries.append(report)
 if len(entries) > LOG_MAX_ENTRIES:
  entries = entries[-LOG_MAX_ENTRIES:]
 try:
  with open(LOG_PATH, "w") as f:
   json.dump(entries, f, indent=1)
 except Exception as e:
  log_print("Cannot write log: %s" % str(e), "ERROR")


def print_summary(report):
 """Print compact summary to stdout for pm2 logs."""
 status = report.get("overall", "???")
 procs = report.get("processes", {})
 kb = report.get("knowledge_base_kb", 0)
 growing = report.get("knowledge_base_growing", False)
 disk = report.get("disk_free_mb", 0)
 inet = report.get("internet_up", False)
 zs = report.get("zero_sleep_locked", False)
 acts = report.get("actions_taken", [])
 issues = report.get("issues", [])
 proc_str = " ".join(["%s=%s" % (k, v) for k, v in procs.items()])
 line = "[PATROL] %s | %s | KB=%.0fKB grow=%s | disk=%dMB | inet=%s | zs=%s" % (
  status, proc_str, kb, growing, disk, inet, zs
 )
 print(line)
 if acts:
  print("[PATROL] Actions: %s" % ", ".join(acts))
 if issues:
  print("[PATROL] Issues: %s" % ", ".join(issues))


def run_patrol():
 """Execute one full patrol cycle."""
 log_print("=== PATROL CYCLE START ===")
 all_actions = []
 all_issues = []
 # 1. PM2 processes
 pm2_data = get_pm2_processes()
 proc_statuses, proc_actions, proc_issues = check_processes(pm2_data)
 all_actions.extend(proc_actions)
 all_issues.extend(proc_issues)
 # 2. Memory check
 mem_issues = check_memory(pm2_data)
 all_issues.extend(mem_issues)
 # 3. Knowledge base
 kb_size, kb_growing, kb_issues = check_knowledge_base()
 all_issues.extend(kb_issues)
 # 4. Action queue
 aq_issues = check_action_queue()
 all_issues.extend(aq_issues)
 # 5. Zero-sleep
 zs_locked, zs_actions, zs_issues = check_zero_sleep()
 all_actions.extend(zs_actions)
 all_issues.extend(zs_issues)
 # 6. .env check
 env_issues = check_env()
 all_issues.extend(env_issues)
 # 7. Disk space
 disk_mb, disk_issues = check_disk()
 all_issues.extend(disk_issues)
 # 8. Internet connectivity
 inet_up, inet_issues = check_internet()
 all_issues.extend(inet_issues)
 # Build report
 overall = determine_status(all_issues, all_actions)
 report = {
  "timestamp": now_iso(),
  "overall": overall,
  "processes": proc_statuses,
  "knowledge_base_kb": kb_size,
  "knowledge_base_growing": kb_growing,
  "zero_sleep_locked": zs_locked,
  "disk_free_mb": disk_mb,
  "internet_up": inet_up,
  "actions_taken": all_actions,
  "issues": all_issues,
 }
 write_report(report)
 append_log(report)
 print_summary(report)
 log_print("=== PATROL CYCLE END === Status: %s" % overall)
 return report


def main():
 log_print("Zenith Health Patrol v1.0 starting")
 log_print("Monitoring: %s" % ", ".join(EXPECTED_PROCESSES))
 log_print("Interval: %d seconds" % PATROL_INTERVAL)
 cycle = 0
 while True:
  try:
   cycle += 1
   log_print("Patrol cycle #%d" % cycle)
   run_patrol()
  except Exception as e:
   log_print("PATROL CYCLE CRASHED: %s" % str(e), "ERROR")
  try:
   time.sleep(PATROL_INTERVAL)
  except KeyboardInterrupt:
   log_print("Patrol stopped by user")
   break


if __name__ == "__main__":
 main()
