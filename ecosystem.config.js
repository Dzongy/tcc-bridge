module.exports = {
  apps: [
    {
      name: "tcc-bridge",
      script: "python3",
      args: "bridge.py",
      autorestart: true,
      restart_delay: 5000,
      env: {
        BRIDGE_PORT: "8765",
        BRIDGE_AUTH: "amos-bridge-2026"
      }
    },
    {
      name: "cloudflared",
      script: "cloudflared",
      args: "tunnel run --token " + (process.env.CF_TOKEN || "") + " 18ba1a49-fdf9-4a52-a27a-5250d397c5c5",
      autorestart: true,
      restart_delay: 10000
    },
    {
      name: "tcc-watchdog",
      script: "bash",
      args: "watchdog-v2.sh",
      autorestart: true
    }
  ]
};