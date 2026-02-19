
module.exports = {
  apps: [
    {
      name: "tcc-bridge",
      script: "python3",
      args: "bridge.py",
      autorestart: true,
      watch: false,
      max_memory_restart: "100M",
      env: {
        BRIDGE_PORT: 8080
      }
    },
    {
      name: "tcc-state-push",
      script: "python3",
      args: "state-push.py",
      autorestart: true,
      env: {
        SUPABASE_URL: "https://vbqbbziqleymxcyesmky.supabase.co",
        NTFY_TOPIC: "tcc-zenith-hive"
      }
    },
    {
      name: "tcc-tunnel",
      script: "cloudflared",
      args: "tunnel run --token YOUR_TOKEN_HERE",
      autorestart: true
    }
  ]
};
