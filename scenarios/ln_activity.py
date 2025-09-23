#!/usr/bin/env python3

import random
import threading
from commander import Commander
from time import sleep

class LNActivity(Commander):
    def set_test_params(self):
        # This is just a minimum
        self.num_nodes = 0
        self.miners = []

    def add_options(self, parser):
        parser.description = "Send LN payments from one half of the network to the other"
        parser.usage = "warnet run /path/to/ln_activity.py [options]"
        # parser.add_argument(
        #     "--allnodes",
        #     dest="allnodes",
        #     action="store_true",
        #     help="When true, generate blocks from all nodes instead of just nodes[0]",
        # )

    def run_test(self):
        sources = []
        targets = []
        coin = False
        for ln in self.lns.values():
            if coin:
                sources.append(ln)
            else:
                targets.append(ln)
            coin = not coin
        self.log.info(f"Sources:\n  {'\n  '.join([ln.name for ln in sources])}")
        self.log.info(f"Targets:\n  {'\n  '.join([ln.name for ln in targets])}")

        def make_payments(self, sources, targets):
            while True:
                sats = 15000
                tgt = random.choice(targets)
                src = random.choice(sources)
                res = None
                try:
                    inv = tgt.createinvoice(sats, "label")
                    res = src.payinvoice(inv)
                    if 'error' in res:
                        raise Exception(res['error']['message'])
                    if 'payment_error' in res['result'] and res['result']['payment_error'] != '':
                        raise Exception(res['result']['payment_error'])
                    self.log.info(f"{src.name}->{tgt.name} success! sats: {sats} hops: {len(res['result']['payment_route']['hops'])}")
                except Exception as e:
                    self.log.info(f"{src.name}->{tgt.name} error: {e}")
                sleep(1)

        payment_threads = [
            threading.Thread(target=make_payments, args=(self, sources, targets)) for _ in range(4)
        ]
        for thread in payment_threads:
            thread.start()
        all(thread.join() is None for thread in payment_threads)



def main():
    LNActivity().main()


if __name__ == "__main__":
    main()
