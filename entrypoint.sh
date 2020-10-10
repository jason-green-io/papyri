#!/bin/bash

# turn on bash's job control
set -m

# extract environment variables for cron
printenv | sed 's/^\(.*\)$/export \1/g' > /root/project_env.sh

# create cron file from environment schedule
crontab << EOM
SHELL=/bin/bash
BASH_ENV=/root/project_env.sh
$SCHEDULE python /papyri/papyri.py --type $TYPE --world /data/world --output /output > /proc/1/fd/1 2>&1

EOM

# rsyslog is required for cron to have output
service rsyslog start

# If webserver is enabled, run cron in background and server in foreground, otherwise just cron in foreground
if [ "$WEBSERVER" = true ]
then
  service cron start
  python -m http.server 80 -d /output
else
  cron -f
fi
