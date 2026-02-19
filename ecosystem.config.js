module.exports = {
  apps: [
    {
      name: "bridge",
      script: "bridge.py",
      interpreter: "python3",
      restart_delay: 5000
    },
    {
      name: "tunnel",
      script: "cloudflared",
      args: "tunnel run 18ba1a49-fdf9-4a52-a27a-5250d397c5c5",
      restart_delay: 10000
    },
    {
      name: "watchdog",
      script: "watchdog-v2.sh",
      interpreter: "bash"
    },
    {
      name: "state-push",
      script: "state-push.py",
      interpreter: "python3",
      restart_delay: 10000
    }
  ]
};