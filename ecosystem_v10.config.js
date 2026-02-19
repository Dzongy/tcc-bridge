module.exports = {
  apps: [
    {
      name: "tcc-bridge-v10",
      script: "python3",
      args: "bridge_v10.py",
      autorestart: true,
      max_memory_restart: "200M",
      env: {
        PYTHONUNBUFFERED: "1"
      }
    },
    {
      name: "tcc-tunnel",
      script: "cloudflared",
      args: "tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5",
      autorestart: true,
      restart_delay: 10000
    }
  ]
};