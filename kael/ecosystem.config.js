// PM2 Ecosystem Config â Bridge V2
// Usage: pm2 start ecosystem.config.js

const HOME = process.env.HOME || '/data/data/com.termux/files/home';

module.exports = {
  apps: [
    {
      name: 'bridge',
      script: `${HOME}/bridge.py`,
      interpreter: 'python3',
      cwd: HOME,
      watch: false,
      autorestart: true,
      max_restarts: 20,
      min_uptime: '10s',
      restart_delay: 3000,
      env: {
        PYTHONUNBUFFERED: '1'
      },
      out_file: `${HOME}/bridge.out.log`,
      error_file: `${HOME}/bridge.err.log`,
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    },
    {
      name: 'watchdog',
      script: `${HOME}/watchdog.py`,
      interpreter: 'python3',
      cwd: HOME,
      watch: false,
      autorestart: true,
      max_restarts: 20,
      min_uptime: '10s',
      restart_delay: 5000,
      env: {
        PYTHONUNBUFFERED: '1'
        // SUPABASE_KEY is inherited from environment or set here:
        // SUPABASE_KEY: 'your-key-here'
      },
      out_file: `${HOME}/watchdog.out.log`,
      error_file: `${HOME}/watchdog.err.log`,
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    },
    {
      name: 'state-push',
      script: `${HOME}/state-push.py`,
      interpreter: 'python3',
      cwd: HOME,
      watch: false,
      autorestart: true,
      max_restarts: 20,
      min_uptime: '10s',
      restart_delay: 5000,
      env: {
        PYTHONUNBUFFERED: '1'
        // SUPABASE_KEY: 'your-key-here'
      },
      out_file: `${HOME}/state-push.out.log`,
      error_file: `${HOME}/state-push.err.log`,
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    },
    {
      name: 'cloudflared',
      script: 'cloudflared',
      args: 'tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5',
      interpreter: 'none',
      cwd: HOME,
      watch: false,
      autorestart: true,
      max_restarts: 30,
      min_uptime: '10s',
      restart_delay: 5000,
      out_file: `${HOME}/cloudflared.out.log`,
      error_file: `${HOME}/cloudflared.err.log`,
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    }
  ]
};
