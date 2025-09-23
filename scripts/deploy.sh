#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Usage: $0 <game name>"
    exit 1
fi

warnet deploy armies/$1
warnet admin create-kubeconfigs
warnet deploy battlefields/$1
warnet deploy armadas/$1 --to-all-users
