// ecosystem.config.js — TCC Bridge v8.1.0
module.exports = {
  apps: [
    {
      name:         "tcc-bridge",
      script:       "bridge.py",
      interpreter:  "/data/data/com.termux/files/usr/bin/python3",
      cwd:          process.env.HOME + "/tcc",
      autorestart:  true,
      max_restarts: 50,
      restart_delay: 5000,
      env: {
        BRIDGE_AUTH: "amos-bridge-2026",
        BRIDGE_PORT: "8080"
      }
    },
    {
      name:         "tcc-tunnel",
      script:       "cloudflared",
      args:         "tunnel --no-autoupdate run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5",
      interpreter:  "none",
      autorestart:  true,
      restart_delay: 10000
    },
    {
      name:         "tcc-state-push",
      script:       "state-push.py",
      interpreter:  "/data/data/com.termux/files/usr/bin/python3",
      cwd:          process.env.HOME + "/tcc",
      autorestart:  true,
      restart_delay: 300000
    }
  ]
};
