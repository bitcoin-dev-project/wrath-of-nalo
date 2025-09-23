#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Usage: $0 <game name>"
    exit 1
fi

warnet deploy battlefields/$1
warnet deploy armies/$1
warnet admin create-kubeconfigs
warnet deploy armadas/$1 --to-all-users
warnet run scenarios/arm_armada.py --debug --admin
warnet run scenarios/miner_std.py --tank=miner --admin
warnet run scenarios/ln_activity.py
./scripts/upload_grafana_dashboard.py