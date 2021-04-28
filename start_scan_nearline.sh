#!/bin/bash
find /nearline/ -maxdepth 1 -type l | grep -v duc_databases > nearline_list

mkdir -p /tmp/robinhood2duc/

parallel -P 16 --joblog nearline_joblog --arg-file nearline_list "./scan.sh lustre03.conf nearline {/}"
