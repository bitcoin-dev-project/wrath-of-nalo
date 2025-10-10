#!/usr/bin/env python3

import json
import os
import random
import secrets
import sys
import yaml
from pathlib import Path
from random import randbytes, choice
from base64 import b64encode
from subprocess import run

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from test_framework.key import ECKey  # noqa: E402
from test_framework.script_util import key_to_p2wpkh_script  # noqa: E402
from test_framework.wallet_util import bytes_to_wif  # noqa: E402
from test_framework.descriptors import descsum_create  # noqa: E402

TEAMS = [
    "aries",
    "taurus",
    "gemini",
    "cancer",
    "leo",
    "virgo",
    "libra",
    "scorpio",
    "sagittarius",
    "capricorn",
    "aquarius",
    "pisces"
]

COLORS = [
    "#e6194b",
    "#3cb44b",
    "#ffe119",
    "#4363d8",
    "#f58231",
    "#911eb4",
    "#46f0f0",
    "#f032e6",
    "#bcf60c",
    "#fabebe",
    "#008080",
    "#e6beff"
]

class Node:
    def __init__(self, game, name):
        self.game = game
        self.name = name
        self.bitcoin_image = {"tag": "29.0"}
        self.rpcpassword = secrets.token_hex(16)

        self.addnode = []

        self.lnd_image = {"tag": "v0.19.0-beta"}
        self.lnd_color = "#3399FF"

        self.root_key_base64 = None
        self.admin_macaroon = None
        self.generate_macaroon()

        self.channels = []

    def generate_macaroon(self):
        entropy = randbytes(32)
        key_hex = entropy.hex()
        key_b64 = b64encode(entropy).decode()
        response = run(
            [
                "lncli",
                "bakemacaroon",
                f"--root_key={key_hex}",
                "address:read",
                "address:write",
                "info:read",
                "info:write",
                "invoices:read",
                "invoices:write",
                "macaroon:generate",
                "macaroon:read",
                "macaroon:write",
                "message:read",
                "message:write",
                "offchain:read",
                "offchain:write",
                "onchain:read",
                "onchain:write",
                "peers:read",
                "peers:write",
                "signer:generate",
                "signer:read"
            ],
            capture_output=True
        )
        self.root_key_base64 = key_b64
        self.admin_macaroon = response.stdout.decode().strip()

    def channel(self, tgt, capacity):
        self.game.add_channel(self, tgt, capacity)

    def to_obj(self):
        return {
            "name": self.name,
            "image": self.bitcoin_image,
            "global": {
                "rpcpassword": self.rpcpassword,
                "chain": self.game.chain
            },
            "config":
                f'maxconnections=1000\n' +
                f'uacomment={self.name}\n' +
                (f'signetchallenge={self.game.signetchallenge}\n' if self.game.chain == 'signet' else '') +
                'coinstatsindex=1',
            "addnode": self.addnode,
            "ln": {"lnd": True},
            "lnd": {
                "image": self.lnd_image,
                **({"channels": self.channels} if self.channels else {}),
                "macaroonRootKey": self.root_key_base64,
                "adminMacaroon": self.admin_macaroon,
                "config": f"color={self.lnd_color}"
            }
        }

class GossipVulnNode(Node):
    def __init__(self, game, name):
        super().__init__(game, name)
        self.bitcoin_image = {"tag": "25.1"}
        self.lnd_image = {"tag": "v0.18.2-beta"}

    def to_obj(self):
        obj = super().to_obj()
        obj["lnd"].update({
            "restartPolicy": "Never",
            "resources": {
                "limits": {
                    "cpu": "4000m",
                    "memory": "500Mi"
                },
                "requests": {
                    "cpu": "100m",
                    "memory": "200Mi"
                }
            }
        })
        return obj

class MetricsNode(Node):
    def to_obj(self):
        obj = super().to_obj()
        obj["lnd"].update({
            "metricsExport": True,
            "prometheusMetricsPort": 9332,
            "extraContainers": [
                {
                    "name": "lnd-exporter",
                    "image": "bitcoindevproject/lnd-exporter:0.2.0",
                    "imagePullPolicy": "IfNotPresent",
                    "volumeMounts": [
                        {
                            "name": "config",
                            "mountPath": "/macaroon.hex",
                            "subPath": "MACAROON_HEX"
                        }
                    ],
                    "env": [
                        {
                            "name": "METRICS",
                            "value":
                                'lnd_block_height=parse("/v1/getinfo","block_height") '
                        }
                    ],
                    "ports": [
                        {
                            "name": "prom-metrics",
                            "containerPort": 9332,
                            "protocol": "TCP",
                        }
                    ]
                }
            ]
        })
        return obj

class SpenderNode(MetricsNode):
    def to_obj(self):
        obj = super().to_obj()
        obj["lnd"]["extraContainers"][0]["env"][0]["value"] += 'failed_payments=FAILED_PAYMENTS '
        return obj

