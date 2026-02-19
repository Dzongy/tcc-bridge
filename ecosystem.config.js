module.exports = {
  apps: [
    {
      name: 'tcc-bridge',
      script: '/data/data/com.termux/files/home/tcc-bridge/bridge.py',
      interpreter: 'python',
      restart_delay: 5000,
      max_restarts: 50,
      watch: false,
      env: {
        PYTHONUNBUFFERED: '1'
      }
    },
    {
      name: 'cloudflared',
      script: 'cloudflared',
      args: 'tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5',
      interpreter: 'none',
      restart_delay: 5000,
      max_restarts: 50,
      watch: false
    }
  ]
};
