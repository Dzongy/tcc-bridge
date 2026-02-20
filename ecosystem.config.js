// ecosystem.config.js â TCC Bridge V3 PM2 Process Manager Configuration
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
    // ââ 1. TCC Bridge API (bridge.py) ââââââââââââââââââââââââââââââââââââââ
    {
      name: 'tcc-bridge',
      script: `${BRIDGE_DIR}/bridge.py`,
      interpreter: 'python3',
      cwd: BRIDGE_DIR,

      // Restart behaviour
      autorestart: true,
      watch: false,
      max_restarts: 100,
      restart_delay: 3000,
      exp_backoff_restart_delay: 100,

      // Logging
      out_file: `${LOG_DIR}/bridge-out.log`,
      error_file: `${LOG_DIR}/bridge-err.log`,
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',

      // Environment â CORRECTED PORT AND SUPABASE
      env: {
        PYTHONUNBUFFERED: '1',
        BRIDGE_PORT: '8765',
        SUPABASE_URL: 'https://vbqbbziqleymxcyesmky.supabase.co',
        SUPABASE_KEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZicWJiemlxbGV5bXhjeWVzbWt5Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTExMTUxNiwiZXhwIjoyMDg2Njg3NTE2fQ.MREdeLv0R__fHe61lOYSconedoo_qHItZUpmcR-IORQ',
        BRIDGE_AUTH: 'amos-bridge-2026',
        PUBLIC_URL: 'zenith.cosmic-claw.com',
        NODE_ENV: 'production',
      },
    },

    // ââ 2. State Push Worker (state-push.py) âââââââââââââââââââââââââââââââ
    {
      name: 'tcc-state-push',
      script: `${BRIDGE_DIR}/state-push.py`,
      interpreter: 'python3',
      cwd: BRIDGE_DIR,

      autorestart: true,
      watch: false,
      max_restarts: 50,
      restart_delay: 5000,

      out_file: `${LOG_DIR}/state-push-out.log`,
      error_file: `${LOG_DIR}/state-push-err.log`,
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',

      env: {
        PYTHONUNBUFFERED: '1',
        SUPABASE_URL: 'https://vbqbbziqleymxcyesmky.supabase.co',
        SUPABASE_KEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZicWJiemlxbGV5bXhjeWVzbWt5Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTExMTUxNiwiZXhwIjoyMDg2Njg3NTE2fQ.MREdeLv0R__fHe61lOYSconedoo_qHItZUpmcR-IORQ',
      },
    },

    // ââ 3. Cloudflare Tunnel âââââââââââââââââââââââââââââââââââââââââââââââ
    {
      name: 'tcc-cloudflared',
      script: 'cloudflared',
      args: `tunnel --no-autoupdate run --token ${process.env.CF_TOKEN || ''}`,
      interpreter: 'none',
      cwd: BRIDGE_DIR,

      autorestart: true,
      watch: false,
      max_restarts: 50,
      restart_delay: 5000,

      out_file: `${LOG_DIR}/tunnel-out.log`,
      error_file: `${LOG_DIR}/tunnel-err.log`,
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },

    // ââ 4. Watchdog ââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
    {
      name: 'tcc-watchdog',
      script: `${BRIDGE_DIR}/watchdog.sh`,
      interpreter: 'bash',
      cwd: BRIDGE_DIR,

      autorestart: true,
      watch: false,
      max_restarts: 10,
      restart_delay: 10000,

      out_file: `${LOG_DIR}/watchdog-out.log`,
      error_file: `${LOG_DIR}/watchdog-err.log`,
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },
  ],
};
