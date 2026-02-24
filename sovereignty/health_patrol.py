#!/usr/bin/env python3
"""
Zenith Health Patrol v2.0 "Fortress"
Comprehensive on-device health monitoring -- replaces Twin scheduled checks.
Runs every 10 minutes, checks ALL system components, auto-heals issues.
v2.0 adds: auto-backup with rotation, integrity checksums, log rotation,
brain health check, auto-gitignore enforcement, sovereignty dir monitoring.
Pure Python, zero pip dependencies.
Runs as: pm2 start sovereignty/health_patrol.py --name patrol --interpreter python3
"""

import subprocess
import json
import os
import time
import datetime
import shutil
import glob
import hashlib

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

# === BACKUP CONFIG ===
BACKUP_DIR = "sovereignty/backups"
BACKUP_MAX_COPIES = 5
BACKUP_FILES = [
 ("sovereignty/knowledge_base.json", "knowledge_base"),
 ("sovereignty/goals.json", "goals"),
 ("sovereignty/action_log.json", "action_log"),
 ("sovereignty/zenith_agi_core.json", "agi_state"),
]

# === INTEGRITY CONFIG ===
INTEGRITY_MANIFEST = "sovereignty/integrity_manifest.json"
INTEGRITY_FILES = [
 "sovereignty/mega_harvester.py",
 "sovereignty/zenith_agi_core.py",
 "sovereignty/action_dispatcher.py",
 "sovereignty/watchdog.py",
 "sovereignty/health_patrol.py",
]

# === CLEANUP CONFIG ===
SOVEREIGNTY_MAX_MB = 500

# === GITIGNORE ENFORCEMENT ===
GITIGNORE_PATH = ".gitignore"
GITIGNORE_REQUIRED = [
 ".env",
 "sovereignty/backups/",
 "sovereignty/patrol_log.json",
 "sovereignty/patrol_report.json",
]

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



# ============================================================
# === FORTRESS FEATURES (v2.0) ===
# ============================================================

def run_backup():
 """Backup critical files with rotation. Auto-restore if KB missing."""
 backup_status = "backed_up"
 backup_count = 0
 backup_size_bytes = 0
 restore_actions = []
 try:
  if not os.path.isdir(BACKUP_DIR):
   os.makedirs(BACKUP_DIR, exist_ok=True)
   log_print("Created backup directory: %s" % BACKUP_DIR)
  ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
  for src_path, prefix in BACKUP_FILES:
   try:
    if not os.path.isfile(src_path):
     continue
    sz = os.path.getsize(src_path)
    if sz == 0:
     continue
    dst = os.path.join(BACKUP_DIR, "%s_%s.json" % (prefix, ts))
    shutil.copy2(src_path, dst)
    log_print("Backed up %s -> %s (%d bytes)" % (src_path, dst, sz))
    pattern = os.path.join(BACKUP_DIR, "%s_*.json" % prefix)
    existing = sorted(glob.glob(pattern))
    while len(existing) > BACKUP_MAX_COPIES:
     oldest = existing.pop(0)
     try:
      os.remove(oldest)
      log_print("Rotated old backup: %s" % oldest)
     except Exception:
      pass
   except Exception as e:
    log_print("Backup failed for %s: %s" % (src_path, str(e)), "WARN")
  # Auto-restore: if knowledge_base.json missing or empty, restore from backup
  kb_src = "sovereignty/knowledge_base.json"
  kb_needs_restore = False
  if not os.path.isfile(kb_src):
   kb_needs_restore = True
  elif os.path.getsize(kb_src) == 0:
   kb_needs_restore = True
  if kb_needs_restore:
   kb_backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "knowledge_base_*.json")))
   if kb_backups:
    latest = kb_backups[-1]
    try:
     shutil.copy2(latest, kb_src)
     msg = "AUTO-RESTORED knowledge_base.json from %s" % latest
     log_print(msg, "WARN")
     restore_actions.append(msg)
    except Exception as e:
     log_print("Auto-restore failed: %s" % str(e), "ERROR")
  # Count all backups and total size
  try:
   for f in os.listdir(BACKUP_DIR):
    fp = os.path.join(BACKUP_DIR, f)
    if os.path.isfile(fp):
     backup_count += 1
     backup_size_bytes += os.path.getsize(fp)
  except Exception:
   pass
 except Exception as e:
  backup_status = "failed"
  log_print("Backup system error: %s" % str(e), "ERROR")
 backup_size_mb = round(backup_size_bytes / (1024.0 * 1024.0), 2)
 return backup_status, backup_count, backup_size_mb, restore_actions


def compute_file_sha256(filepath):
 """Compute SHA-256 hash of a file. Returns hex string or None."""
 try:
  h = hashlib.sha256()
  with open(filepath, "rb") as f:
   while True:
    chunk = f.read(65536)
    if not chunk:
     break
    h.update(chunk)
  return h.hexdigest()
 except Exception:
  return None


