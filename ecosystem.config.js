
module.exports = {
  apps: [
    {
      name: "tcc-bridge",
      script: "python3",
      args: "bridge.py",
      cwd: "/data/data/com.termux/files/home/tcc",
      autorestart: true,
      restart_delay: 5000,
      env: {
        BRIDGE_AUTH: "amos-bridge-2026",
        BRIDGE_PORT: "8080",
        SUPABASE_URL: "https://vbqbbziqleymxcyesmky.supabase.co",
        NTFY_TOPIC: "tcc-zenith-hive",
        PUBLIC_URL: "https://zenith.cosmic-claw.com"
      }
    },
    {
      name: "cloudflared",
      script: "cloudflared",
      args: "tunnel run",
      autorestart: true,
      restart_delay: 10000
    }
  ]
};
