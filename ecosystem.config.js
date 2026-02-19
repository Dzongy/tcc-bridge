
module.exports = {
  apps: [
    {
      name: "tcc-bridge",
      script: "python3",
      args: "bridge_v2.py",
      cwd: "/data/data/com.termux/files/home/tcc-bridge",
      autorestart: true,
      restart_delay: 5000,
      env: {
        SUPABASE_URL: "https://vbqbbziqleymxcyesmky.supabase.co",
        SUPABASE_KEY: "sb_secret_lIbl-DBgdnrt_fejgJjKqg_qR62SVEm",
        NTFY_TOPIC: "zenith-escape",
        PUBLIC_URL: "https://zenith.cosmic-claw.com"
      }
    },
    {
      name: "cloudflared",
      script: "cloudflared",
      args: "tunnel --config /data/data/com.termux/files/home/.cloudflared/config.yml run",
      autorestart: true,
      restart_delay: 10000
    }
  ]
};