def check_integrity():
 """Check SHA-256 hashes of core .py files against manifest."""
 integrity_status = "verified"
 changed_files = []
 current_hashes = {}
 checked_at = now_iso()
 # Compute current hashes
 for fp in INTEGRITY_FILES:
  h = compute_file_sha256(fp)
  if h is not None:
   current_hashes[fp] = h
 # Load existing manifest
 old_manifest = {}
 if os.path.isfile(INTEGRITY_MANIFEST):
  try:
   with open(INTEGRITY_MANIFEST, "r") as f:
    old_manifest = json.load(f)
  except Exception:
   old_manifest = {}
 old_hashes = {}
 for k, v in old_manifest.items():
  if k not in ("checked_at",):
   old_hashes[k] = v
 # Compare
 if old_hashes:
  # Check if a git pull happened recently (git reflog)
  git_pull_recent = False
  try:
   ok, out, _ = run_cmd(["git", "log", "--oneline", "-1", "--format=%ct"])
   if ok and out.strip():
    last_commit_ts = int(out.strip())
    now_ts = int(time.time())
    if (now_ts - last_commit_ts) < (PATROL_INTERVAL + 60):
     git_pull_recent = True
  except Exception:
   pass
  for fp, new_hash in current_hashes.items():
   old_hash = old_hashes.get(fp)
   if old_hash and old_hash != new_hash:
    if git_pull_recent:
     log_print("File %s changed (git pull detected, OK)" % fp)
    else:
     changed_files.append(fp)
     log_print("INTEGRITY: %s hash changed without git pull!" % fp, "WARN")
 if changed_files:
  integrity_status = "changed"
 # Write updated manifest
 manifest_data = dict(current_hashes)
 manifest_data["checked_at"] = checked_at
 try:
  with open(INTEGRITY_MANIFEST, "w") as f:
   json.dump(manifest_data, f, indent=1)
 except Exception as e:
  log_print("Cannot write integrity manifest: %s" % str(e), "ERROR")
 return integrity_status, changed_files


def check_brain_health():
 """Count API keys in .env and detect possible auth errors in pm2 logs."""
 api_keys_found = 0
 expired_suspects = []
 try:
  if os.path.isfile(ENV_PATH):
   with open(ENV_PATH, "r") as f:
    for line in f:
     line = line.strip()
     if not line or line.startswith("#"):
      continue
     if ("_API_KEY=" in line or "_KEY=" in line):
      parts = line.split("=", 1)
      if len(parts) == 2:
       val = parts[1].strip().strip('"').strip("'")
       if val and val != "" and "DISABLED" not in parts[0]:
        api_keys_found += 1
 except Exception as e:
  log_print("Cannot read .env for brain health: %s" % str(e), "WARN")
 # Check pm2 logs for auth errors (last 50 lines per process)
 auth_error_patterns = ["401", "403", "unauthorized", "invalid_api_key", "auth_error", "invalid key"]
 for proc in ["mega", "agi", "action"]:
  try:
   ok, out, _ = run_cmd(["pm2", "logs", proc, "--lines", "50", "--nostream"], timeout=10)
   if ok and out:
    lower_out = out.lower()
    for pattern in auth_error_patterns:
     if pattern in lower_out:
      expired_suspects.append(proc)
      break
  except Exception:
   pass
 return api_keys_found, expired_suspects


