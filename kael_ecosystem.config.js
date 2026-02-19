module.exports = {
  apps : [
    {
      name: 'tcc-bridge',
      script: 'python3',
      args: 'bridge.py',
      restart_delay: 5000,
      max_restarts: 50,
      autorestart: true,
      env: {
        PYTHONUNBUFFERED: "1",
        BRIDGE_PORT: "8080",
        NTFY_TOPIC: "tcc-zenith-hive"
      }
    },
    {
      name: 'tcc-tunnel',
      script: 'cloudflared',
      args: 'tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5',
      autorestart: true,
      restart_delay: 10000
    },
    {
      name: 'tcc-watchdog',
      script: 'bash',
      args: 'kael_watchdog.sh',
      autorestart: true
    }
  ]
};