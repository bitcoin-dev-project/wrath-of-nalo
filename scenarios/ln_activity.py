#!/usr/bin/env python3

import base64
import hashlib
import json
import secrets
import threading
from commander import Commander
from time import sleep

class LNActivity(Commander):
    def set_test_params(self):
        # This is just a minimum
        self.num_nodes = 0
        self.miners = []

    def add_options(self, parser):
        parser.description = "Send LN payments"
        parser.usage = "warnet run /path/to/ln_activity.py [options]"

    def run_test(self):
        def make_payments(self, src, tgt_pubkey):
            while True:
                # ensure all payments are above dust limit
                amt = 600
                preimage = secrets.token_bytes(32)
                payment_hash = hashlib.sha256(preimage).digest()
                try:
                    response = src.post(
                        "/v2/router/send",
                        data={
                            "dest": src.hex_to_b64(tgt_pubkey),
                            "amt": amt,
                            "payment_hash": base64.b64encode(payment_hash).decode(),
                            "fee_limit_sat": 1,
                            "dest_custom_records": {
                                "5482373484": base64.b64encode(preimage).decode()
                            }
                        },
                        wait_for_completion=True,
                    )
                    for line in response.splitlines():
                        json_response = json.loads(line)["result"]
                        self.log.info(f"{src.name}: payment_index: {json_response['payment_index']} status: {json_response['status']}")
                except Exception as e:
                    self.log.info(f"Payment FAILED from {src.name}:\n{e}\n")
                sleep(5)

        payment_threads = []
        sources = [ln for ln in self.lns.values() if "spender" in ln.name]
        self.log.info(f"Sources: {[s.name for s in sources]}")

        for src in sources:
            target_name = src.name.replace("spender", "recipient")
            target_uri = self.lns[target_name].uri()
            pk, host = target_uri.split("@")
            self.log.info(f"Starting endless payment thread for {src.name}->{pk}")
            payment_threads.append(threading.Thread(target=make_payments, args=(self, src, pk)))

        for thread in payment_threads:
            thread.start()
        all(thread.join() is None for thread in payment_threads)

def main():
    LNActivity().main()

if __name__ == "__main__":
    main()
