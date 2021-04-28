#!/bin/bash
find /home/ -maxdepth 1 -type d | tail -n +2 | grep -v duc_databases > home_list

mkdir -p /tmp/robinhood2duc/
mkdir -p /home/.duc_databases/

parallel -P 16 --joblog home_joblog --arg-file home_list "./scan.sh lustre02.conf home {/}"
