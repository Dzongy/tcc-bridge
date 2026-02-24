module.exports = {
  apps : [
    {
      name : 'kael-sovereignty',
      script : '/data/data/com.termux/files/home/tcc-bridge/sovereignhy/run_kael.sh',
      interpreter : '/bin/bash',
      cwd : '/data/data/com.termux/files/home/tcc-bridge/sovereignty',
      kill_timeout : 3000,
      shutdown_with_message : true,
      autorestart : true,
      max_restarts : 100,
      restart_delay : 5000
    },
    {
      name : 'chris-sovereignty',
      script : '/bin/bash',
      args : '/data/data/com.termux/files/home/tcc-bridge/sovereignhy/run_chris.sh',
      cwd : '/data/data/com.termux/files/home/tcc-bridge/sovereignhy',
      kill_timeout : 3000,
      shutdown_with_message : true,
      autorestart : true,
      max_restarts : 100,
      restart_delay : 5000
    }
  ]
}
