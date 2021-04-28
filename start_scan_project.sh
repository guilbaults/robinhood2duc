#!/bin/bash
find /project/ -maxdepth 1 -type l > project_list

mkdir -p /tmp/robinhood2duc/
mkdir -p /project/.duc_databases/

parallel -P 16 --joblog project_joblog --arg-file project_list "./scan.sh lustre03.conf project {/}"
