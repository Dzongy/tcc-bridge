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
      name: 'watchdog',
      script: 'watchdog-v2.sh',
      interpreter: 'bash',
      restart_delay: 5000
    },
    {
      name: 'cloudflared',
      script: 'cloudflared',
      args: 'tunnel run --token ' + process.env.CLOUDFLARE_TOKEN,
      restart_delay: 10000
    }
  ]
};
