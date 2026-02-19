module.exports = {
  apps: [
    {
      name: "tcc-bridge",
      script: "python3",
      args: "bridge.py",
      cwd: "/data/data/com.termux/files/home/tcc-bridge",
      autorestart: true,
      watch: ["bridge.py"],
      max_memory_restart: "100M",
      env: {
        NODE_ENV: "production",
      }
    }
  ]
};
