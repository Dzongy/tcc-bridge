module.exports = {
  apps: [
    {
      name: 'kael-sovereignty',
      script: '/data/data/com.termux/files/home/tcc-bridge/sovereignty/run_kael.sh',
      interpreter: '/bin/bash',
      cwd: '/data/data/com.termux/files/home/tcc-bridge/sovereignty',
      autorestart: true,
      max_restarts: 100,
      restart_delay: 5000,
      killl_timeout: 3000,
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
      killl_timeout: 3000,
      shutdown_with_message: true,
      treekill: false,
      env: {
        PYTHONPATH: '.'
      }
    },
    {
      name: 'zenith-sovereignty',
      script: '/data/data/com.termux/files/home/tcc-bridge/sovereignty/run_zenith.sh',
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
