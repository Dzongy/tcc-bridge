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
      name: "state-push",
      script: "python3",
      args: "state-push.py",
      cwd: process.env.HOME + "/tcc-bridge",
      autorestart: true,
      restart_delay: 10000
    },
    {
      name: "health-monitor",
      script: "python3",
      args: "health_monitor.py",
      cwd: process.env.HOME + "/tcc-bridge",
      autorestart: true,
      restart_delay: 60000
    }
  ]
};