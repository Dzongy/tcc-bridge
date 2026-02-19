module.exports = {
  apps: [
    {
      name: "tcc-bridge",
      script: "python3",
      args: "bridge.py",
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
    },
    {
       name: "tcc-server",
       script: "python3",
       args: "server.py",
       autorestart: true,
       env: {
         BRIDGE_AUTH: "amos-bridge-2026"
       }
    }
  ]
}
