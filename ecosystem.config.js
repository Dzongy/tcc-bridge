
module.exports = {
  apps: [
    {
      name: "tcc-bridge",
      script: "python3 bridge.py",
      restart_delay: 5000,
      max_restarts: 50,
      env: {
        PYTHONUNBUFFERED: "1"
      }
    },
    {
      name: "tcc-tunnel",
      script: "cloudflared tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5",
      restart_delay: 5000,
      max_restarts: 100
    }
  ]
}
