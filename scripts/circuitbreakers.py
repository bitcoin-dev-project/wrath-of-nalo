#!/usr/bin/env python3

import json
import os
import subprocess
import threading

cmd = "warnet ln rpc miner-ln describegraph"
graph = json.loads(subprocess.check_output(cmd, shell=True).decode())
nodes = graph["nodes"]

keys = []
aliases = []
for node in nodes:
    print(f"{node['pub_key']} {node['alias']}")
    keys.append(node['pub_key'])
    aliases.append(node['alias'])

def update_limits(alias):
    for key in keys:
            update = f'{{"limits":{{"{key}":{{"maxHourlyRate":"0","maxPending":"0","mode":"MODE_FAIL"}}}}}}'
            cmd = f"kubectl exec {alias.split(".")[0]} -c circuitbreaker -- wget -qO-  --post-data='{update}' 127.0.0.1:9235/api/updatelimits"
            try:
                print(cmd, subprocess.check_output(cmd, shell=True).decode())
            except Exception as e:
                print(cmd, "(failed)")

threads = [
    threading.Thread(target=update_limits, args=(alias,)) for alias in aliases if "cb" in alias
]
for thread in threads:
    thread.start()

all(thread.join() is None for thread in threads)
