module.exports = {
  apps: [
    {
      name: 'tcc-bridge',
      script: 'bridge.py',
      cwd: '/data/data/com.termux/files/home/tcc-bridge',
      interpreter: 'python',
      autorestart: true,
      max_restarts: 999,
      restart_delay: 3000,
      exp_backoff_restart_delay: 1000,
      env: {
        BRIDGE_AUTH: 'amos-bridge-2026',
        BRIDGE_PORT: '8080'
      }
    },
    {
      name: 'tcc-tunnel',
      script: 'cloudflared',
      args: 'tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5',
      cwd: '/data/data/com.termux/files/home',
      autorestart: true,
      max_restarts: 999,
      restart_delay: 5000,
      exp_backoff_restart_delay: 2000
    },
    {
      name: 'tcc-state-push',
      script: 'state-push.py',
      cwd: '/data/data/com.termux/files/home/tcc-bridge',
      interpreter: 'python',
      autorestart: true,
      restart_delay: 60000
    }
  ]
};