#!/usr/bin/env python3

import threading
from commander import Commander
from time import sleep

# After 500 regtest blocks, miner will have about 13000 BTC
# Opening as much as 500 channels, 10 BTC each, leaves 8000
# Providing for as many as 40 armada nodes, is 200 each
# Leave a huge margin
FUNDS_PER_TANK = 10
FUNDING_TXS_COUNT = 10

class ArmArmada(Commander):
    def set_test_params(self):
        # This is just a minimum
        self.num_nodes = 0
        self.miners = []

    def add_options(self, parser):
        parser.description = "Send initial funds to all armada LN nodes"
        parser.usage = "warnet run /path/to/arm_armada.py"

    def run_test(self):
        self.log.info("Gathering armada LN nodes across all namespaces")
        tanks = []
        for ln in self.ln_nodes:
            if "armada" in ln.name:
                tanks.append(ln)
        self.log.info(f"Armada tanks:\n{[f'{ln.name}.{ln.namespace}' for ln in tanks]}")
        self.log.info("Getting Armada LN wallet addresses...")
        outputs = {}

        def get_ln_addr(self, ln):
            while True:
                try:
                    address = ln.newaddress()
                    self.log.info(f"Got wallet address {address} from {ln.name}.{ln.namespace}")
                    outputs[address] = FUNDS_PER_TANK / FUNDING_TXS_COUNT
                    break
                except Exception as e:
                    self.log.info(
                        f"Couldn't get wallet address from {ln.name} because {e}, retrying in 5 seconds..."
                    )
                    sleep(5)

        addr_threads = [
            threading.Thread(target=get_ln_addr, args=(self, ln)) for ln in tanks
        ]
        for thread in addr_threads:
            thread.start()

        all(thread.join() is None for thread in addr_threads)
        self.log.info(f"Got {len(outputs)} addresses from {len(self.lns)} LN nodes")

        self.log.info("Funding Armada LN wallets...")

        for i in range(FUNDING_TXS_COUNT):
            self.log.info(f"Sending funding tx {i} of {FUNDING_TXS_COUNT}")
            res = self.tanks["miner"].sendmany(amounts=outputs, fee_rate=1)
            self.log.info(res)

        self.generatetoaddress(self.tanks["miner"], 1, self.tanks["miner"].getnewaddress())


def main():
    ArmArmada("").main()

if __name__ == "__main__":
    main()
