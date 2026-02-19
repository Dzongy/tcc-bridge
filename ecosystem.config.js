module.exports = {
  apps: [
    {
      name: "tcc-bridge",
      script: "python3",
      args: "bridge.py",
      cwd: process.env.HOME + "/tcc-bridge",
      autorestart: true,
      restart_delay: 2000,
      exp_backoff_restart_delay: 100,
      watch: false,
      max_memory_restart: "200M",
      env: {
        PYTHONUNBUFFERED: "1"
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
      restart_delay: 60000
    }
  ]
};