def check_sovereignty_size():
 """Check total size of sovereignty/ directory. Clean up if over limit."""
 total_bytes = 0
 cleanup_actions = []
 try:
  for root, dirs, files in os.walk("sovereignty"):
   for f in files:
    fp = os.path.join(root, f)
    try:
     total_bytes += os.path.getsize(fp)
    except Exception:
     pass
 except Exception:
  pass
 total_mb = round(total_bytes / (1024.0 * 1024.0), 1)
 if total_mb > SOVEREIGNTY_MAX_MB:
  log_print("sovereignty/ dir at %.1f MB (limit %d MB), cleaning up" % (total_mb, SOVEREIGNTY_MAX_MB), "WARN")
  # Delete oldest backups first
  try:
   all_backups = []
   if os.path.isdir(BACKUP_DIR):
    for f in os.listdir(BACKUP_DIR):
     fp = os.path.join(BACKUP_DIR, f)
     if os.path.isfile(fp):
      all_backups.append((os.path.getmtime(fp), fp))
   all_backups.sort()
   deleted = 0
   while all_backups and total_mb > SOVEREIGNTY_MAX_MB * 0.8:
    _, oldest = all_backups.pop(0)
    sz = os.path.getsize(oldest)
    os.remove(oldest)
    total_bytes -= sz
    total_mb = round(total_bytes / (1024.0 * 1024.0), 1)
    deleted += 1
   if deleted:
    cleanup_actions.append("Deleted %d old backups to free space" % deleted)
    log_print("Deleted %d old backups, now at %.1f MB" % (deleted, total_mb))
  except Exception as e:
   log_print("Backup cleanup error: %s" % str(e), "WARN")
  # If still over, trim patrol log
  if total_mb > SOVEREIGNTY_MAX_MB:
   try:
    if os.path.isfile(LOG_PATH):
     with open(LOG_PATH, "r") as f:
      entries = json.load(f)
     if isinstance(entries, list) and len(entries) > 20:
      entries = entries[-(len(entries) // 2):]
      with open(LOG_PATH, "w") as f:
       json.dump(entries, f, indent=1)
      cleanup_actions.append("Trimmed patrol log to %d entries" % len(entries))
      log_print("Trimmed patrol log to %d entries" % len(entries))
   except Exception:
    pass
 return total_mb, cleanup_actions


def enforce_gitignore():
 """Ensure .gitignore contains required entries. Local only."""
 actions = []
 try:
  existing_lines = []
  if os.path.isfile(GITIGNORE_PATH):
   with open(GITIGNORE_PATH, "r") as f:
    existing_lines = [l.strip() for l in f.readlines()]
  missing = []
  for entry in GITIGNORE_REQUIRED:
   if entry not in existing_lines:
    missing.append(entry)
  if missing:
   with open(GITIGNORE_PATH, "a") as f:
    for entry in missing:
     f.write("\n%s" % entry)
   msg = "Added to .gitignore: %s" % ", ".join(missing)
   log_print(msg)
   actions.append(msg)
 except Exception as e:
  log_print("Gitignore enforcement error: %s" % str(e), "WARN")
 return actions



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
 bks = report.get("backup_status", "n/a")
 integ = report.get("integrity_status", "n/a")
 keys = report.get("api_keys_found", 0)
 sov_mb = report.get("sovereignty_dir_mb", 0)
 proc_str = " ".join(["%s=%s" % (k, v) for k, v in procs.items()])
 line = "[PATROL] %s | %s | KB=%.0fKB grow=%s | disk=%dMB | inet=%s | zs=%s | bk=%s | integ=%s | keys=%d | sov=%.0fMB" % (
  status, proc_str, kb, growing, disk, inet, zs, bks, integ, keys, sov_mb
 )
 print(line)
 if acts:
  print("[PATROL] Actions: %s" % ", ".join(acts))
 if issues:
  print("[PATROL] Issues: %s" % ", ".join(issues))


def run_patrol():
 """Execute one full patrol cycle with fortress features."""
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
 # === FORTRESS v2.0 ===
 # 9. Backup critical files
 bk_status, bk_count, bk_size_mb, bk_restores = run_backup()
 all_actions.extend(bk_restores)
 # 10. Integrity checksums
 integ_status, integ_changed = check_integrity()
 if integ_changed:
  all_issues.extend(["integrity_warning: %s" % f for f in integ_changed])
 # 11. Brain health
 api_keys_found, expired_suspects = check_brain_health()
 if expired_suspects:
  all_issues.extend(["possible_auth_error: %s" % p for p in expired_suspects])
 # 12. Sovereignty dir size + cleanup
 sov_mb, cleanup_acts = check_sovereignty_size()
 all_actions.extend(cleanup_acts)
 # 13. Gitignore enforcement
 gi_acts = enforce_gitignore()
 all_actions.extend(gi_acts)
 # Build report
 overall = determine_status(all_issues, all_actions)
 if integ_changed:
  if overall == "GREEN":
   overall = "YELLOW"
 report = {
  "timestamp": now_iso(),
  "overall": overall,
  "processes": proc_statuses,
  "knowledge_base_kb": kb_size,
  "knowledge_base_growing": kb_growing,
  "zero_sleep_locked": zs_locked,
  "disk_free_mb": disk_mb,
  "internet_up": inet_up,
  "backup_status": bk_status,
  "backup_count": bk_count,
  "backup_size_mb": bk_size_mb,
  "integrity_status": integ_status,
  "integrity_changed_files": integ_changed,
  "api_keys_found": api_keys_found,
  "expired_key_suspects": expired_suspects,
  "sovereignty_dir_mb": sov_mb,
  "actions_taken": all_actions,
  "issues": all_issues,
 }
 write_report(report)
 append_log(report)
 print_summary(report)
 log_print("=== PATROL CYCLE END === Status: %s" % overall)
 return report


def main():
 log_print("Zenith Health Patrol v2.0 Fortress starting")
 log_print("Monitoring: %s" % ", ".join(EXPECTED_PROCESSES))
 log_print("Interval: %d seconds" % PATROL_INTERVAL)
 log_print("Fortress: backup, integrity, brain-health, cleanup, gitignore")
 cycle = 0
 while True:
  try:
   cycle += 1
   log_print("Patrol cycle #%d" % cycle)
   run_patrol()
  except Exception as e:
   log_print("Patrol cycle error: %s" % str(e), "ERROR")
  time.sleep(PATROL_INTERVAL)


if __name__ == "__main__":
 main()
