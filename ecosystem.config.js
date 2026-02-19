module.exports = {
  apps: [
    {
      name: 'bridge',
      script: 'python3',
      args: 'bridge.py',
      restart_delay: 3000,
      max_restarts: 10,
      env: {
        BRIDGE_AUTH: 'amos-bridge-2026',
        BRIDGE_PORT: '8080'
      }
    },
    {
      name: 'cloudflared',
      script: 'cloudflared',
      args: 'tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5',
      restart_delay: 5000
    },
    {
      name: 'state-push',
      script: 'python3',
      args: 'state-push.py',
      restart_delay: 10000
    },
    {
      name: 'watchdog',
      script: './watchdog-v2.sh',
      restart_delay: 10000
    }
  ]
};