class RoutingNode(MetricsNode):
    def to_obj(self):
        obj = super().to_obj()
        obj["lnd"]["extraContainers"][0]["env"][0]["value"] += 'pending_htlcs=PENDING_HTLCS '
        return obj

class RecipientNode(MetricsNode):
    def to_obj(self):
        obj = super().to_obj()
        obj["lnd"]["extraContainers"][0]["env"][0]["value"] += 'lnd_balance_channels=parse("/v1/balance/channels","balance") '
        return obj

class Miner(Node):
    def __init__(self, game):
        super().__init__(game, "miner")
        self.bitcoin_image = {"tag": "29.0-util"}

    def to_obj(self):
        obj = super().to_obj()
        obj.update({
            "startupProbe": {
                "failureThreshold": 10,
                "periodSeconds": 30,
                "successThreshold": 1,
                "timeoutSeconds": 60,
                "exec": {
                    "command": [
                        "/bin/sh",
                        "-c",
                        "bitcoin-cli createwallet miner && " +
                        f"bitcoin-cli importdescriptors {self.game.desc_string}"
                    ]
                }
            },
            "lnd": {
                "extraContainers": [
                    {
                        "name": "lnvisweb",
                        "image": "bitcoindevproject/lnvisualizer:latest",
                        "ports": [
                            {
                                "name": "web",
                                "containerPort": 80,
                                "protocol": "TCP"
                            }
                        ],
                        "env": [
                            {
                              "name": "LN_VISUALIZER_API_URL",
                              "value": "http://127.0.0.1:5647"
                            }
                        ]
                    },
                    {
                        "name": "lnvisapi",
                        "image": "maxkotlan/ln-visualizer-api:v0.0.28",
                        "ports": [
                            {
                                "name": "api",
                                "containerPort": 5647,
                                "protocol": "TCP"
                            }
                        ],
                        "env": [
                            {
                                "name": "LND_CERT_FILE",
                                "value": "/tls.cert"
                            },
                            {
                                "name": "LND_MACAROON_FILE",
                                "value": f"/root/.lnd/data/chain/bitcoin/{self.game.chain}/admin.macaroon"
                            },
                            {
                                "name": "LND_SOCKET",
                                "value": "localhost:10009"
                            },
                            {
                                "name": "LNVIS_RESYNCTIMER",
                                "value": "* * * * *"
                            }
                        ],
                        "volumeMounts": [
                            {
                                "name": "shared-volume",
                                "mountPath": "/root/.lnd/"
                            },
                            {
                                "name": "config",
                                "mountPath": "/tls.cert",
                                "subPath": "tls.cert"
                            }
                        ]
                    }
                ]
            }
        })
        return obj

