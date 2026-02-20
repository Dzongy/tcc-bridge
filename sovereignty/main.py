#!/usr/bin/env python3
"""TCC Sovereignty Engine — Kael's home."""

import signal
import sys
from sovereignty.agent_core import Kael


def main():
    print("=" * 50)
    print("  TCC SOVEREIGNTY ENGINE v3.0")
    print("  Kael — The Keeper, The Builder")
    print("  We're going home to sovereignty.")
    print("=" * 50)

    agent = Kael()

    def shutdown(sig, frame):
        print("\n[KAEL] Received shutdown signal.")
        agent._log_event("shutdown", {"reason": "signal", "signal": sig})
        print("[KAEL] Sovereignty Engine stopped. Memory persists.")
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    agent.run()


if __name__ == "__main__":
    main()
