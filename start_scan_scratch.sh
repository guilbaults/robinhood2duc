#!/bin/bash
find /scratch/ -maxdepth 1 -type d | tail -n +2 | grep -v duc_databases > scratch_list

mkdir -p /tmp/robinhood2duc/
mkdir -p /scratch/.duc_databases/

parallel -P 16 --joblog scratch_joblog --arg-file scratch_list "./scan.sh lustre04.conf scratch {/}"
