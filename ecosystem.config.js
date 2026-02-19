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
        BRIDGE_PORT: "8765"
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
      name: "watchdog",
      script: "/data/data/com.termux/files/usr/bin/bash",
      args: "watchdog-v2.sh",
      cwd: process.env.HOME + "/tcc-bridge",
      autorestart: true
    }
  ]
};
