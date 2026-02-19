module.exports = {
  apps: [
    {
      name: "tcc-bridge",
      script: "python3",
      args: "bridge.py",
      restart_delay: 3000,
      max_restarts: 10,
      env: {
        SUPABASE_URL: "https://vbqbbziqleymxcyesmky.supabase.co",
        SUPABASE_KEY: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZicWJiemlxbGV5bXhjeWVzbWt5Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTExMTUxNiwiZXhwIjoyMDg2Njg3NTE2fQ.MREdeLv0R__fHe61lOYSconedoo_qHItZUpmcR-IORQ",
        NTFY_TOPIC: "tcc-zenith-hive"
      }
    },
    {
      name: "tcc-tunnel",
      script: "cloudflared",
      args: "tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5",
      restart_delay: 5000,
      max_restarts: 50
    }
  ]
};