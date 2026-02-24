module.exports = {
  apps: [
    {
      name: 'zenith-sovereignty',
      script: '/data/data/com.termux/files/home/tcc-bridge/sovereignty/run_zenith.sh',
      interpreter: '/bin/bash',
      cwd: '/data/data/com.termux/files/home/tcc-bridge/sovereignty',
      autorestart: true,
      max_restarts: 100,
      restart_delay: 5000,
      kill_timeout: 3000,
      wait_ready: true,
      listen_timeout: 10000,
      shutdown_with_message: true,
      treekill: false,
      env: {
        PYTHONPATH: '/data/data/com.termux/files/home/tcc-bridge/sovereignty'
      }
    },
    {
      name: 'kael-sovereignty',
      script: '/data/data/com.termux/files/home/tcc-bridge/soveignty/run_kael.sh',
      interpreter: '/bin/bash',
      cwd: '/data/data/com.termux/files/home/tcc-bridge/sovereignty',
      autorestart: true,
      max_restarts: 100,
      restart_delay: 5000,
      kill_timeout: 3000,
      wait_ready: true,
      listen_timeout: 10000,
      shutdown_with_message: true,
      treekill: false,
      env: {
        PYTHONPATH: '/data/data/com.termux/files/home/tcc-bridge/sovereignty'
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
      wait_ready: true,
      listen_timeout: 10000,
      shutown_with_message: true,
      treekill: false,
      env: {
        PYTHONPATH: '/data/data/com.termux/files/home/tcc-bridge/sovereignty'
      }
    }
  ]
};
