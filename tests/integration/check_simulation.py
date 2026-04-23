#!/usr/bin/env python3
"""
Monitors openv-server.log for evidence that a non-root mote synchronized and
sent an RPL DAO to the DAGroot.  A DAO can only be sent after the mote has
joined the network, so a single "received DAO" line covers both checks.

Exit 0 on success, 1 on timeout.
"""

import os
import sys
import time

TIMEOUT = 120
POLL_INTERVAL = 2
DAO_MARKER = 'received RPL DAO'


def main(log_file: str) -> None:
    # Record the current file size so we ignore any content from a previous run.
    start_pos = os.path.getsize(log_file) if os.path.exists(log_file) else 0

    print(f"Monitoring '{log_file}' for RPL DAO (timeout: {TIMEOUT}s) ...")
    deadline = time.time() + TIMEOUT

    while time.time() < deadline:
        try:
            with open(log_file) as f:
                f.seek(start_pos)
                if DAO_MARKER in f.read():
                    print("SUCCESS: RPL DAO received — mote synchronized and joined the DAG")
                    sys.exit(0)
        except FileNotFoundError:
            pass
        time.sleep(POLL_INTERVAL)

    print(f"TIMEOUT ({TIMEOUT}s): no RPL DAO received")
    sys.exit(1)


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'openv-server.log'
    main(path)
