module.exports = {
  apps: [
    {
      name: 'bridge',
      script: 'python3',
      args: 'bridge.py',
      restart_delay: 5000,
      max_restarts: 50,
      env: { PYTHONUNBUFFERED: "1" }
    },
    {
      name: 'tunnel',
      script: 'cloudflared',
      args: 'tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5',
      restart_delay: 5000,
      max_restarts: 50
    },
    {
      name: 'state-push',
      script: 'python3',
      args: 'state-push.py',
      restart_delay: 10000,
      env: { PYTHONUNBUFFERED: "1" }
    },
    {
      name: 'watchdog',
      script: 'bash',
      args: 'watchdog-v2.sh',
      restart_delay: 5000
    }
  ]
};
