module.exports = {
  apps: [
    {
      name: "bridge",
      script: "./bridge.py",
      interpreter: "python3",
      env: { BRIDGE_PORT: 8080 }
    },
    {
      name: "cloudflared",
      script: "cloudflared",
      args: "tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5"
    },
    {
      name: "watchdog",
      script: "./watchdog-v2.sh",
      interpreter: "bash"
    }
  ]
};
