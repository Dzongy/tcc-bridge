module.exports = {
  apps: [
    {
      name: "tcc-bridge",
      script: "python3",
      args: "bridge.py",
      cwd: process.env.HOME + "/tcc-bridge",
      autorestart: true,
      restart_delay: 2000,
      env: {
        BRIDGE_AUTH: "amos-bridge-2026",
        BRIDGE_PORT: "8080",
        NTFY_TOPIC: "tcc-zenith-hive"
      }
    },
    {
      name: "cloudflared",
      script: "cloudflared",
      args: "tunnel run",
      autorestart: true,
      restart_delay: 5000
    },
    {
      name: "supabase-backup",
      script: "python3",
      args: "supabase-backup.py",
      cwd: process.env.HOME + "/tcc-bridge",
      autorestart: true,
      restart_delay: 300000 // Every 5 minutes
    },
    {
      name: "health-monitor",
      script: "python3",
      args: "health-monitor.py",
      cwd: process.env.HOME + "/tcc-bridge",
      autorestart: true,
      restart_delay: 60000
    }
  ]
};