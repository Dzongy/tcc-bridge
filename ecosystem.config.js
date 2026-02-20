// ecosystem.config.js ð¡ï¸ TCC Bridge V3 PM2 Process Manager Configuration
// Place at: ~/tcc-bridge/ecosystem.config.js
// Usage:  pm2 start ecosystem.config.js
//         pm2 reload ecosystem.config.js --update-env

const os = require('os');
const HOME = os.homedir();
const BRIDGE_DIR = `${HOME}/tcc-bridge`;
const LOG_DIR = `${BRIDGE_DIR}/logs`;
const SOVEREIGNTY_DIR = `${BRIDGE_DIR}/sovereignty`;
const TUNNEL_UUID = '18ba1a49-fdf9-4a52-a27a-5250d397c5c5';

module.exports = {
  apps: [
    {
      name: 'kael-sovereignty',
      script: `${SOVEREIGNTY_DIR}/run_kael.sh`,
      interpreter: '/bin/bash',
      cwd: SOVEREIGNTY_DIR,
      autorestart: true,
      max_restarts: 100,
      restart_delay: 5000,
      kill_timeout: 3000,
      shutdown_with_message: true,
    },
    {
      name: 'chris-sovereignty',
      script: `${SOVEREIGNTY_DIR}/run_chris.sh`,
      interpreter: '/bin/bash',
      cwd: SOVEREIGNTY_DIR,
      autorestart: true,
      max_restarts: 100,
      restart_delay: 5000,
      kill_timeout: 3000,
      shutdown_with_message: true,
    },
    // ð¡ï¸ð¡ï¸ 1. TCC Bridge API (bridge.py) ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´
    {
      name: 'tcc-bridge',
      script: `${BRIDGE_DIR}/bridge.py`,
      interpreter: 'python3',
      cwd: BRIDGE_DIR,
      error_file: `${LOG_DIR}/bridge-err.log`,
      out_file: `${LOG_DIR}/bridge-out.log`,
      autorestart: true,
      max_restarts: 100,
      restart_delay: 5000,
      env: {
        BRIDGE_PORT: '8080',
        BRIDGE_AUTH: 'amos-bridge-2026',
        NTFY_TOPIC: 'zenith-escape',
      }
    },
    // ð¡ï¸ð¡ï¸ 2. Cloudflare Tunnel ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´ð´
    {
      name: 'tcc-cloudflared',
      script: 'cloudflared',
      args: `tunnel run ${TUNNEL_UUID}`,
      autorestart: true,
      restart_delay: 5000,
    }
  ]
};
