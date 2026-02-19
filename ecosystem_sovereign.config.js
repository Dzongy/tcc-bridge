module.exports = {
  apps: [
    {
      name: "tcc-bridge",
      script: "python3",
      args: "bridge.py",
      cwd: "/data/data/com.termux/files/home/tcc-bridge",
      autorestart: true,
      restart_delay: 5000,
      env: {
        BRIDGE_AUTH: "amos-bridge-2026",
        BRIDGE_PORT: "8080",
        NTFY_TOPIC: "tcc-zenith-hive"
      }
    },
    {
      name: "cloudflared",
      script: "cloudflared",
      args: "tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5",
      autorestart: true,
      restart_delay: 10000
    },
    {
      name: "state-pusher",
      script: "python3",
      args: "state-push.py",
      cwd: "/data/data/com.termux/files/home/tcc-bridge",
      autorestart: true,
      restart_delay: 300000
    }
  ]
};