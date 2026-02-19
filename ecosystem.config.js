module.exports = {
  apps: [
    {
      name: 'tcc-bridge',
      script: 'bridge.py',
      interpreter: 'python3',
      restart_delay: 3000,
      max_restarts: 10,
      autorestart: true,
      watch: false,
      env: {
        PYTHONUNBUFFERED: "1"
      }
    },
    {
      name: 'tcc-watchdog',
      script: 'watchdog.py',
      interpreter: 'python3',
      restart_delay: 10000,
      autorestart: true,
      env: {
        PYTHONUNBUFFERED: "1"
      }
    },
    {
      name: 'tcc-state-push',
      script: 'state-push.py',
      interpreter: 'python3',
      cron_restart: '*/5 * * * *',
      autorestart: false,
      env: {
        PYTHONUNBUFFERED: "1"
      }
    }
  ]
};