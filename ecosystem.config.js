module.exports = {
  apps: [
    {
      name: 'bridge',
      script: 'bridge.py',
      interpreter: 'python3',
      restart_delay: 5000,
      env: {
        BRIDGE_PORT: '8080',
        BRIDGE_AUTH: 'amos-bridge-2026'
      }
    },
    {
      name: 'state-push',
      script: 'state-push.py',
      interpreter: 'python3',
      restart_delay: 10000
    },
    {
      name: 'watchdog',
      script: 'watchdog-v2.sh',
      interpreter: 'bash'
    }
  ]
};
