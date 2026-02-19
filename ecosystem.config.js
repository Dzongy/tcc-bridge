// ecosystem.config.js — PM2 process manager config for TCC Bridge V2
// Manages: bridge_v2.py + cloudflared tunnel

module.exports = {
  apps: [
    {
      name: "tcc-bridge-v2",
      script: "bridge_v2.py",
      interpreter: "python3",
      cwd: process.env.HOME + "/tcc-bridge",
      autorestart: true,
      watch: false,
      max_restarts: 20,
      restart_delay: 4000,
      min_uptime: "10s",
      exp_backoff_restart_delay: 100,
      env: {
        PYTHONUNBUFFERED: "1"
      },
      error_file:  process.env.HOME + "/.pm2/logs/tcc-bridge-v2-error.log",
      out_file:    process.env.HOME + "/.pm2/logs/tcc-bridge-v2-out.log",
      merge_logs:  true,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z"
    },
    {
      name: "cloudflared-tunnel",
      // cloudflared binary expected at ~/bin/cloudflared or in PATH
      script: "cloudflared",
      interpreter: "none",
      args: "tunnel run --token 18ba1a49-fdf9-4a52-a27a-5250d397c5c5",
      cwd: process.env.HOME,
      autorestart: true,
      watch: false,
      max_restarts: 50,
      restart_delay: 5000,
      min_uptime: "5s",
      exp_backoff_restart_delay: 200,
      error_file:  process.env.HOME + "/.pm2/logs/cloudflared-error.log",
      out_file:    process.env.HOME + "/.pm2/logs/cloudflared-out.log",
      merge_logs:  true,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z"
    }
  ]
};
