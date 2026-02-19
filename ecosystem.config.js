module.exports = {
  apps: [
    {
      name: "tcc-bridge",
      script: "bridge.py",
      interpreter: "python3",
      autorestart: true,
      watch: false,
      max_memory_restart: "100M",
      env: {
        BRIDGE_PORT: 8765,
        NTFY_TOPIC: "tcc-zenith-hive"
      }
    },
    {
      name: "state-push",
      script: "state-push.py",
      interpreter: "python3",
      autorestart: true,
      watch: false
    }
  ]
};