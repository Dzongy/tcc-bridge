module.exports = {
  apps: [
    {
      name: 'bridge-v2',
      script: 'bridge-v2.py',
      interpreter: 'python',
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      env: {
        NODE_ENV: 'production'
      }
    },
    {
      name: 'watchdog-v2',
      script: 'watchdog-v2.sh',
      interpreter: 'bash',
      autorestart: true
    },
    {
      name: 'state-push',
      script: 'state-push.py',
      interpreter: 'python',
      autorestart: true,
      cron_restart: '*/5 * * * *'
    }
  ]
};
