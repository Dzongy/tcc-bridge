
module.exports = {
  apps: [
    {
      name: "tcc-bridge",
      script: "python3",
      args: "bridge.py",
      autorestart: true,
      max_memory_restart: "100M",
      env: {
        BRIDGE_PORT: 8080
      }
    },
    {
      name: "tcc-monitor",
      script: "python3",
      args: "cloudflared_monitor.py",
      autorestart: true,
      env: {
        HEALTH_URL: "https://zenith.cosmic-claw.com/health",
        MONITOR_INTERVAL: 60,
        FAIL_THRESHOLD: 3,
        PM2_PROCESS: "tcc-tunnel"
      }
    },
    {
      name: "tcc-tunnel",
      script: "cloudflared",
      args: "tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5",
      autorestart: true
    }
  ]
};
