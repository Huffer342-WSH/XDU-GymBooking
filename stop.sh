#!/bin/bash

SCRIPT="main_once.py"

PIDS=$(ps -ef | grep "$SCRIPT" | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "No process found."
    exit 0
fi

echo "Stopping PIDs: $PIDS"
kill $PIDS
