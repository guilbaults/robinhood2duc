#!/bin/bash
# echo Scanning project directory ${1} in /project
rbh=$1
fs=$2
p=$3

if [[ -z ${rbh} ]]; then
	echo missing rbh config path
	exit 1
fi
if [[ -z ${fs} ]]; then
	echo missing fs name
	exit 1
fi
if [[ -z ${p} ]]; then
	echo missing path
	exit 1
fi

python crawl.py /etc/robinhood.d/${rbh} /${fs}/${p} /tmp/robinhood2duc/${fs}_${p}.sqlite
status=$?

chown root:${p} /tmp/robinhood2duc/${fs}_${p}.sqlite
chmod 740 /tmp/robinhood2duc/${fs}_${p}.sqlite

mv /tmp/robinhood2duc/${fs}_${p}.sqlite /${fs}/.duc_databases/${p}.sqlite

exit $status
