#!/usr/bin/env python3

import base64
import json
import random
from commander import Commander

class LNChannelJam(Commander):
    def set_test_params(self):
        # This is just a minimum
        self.num_nodes = 0
        self.miners = []

    def add_options(self, parser):
        parser.description = "Send hold invoices between two lightning nodes"
        parser.usage = "warnet run /path/to/ln_channel_jam.py"

    def run_test(self):
        # Some node name
        SENDER =
        # Some other node name
        RECEIVER =
        # Some integer
        AMT_SATS = 

        # Clear the Warnet default random seed
        random.seed(None)
        # Create a hold invoice on a LN node using the REST API
        # https://lightning.engineering/api-docs/api/lnd/invoices/add-hold-invoice/
        payment_hash = base64.b64encode(random.randbytes(32)).decode()
        response = self.lns[RECEIVER].post(
            "/v2/invoices/hodl",
            data={
                "value": AMT_SATS,
                "hash":  payment_hash
            }
        )
        json_response = json.loads(response)
        self.log.info(f"Got hold invoice from {RECEIVER}: add_index: {json_response['add_index']}")
        invoice = json_response["payment_request"]

        # Attempt to pay the invoice on some other node using warnet helper functions
        response = self.lns[SENDER].payinvoice(invoice)
        self.log.info(f"Sent payment from {SENDER}: payment_index: {response['result']['payment_index']}")


def main():
    LNChannelJam("").main()

if __name__ == "__main__":
    main()
