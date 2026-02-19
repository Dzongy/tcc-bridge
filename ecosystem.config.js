// =============================================================================
// PM2 Ecosystem Config - TCC Zenith
// Manages: Bridge, Cloudflared Tunnel, Cloudflared Monitor
// =============================================================================

module.exports = {
  apps: [
    // -------------------------------------------------------------------------
    // 1. TCC Bridge - The main HTTP server
    // -------------------------------------------------------------------------
    {
      name: 'tcc-bridge',
      script: '/data/data/com.termux/files/home/tcc/bridge.py',
      interpreter: '/data/data/com.termux/files/usr/bin/python3',
      cwd: '/data/data/com.termux/files/home/tcc',
      autorestart: true,
      watch: false,
      max_restarts: 20,
      restart_delay: 3000,
      min_uptime: '10s',
      env: {
        BRIDGE_PORT: '8080',
        BRIDGE_AUTH: process.env.BRIDGE_AUTH || '',
        SUPABASE_URL: 'https://vbqbbziqleymxcyesmky.supabase.co',
        SUPABASE_KEY: process.env.SUPABASE_KEY || '',
        NTFY_OPS_TOPIC: 'zenith-escape',
        NTFY_HIVE_TOPIC: 'tcc-zenith-hive',
        HEARTBEAT_INTERVAL: '30',
        PYTHONUNBUFFERED: '1'
      },
      error_file: '/data/data/com.termux/files/home/tcc/logs/bridge-error.log',
      out_file: '/data/data/com.termux/files/home/tcc/logs/bridge-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true
    },

    // -------------------------------------------------------------------------
    // 2. Cloudflared Tunnel
    // -------------------------------------------------------------------------
    {
      name: 'tcc-tunnel',
      script: 'cloudflared',
      args: 'tunnel --no-autoupdate run --token 18ba1a49-fdf9-4a52-a27a-5250d397c5c5',
      interpreter: 'none',
      autorestart: true,
      watch: false,
      max_restarts: 50,
      restart_delay: 5000,
      min_uptime: '5s',
      error_file: '/data/data/com.termux/files/home/tcc/logs/tunnel-error.log',
      out_file: '/data/data/com.termux/files/home/tcc/logs/tunnel-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true
    },

    // -------------------------------------------------------------------------
    // 3. Cloudflared Monitor - Watchdog for the tunnel
    // -------------------------------------------------------------------------
    {
      name: 'tcc-monitor',
      script: '/data/data/com.termux/files/home/tcc/cloudflared_monitor.py',
      interpreter: '/data/data/com.termux/files/usr/bin/python3',
      cwd: '/data/data/com.termux/files/home/tcc',
      autorestart: true,
      watch: false,
      max_restarts: 20,
      restart_delay: 5000,
      env: {
        HEALTH_URL: 'https://zenith.cosmic-claw.com/health',
        MONITOR_INTERVAL: '60',
        FAIL_THRESHOLD: '3',
        PM2_PROCESS: 'tcc-tunnel',
        RESTART_COOLDOWN: '120',
        PYTHONUNBUFFERED: '1'
      },
      error_file: '/data/data/com.termux/files/home/tcc/logs/monitor-error.log',
      out_file: '/data/data/com.termux/files/home/tcc/logs/monitor-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true
    }
  ]
};
