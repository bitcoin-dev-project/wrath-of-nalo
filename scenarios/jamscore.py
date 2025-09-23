#!/usr/bin/env python3

import json
import time
import threading
from commander import Commander


class JamScore(Commander):
    def set_test_params(self):
        # This is just a minimum
        self.num_nodes = 0
        self.miners = []
        self.pods = []

    def add_options(self, parser):
        parser.description = "Generate channel jamming scoreboard"
        parser.usage = "warnet run /path/to/jamscore.py --admin --debug"


    def get_payments(self, ln):
        success = 0
        failed = 0
        elapsed = -1

        try:
            start = time.perf_counter()
            payments = json.loads(ln.get("/v1/payments?include_incomplete=true"))
            elapsed = time.perf_counter() - start

            self.log.info(f"Got payments from {ln.name} in {elapsed}")
            for payment in payments["payments"]:
                if payment["status"] == "SUCCEEDED":
                    success += 1
                else:
                    failed += 1

        except Exception as e:
            self.log.info(f"Failed to get payments from {ln.name}: {e}")

        self.pods.append({
            "node": ln.name,
            "succeeded": success,
            "failed": failed,
            "elapsed": elapsed
        })

    def run_test(self):
        threads = [
            threading.Thread(target=self.get_payments, args=(ln,)) for ln in self.lns.values() if "spender" in ln.name
        ]
        for thread in threads:
            thread.start()

        all(thread.join() is None for thread in threads)

        title = "Wrath of Nalo Channel Jamming scores"

        headers = [
            "Node Name",
            "Succeeded payments",
            "Failed payments",
            "lncli time (seconds)",
        ]

        self.pods.sort(key=lambda p: p["node"])
        rows = [
            (
                pod["node"],
                str(pod["succeeded"]),
                str(pod["failed"]),
                str(int(pod["elapsed"])),
            )
            for pod in self.pods
        ]

        # column widths = max(header, content)
        widths = [
            max(len(headers[i]), max(len(row[i]) for row in rows))
            for i in range(len(headers))
        ]

        def fmt_row(cols):
            return " | ".join(cols[i].ljust(widths[i]) for i in range(len(cols)))


        self.log.info(title)
        self.log.info("-" * len(fmt_row(headers)))
        self.log.info(fmt_row(headers))
        self.log.info("-" * len(fmt_row(headers)))

        for row in rows:
            self.log.info(fmt_row(row))


def main():
    JamScore("").main()

if __name__ == "__main__":
    main()
