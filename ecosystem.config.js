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
      args: "tunnel --config /data/data/com.termux/files/home/.cloudflared/config.yml run",
      autorestart: true,
      restart_delay: 5000
    },
    {
      name: "state-pusher",
      script: "python3",
      args: "bridge_v2.py",
      cwd: "/data/data/com.termux/files/home/tcc-bridge",
      autorestart: true,
      restart_delay: 60000
    }
  ]
};