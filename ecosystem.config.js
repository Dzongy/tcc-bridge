// ecosystem.config.js — TCC Bridge v5.0
// pm2 process definition for the Termux bridge.
// Usage:
//   pm2 start ecosystem.config.js
//   pm2 save
//   pm2 restart tcc-bridge

module.exports = {
  apps: [
    {
      // ── Identity ────────────────────────────────────────────
      name:        "tcc-bridge",
      script:      "bridge.py",
      interpreter: "/data/data/com.termux/files/usr/bin/python3",
      cwd:         require("os").homedir() + "/tcc-bridge",

      // ── Process behaviour ───────────────────────────────────
      watch:        false,          // don't restart on file changes
      autorestart:  true,
      max_restarts: 25,             // give up after 25 rapid crashes
      min_uptime:   "5s",          // must stay alive 5 s to count as "started"
      restart_delay: 3000,         // wait 3 s between restarts
      exp_backoff_restart_delay: 200, // exponential back-off seed (ms)
      kill_timeout:  5000,         // ms to wait for clean shutdown

      // ── Environment ─────────────────────────────────────────
      // Values here are DEFAULTS; they are overridden by anything
      // already exported in the shell (e.g. sourced from ~/.bridge-env).
      env: {
        BRIDGE_AUTH:  process.env.BRIDGE_AUTH  || "amos-bridge-2026",
        BRIDGE_PORT:  process.env.BRIDGE_PORT  || "8080",
        SUPABASE_URL: process.env.SUPABASE_URL || "https://vbqbbziqleymxcyesmky.supabase.co",
        SUPABASE_KEY: process.env.SUPABASE_KEY || "",
        NTFY_TOPIC:   process.env.NTFY_TOPIC   || "tcc-zenith-hive",
      },

      // ── Logging ─────────────────────────────────────────────
      error_file:      require("os").homedir() + "/bridge-err.log",
      out_file:        require("os").homedir() + "/bridge-out.log",
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      merge_logs:      true,        // combine stdout + stderr in one stream
      log_type:        "raw",       // no JSON wrapping — bridge logs its own format

      // ── Metrics / monitoring ────────────────────────────────
      // pm2 will expose these via `pm2 monit` and pm2-web dashboards.
      instance_var: "INSTANCE_ID",
      pmx:          true,
    },
  ],
};
