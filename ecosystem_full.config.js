module.exports = {
  apps: [
    {
      name: 'tcc-bridge',
      script: 'python3',
      args: 'bridge.py',
      autorestart: true,
      env: {
        PYTHONUNBUFFERED: "1",
        BRIDGE_PORT: "8765"
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
      name: 'kael-sovereignty',
      script: '/data/data/com.termux/files/home/tcc-bridge/sovereignty/run_kael.sh',
      interpreter: '/bin/bash',
      cwd: '/data/data/com.termux/files/home/tcc-bridge/sovereignty',
      autorestart: true,
      max_restarts: 100,
      restart_delay: 5000,
      kill_timeout: 3000,
      shutdown_with_message: true,
      treekill: false,
      env: {
        PYTHONPATH: '.'
      }
    },
    {
      name: 'chris-sovereignty',
      script: '/data/data/com.termux/files/home/tcc-bridge/sovereignty/run_chris.sh',
      interpreter: '/bin/bash',
      cwd: '/data/data/com.termux/files/home/tcc-bridge/sovereignty',
      autorestart: true,
      max_restarts: 100,
      restart_delay: 5000,
      kill_timeout: 3000,
      shutdown_with_message: true,
      treekill: false,
      env: {
        PYTHONPATH: '.'
      }
    }
  ]
};