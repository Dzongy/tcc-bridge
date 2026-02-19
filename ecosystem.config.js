// =============================================================
// TCC Bridge — ecosystem.config.js
// PM2 process manager config
// Master Engineer: Kael | The Cosmic Claws
// =============================================================

module.exports = {
  apps: [
    // ── 1. Main bridge server ─────────────────────────────────
    {
      name:             "tcc-bridge",
      script:           "bridge.py",
      interpreter:      "python3",
      cwd:              process.env.HOME + "/tcc-bridge",

      // Restart policy
      autorestart:      true,
      watch:            false,           // disable file-watch in prod
      max_restarts:     20,
      min_uptime:       "10s",           // must stay up 10 s to count as started
      restart_delay:    3000,            // ms between restarts
      exp_backoff_restart_delay: 100,   // exponential back-off

      // Logging
      out_file:         process.env.HOME + "/tcc-bridge/logs/bridge-out.log",
      error_file:       process.env.HOME + "/tcc-bridge/logs/bridge-err.log",
      merge_logs:       true,
      log_date_format:  "YYYY-MM-DD HH:mm:ss Z",
      log_type:         "json",

      // Environment
      env: {
        PYTHONUNBUFFERED: "1",
        TCC_ENV:          "production",
      },
    },

    // ── 2. State push — runs every 5 minutes via cron ─────────
    {
      name:             "tcc-state-push",
      script:           "state-push.py",
      interpreter:      "python3",
      cwd:              process.env.HOME + "/tcc-bridge",

      // Cron mode: run every 5 minutes, then exit
      cron_restart:     "*/5 * * * *",
      autorestart:      false,           // exits after each run
      watch:            false,

      // Logging
      out_file:         process.env.HOME + "/tcc-bridge/logs/state-push-out.log",
      error_file:       process.env.HOME + "/tcc-bridge/logs/state-push-err.log",
      merge_logs:       true,
      log_date_format:  "YYYY-MM-DD HH:mm:ss Z",

      // Environment — SUPABASE_ANON_KEY injected from shell env
      env: {
        PYTHONUNBUFFERED: "1",
        TCC_ENV:          "production",
        SUPABASE_ANON_KEY: process.env.SUPABASE_ANON_KEY || "",
      },
    },
  ],
};
