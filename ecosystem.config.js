module.exports = {
  apps: [
    {
      name: 'kael-sovereignty',
      script: '/data/data/com.termux/files/home/tcc-bridge/sovereignty/run_kael.sh',
      interpreter: '/data/data/com.termux/files/usr/bin/bash',
      cwd: '/data/data/com.termux/files/home/tcc-bridge/sovereignty',
      kill_timeout: 3000,
      shutdown_with_message: true,
      autorestart: true,
      max_restarts: 100,
      restart_delay: 5000,
      env: {
        PYTHONUNBUFFERED: '1',
        GROQ_API_KEY: '${GROQ_API_KEY}'
      }
    },
    {
      name: 'chris-sovereignty',
      script: '/data/data/com.termux/files/home/tcc-bridge/sovereignty/run_chris.sh',
      interpreter: '/data/data/com.termux/files/usr/bin/bash',
      cwd: '/data/data/com.termux/files/home/tcc-bridge/sovereignty',
      kill_timeout: 3000,
      shutdown_with_message: true,
      autorestart: true,
      max_restarts: 100,
      restart_delay: 5000,
      env: {
        PYTHONUNBUFFERED: '1',
        GROQ_API_KEY: '${GROQ_API_KEY}'
      }
    }
  ]
};