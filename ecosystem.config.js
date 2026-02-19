// ecosystem.config.js â TCC Bridge V2 PM2 Process Manager Configuration
// Place at: ~/tcc-bridge/ecosystem.config.js
// Usage:  pm2 start ecosystem.config.js
//         pm2 reload ecosystem.config.js --update-env

const os = require('os');
const HOME = os.homedir();
const BRIDGE_DIR = `${HOME}/tcc-bridge`;
const LOG_DIR = `${BRIDGE_DIR}/logs`;
const TUNNEL_UUID = '18ba1a49-fdf9-4a52-a27a-5250d397c5c5';

module.exports = {
  apps: [
    // ââ 1. TCC Bridge API (bridge.py) ââââââââââââââââââââââââââââââââââââââââ
    {
      name: 'tcc-bridge',
      script: `${BRIDGE_DIR}/bridge.py`,
      interpreter: 'python3',
      cwd: BRIDGE_DIR,

      // Restart behaviour
      autorestart: true,
      watch: false,
      max_restarts: 20,
      restart_delay: 3000,    // ms â wait 3 s before restart
      exp_backoff_restart_delay: 100,

      // Logging
      out_file: `${LOG_DIR}/bridge-out.log`,
      error_file: `${LOG_DIR}/bridge-err.log`,
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',

      // Environment
      env: {
        PYTHONUNBUFFERED: '1',
        BRIDGE_PORT: '8080',
        NODE_ENV: 'production',
      },
    },

    // ââ 2. State Push Worker (state-push.py) âââââââââââââââââââââââââââââââââ
    {
      name: 'tcc-state-push',
      script: `${BRIDGE_DIR}/state-push.py`,
      interpreter: 'python3',
      cwd: BRIDGE_DIR,

      autorestart: true,
      watch: false,
      max_restarts: 20,
      restart_delay: 5000,
      exp_backoff_restart_delay: 100,

      out_file: `${LOG_DIR}/state-push-out.log`,
      error_file: `${LOG_DIR}/state-push-err.log`,
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',

      env: {
        PYTHONUNBUFFERED: '1',
        NODE_ENV: 'production',
      },
    },

    // ââ 3. Cloudflare Tunnel (cloudflared) âââââââââââââââââââââââââââââââââââ
    {
      name: 'tcc-cloudflared',
      script: 'cloudflared',
      args: `tunnel run ${TUNNEL_UUID}`,
      interpreter: 'none',   // binary, not a script interpreter
      cwd: BRIDGE_DIR,

      autorestart: true,
      watch: false,
      max_restarts: 50,        // tunnels should be very resilient
      restart_delay: 2000,
      exp_backoff_restart_delay: 100,
      min_uptime: '10s',       // must stay up 10 s to count as healthy

      out_file: `${LOG_DIR}/cloudflared-out.log`,
      error_file: `${LOG_DIR}/cloudflared-err.log`,
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',

      env: {
        NODE_ENV: 'production',
      },
    },
  ],
};
