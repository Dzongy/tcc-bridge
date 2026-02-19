// TCC Bridge — PM2 Ecosystem Config
// Optional: If Commander has Node.js + PM2 installed
//   npm install -g pm2
//   pm2 start ecosystem.config.js
//   pm2 save
module.exports = {
  apps: [
    {
      name: "tcc-bridge",
      script: "python",
      args: "bridge.py",
      cwd: "/data/data/com.termux/files/home/tcc-bridge",
      interpreter: "none",
      autorestart: true,
      watch: false,
      max_restarts: 100,
      restart_delay: 3000,
      max_memory_restart: "100M",
      env: {
        BRIDGE_AUTH: "amos-bridge-2026",
        BRIDGE_PORT: "8080",
        NTFY_TOPIC: "tcc-zenith-hive",
        SUPABASE_URL: "https://vbqbbziqleymxcyesmky.supabase.co",
      },
      error_file: "/data/data/com.termux/files/home/bridge-pm2-error.log",
      out_file: "/data/data/com.termux/files/home/bridge-pm2-out.log",
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
    },
    {
      name: "cloudflared",
      script: "cloudflared",
      args: "tunnel --config /data/data/com.termux/files/home/.cloudflared/config.yml run",
      interpreter: "none",
      autorestart: true,
      watch: false,
      max_restarts: 50,
      restart_delay: 5000,
      error_file: "/data/data/com.termux/files/home/cloudflared-pm2-error.log",
      out_file: "/data/data/com.termux/files/home/cloudflared-pm2-out.log",
    },
  ],
};
