#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from warnet.process import run_command

assert sys.argv[1] == "entrypoint"
plugin_data = json.loads(sys.argv[2])

if __name__ == "__main__":
    command = f"helm upgrade --install lnvisualizer {Path(__file__).parent / 'charts' / 'lnvisualizer'}"
    for key in plugin_data.keys():
        command += f" --set {key}={plugin_data[key]}"
    run_command(command)
