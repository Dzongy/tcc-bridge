module.exports = {
  apps: [
    {
      name: 'bridge',
      script: 'bridge.py',
      interpreter: 'python',
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      env: {
        NODE_ENV: 'production'
      }
    },
    {
      name: 'watchdog',
      script: 'watchdog-v2.sh',
      interpreter: 'bash',
      autorestart: true
    }
  ]
};
