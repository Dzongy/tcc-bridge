module.exports = {
  apps: [
    {
      name: "tcc-bridge",
      script: "python3",
      args: "bridge.py",
      autorestart: true,
      restart_delay: 5000,
      env: {
        BRIDGE_PORT: "8765",
        BRIDGE_AUTH: "amos-bridge-2026",
        NTFY_TOPIC: "tcc-zenith-hive",
        PUBLIC_URL: "https://zenith.cosmic-claw.com",
        SUPABASE_URL: "https://vbqbbziqleymxcyesmky.supabase.co"
      }
    },
    {
      name: "cloudflared",
      script: "cloudflared",
      args: "tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5",
      autorestart: true,
      restart_delay: 10000
    },
    {
      name: "tcc-state-push",
      script: "python3",
      args: "state-push.py",
      autorestart: true,
      restart_delay: 300000
    }
  ]
};