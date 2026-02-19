module.exports = {
  apps : [
    {
      name: 'tcc-bridge',
      script: 'bridge.py',
      interpreter: 'python3',
      restart_delay: 3000,
      max_restarts: 10,
      env: {
        PYTHONUNBUFFERED: "1"
      }
    },
    {
      name: 'tcc-tunnel',
      script: 'cloudflared',
      args: 'tunnel run --token 18ba1a49-fdf9-4a52-a27a-5250d397c5c5',
      restart_delay: 5000,
      max_restarts: 50
    }
  ]
}