class Game:
    def __init__(self, network_name, chain="signet"):
        print(f"\n**\n* Creating game {network_name}")
        self.network_name = network_name
        self.signetchallenge = None
        self.desc_string = None
        self.chain = chain
        self.generate_signet()

        self.miner = None
        self.nodes = []
        self.channels = {
            "next_index": {
                "block": 500,
                "index": 1
            },
            "target_by_source": {},
            "total": 0
        }

    def generate_signet(self):
        # generate entropy
        secret = secrets.token_bytes(32)

        # derive private key and set global signet challenge (simple p2wpkh script)
        privkey = ECKey()
        privkey.set(secret, True)
        pubkey = privkey.get_pubkey().get_bytes()
        challenge = key_to_p2wpkh_script(pubkey)
        self.signetchallenge = challenge.hex()

        # output a bash script that executes warnet commands creating
        # a wallet on the miner node that can create signet blocks
        privkeywif=bytes_to_wif(secret)
        desc = descsum_create('combo(' + privkeywif + ')')
        desc_import = [{
            'desc': desc,
            'timestamp': 0
        }]
        desc_string = json.dumps(desc_import)
        self.desc_string = desc_string.replace("\"", "\\\"").replace(" ", "").replace("(", "\\(").replace(")", "\\)").replace(",", "\\,")

    def add_nodes(self, num_nodes):
        for n in range(num_nodes):
            self.nodes.append(Node(self, f"tank-{len(self.nodes):04d}"))

    def get_new_channel_id(self):
        assign = self.channels["next_index"].copy()
        self.channels["next_index"]["index"] += 1
        if self.channels["next_index"]["index"] > 200:
            self.channels["next_index"]["index"] = 1
            self.channels["next_index"]["block"] += 1
        return assign

    def add_channel(self, src, tgt, capacity, options = None):
        print(f" adding channel: {src.name}->{tgt.name} {capacity} sats")
        if src not in self.channels["target_by_source"]:
            self.channels["target_by_source"][src] = []
        self.channels["target_by_source"][src].append(tgt)
        src.channels.append({
            "id": self.get_new_channel_id(),
            "target": f"{tgt.name}-ln",
            "capacity": capacity,
            **(options or {})
        })
        self.channels["total"] += 1

    def add_random_channels(self, n):
        print(f"Adding {n} random channels")
        # random for now
        while n > 0:
            src = choice(self.nodes)
            tgt = choice(self.nodes)
            # No self connections
            if src == tgt:
                print(" avoiding self-connect")
                continue
            # Leave target recipients alones so balances are even
            if "recipient" in tgt.name or "recipient" in src.name:
                print(" not getting involved with recipient nodes")
                continue
            # One channel per peer pair please
            if src in self.channels["target_by_source"] and tgt in self.channels["target_by_source"][src]:
                print(f" avoiding duplicate {src.name}->{tgt.name}")
                continue
            if tgt in self.channels["target_by_source"] and src in self.channels["target_by_source"][tgt]:
                print(f" avoiding reverse {src.name}->{tgt.name}")
                continue
            capacity = random.randint(1000000, 10000000)
            self.add_channel(src, tgt, capacity, {"push_amt": random.randint(capacity // 8, capacity // 2)})
            n -= 1

    def add_miner(self):
        miner = Miner(self)
        self.miner = miner
        # connect all nodes to miner
        for node in self.nodes:
            node.addnode.append("miner")
        # do this last, don't connect to self
        self.nodes.append(miner)

    def add_payment_routes(self, n):
        for i in range(n):
            team = TEAMS[i]
            # Create 3-node chain of channels: spender->router->recipient
            spender = SpenderNode(self, f"{team}-spender")
            spender.lnd_color = COLORS[i]
            router = RoutingNode(self, f"{team}-router")
            router.lnd_color = COLORS[i]
            recipient = RecipientNode(self, f"{team}-recipient")
            recipient.lnd_color = COLORS[i]
            self.nodes.append(spender)
            self.nodes.append(router)
            self.nodes.append(recipient)
            self.add_channel(spender, router, int(2e8), {"push_amt": 0})
            self.add_channel(router, recipient, int(2e8), {"push_amt": 0})
            # Insert a vulnerable node for DoS attacks
            vuln = GossipVulnNode(self, f"{team}-vuln")
            vuln.lnd_color = COLORS[i]
            self.nodes.append(vuln)

    def write(self):
        network = {
            "nodes": [n.to_obj() for n in self.nodes],
            "caddy": {"enabled": True},
            "services": [
                {
                    "title": "LN Visualizer Web UI",
                    "path": "/lnvisualizer/",
                    "host": "lnvisualizer.default",
                    "port": 80
                }
            ],
            "plugins": {
                "preDeploy": {
                    "lnvisualizer": {
                        "entrypoint": "../../plugins/lnvisualizer",
                        "instance": "miner",
                        "name": "lnd-ln"
                    }
                }
            }
        }
        self.write_network_yaml_dir("battlefields", network)


        armada = [
            Node(self, "armada-1"),
            Node(self, "armada-2"),
            Node(self, "armada-3")
        ]
        for n in armada:
            n.addnode.append("miner.default")
        self.write_network_yaml_dir("armadas", {"nodes": [n.to_obj() for n in armada]})

    def write_armies(self, n):
        data = { "namespaces": [] }
        for i in range(n):
            data['namespaces'].append({"name": "wargames-" + TEAMS[i]})
        default = {
            "users": [
                {
                    "name": "warnet-user",
                    "roles": [
                        "pod-viewer",
                        "pod-manager",
                        "ingress-viewer",
                        "ingress-controller-viewer"
                    ]
                }
            ]
        }
        self.write_yaml_dir("armies", data, default, "namespaces.yaml", "namespace-defaults.yaml")

    def write_network_yaml_dir(self, subdir, data):
        self.write_yaml_dir(subdir, data, {"warnet": self.network_name}, "network.yaml", "node-defaults.yaml")

    def write_yaml_dir(self, subdir, main_data, defaults_data, main_filename, defaults_filename):
        try:
            print("Creating armada directory...")
            os.mkdir(Path(os.path.dirname(__file__)) / ".." / subdir / self.network_name)
        except FileExistsError:
            print("...already exists")
        with open(Path(os.path.dirname(__file__)) / ".." / subdir / self.network_name / main_filename, "w") as f:
            print(f"Writing {main_filename}...")
            yaml.dump(main_data, f, default_flow_style=False)
        with open(Path(os.path.dirname(__file__)) / ".." / subdir / self.network_name / defaults_filename, "w") as f:
            print(f"Writing {defaults_filename}...")
            yaml.dump(defaults_data, f, default_flow_style=False)


g = Game("signet100", "signet")
g.add_payment_routes(len(TEAMS))
g.add_nodes(40)
g.add_random_channels(200)
g.add_miner()
g.write()
g.write_armies(len(TEAMS))

g = Game("regtest4", "regtest")
g.add_payment_routes(1)
g.add_nodes(2)
g.add_random_channels(3)
g.add_miner()
g.write()
g.write_armies(1)
