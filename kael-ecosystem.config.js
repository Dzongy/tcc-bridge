module.exports = {
  apps: [
    {
      name: "kael-bridge",
      script: "python3",
      args: "~/tcc-bridge/kael-bridge-final.py",
      autorestart: true,
      watch: false,
      env: {
        PORT: 8080,
        AUTH_TOKEN: "amos-bridge-2026"
      }
    },
    {
      name: "kael-watchdog",
      script: "bash",
      args: "~/tcc-bridge/kael-watchdog.sh",
      autorestart: true
    },
    {
      name: "kael-state-push",
      script: "python3",
      args: "~/tcc-bridge/kael-state-push.py",
      cron_restart: "*/5 * * * *",
      autorestart: false
    }
  ]
};