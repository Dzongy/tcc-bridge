module.exports = {
  apps: [
    {
      name: 'tcc-bridge',
      script: 'bridge.py',
      cwd: '/data/data/com.termux/files/home',
      interpreter: 'python',
      restart_delay: 3000,
      max_restarts: 10,
    },
    {
      name: 'tcc-tunnel',
      script: 'cloudflared',
      args: 'tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5',
      cwd: '/data/data/com.termux/files/home',
      restart_delay: 5000,
      max_restarts: 10,
    }
  ]
};