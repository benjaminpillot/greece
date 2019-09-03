#!/usr/bin/env bash
interpreter=`command -v python3`

if [[ -z "$interpreter" ]]
then
echo "No Python interpreter found ! Exiting !"
exit 2
else
solar_ghi.py "$1"
fi
