"""
main.py — Light-ASI LLM Gateway
Dual-mode entry point:
  python3 main.py              → interactive terminal (Phase 0-2)
  python3 main.py --serve      → HTTP API server on :8000 (Phase 3)
  python3 main.py --serve 9000 → HTTP API server on :9000
  python3 main.py --nodes 1000 → bootstrap with 1000 nodes
"""

import argparse
import logging
import sys

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

from engine.core.graph import NodeGraph
from engine.auth.auth import AuthManager
from engine.world.ingester import WorldIngester
from engine.interface.terminal import Terminal
from engine.api.server import APIServer


def main() -> None:
    parser = argparse.ArgumentParser(description="Light-ASI LLM Gateway")
    parser.add_argument("--serve", nargs="?", const=8000, type=int, default=None,
                        help="Start HTTP API server (default port 8000)")
    parser.add_argument("--nodes", type=int, default=10,
                        help="Number of nodes to bootstrap (default 10)")
    parser.add_argument("--ingest-interval", type=int, default=120,
                        help="World-net ingestion interval in seconds (default 120)")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable DEBUG logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # ── Build the engine ──────────────────────────────────────────────────
    graph = NodeGraph()
    auth  = AuthManager()

    # Create default admin
    admin = auth.create_user("admin", "admin")
    print(f"\n  [*] Admin token (save this): {admin.token}\n")

    # WorldIngester
    ingester = WorldIngester(graph.semantic_map, graph, interval=args.ingest_interval)

    # ── Serve mode (Phase 3 HTTP API) ─────────────────────────────────────
    if args.serve is not None:
        port = args.serve
        print(f"  [*] Bootstrapping {args.nodes:,} nodes…")
        graph.bootstrap(args.nodes)
        print(f"  [✓] {args.nodes:,} nodes online.")

        # Start background ingester
        ingester.start()
        print(f"  [✓] WorldIngester started (interval={args.ingest_interval}s)")

        server = APIServer(graph=graph, auth=auth, ingester=ingester,
                           host="0.0.0.0", port=port)
        print(f"\n  ╔══════════════════════════════════════════════════╗")
        print(f"  ║  Light-ASI API Server                            ║")
        print(f"  ║  http://localhost:{port:<5}                        ║")
        print(f"  ║  Nodes: {args.nodes:<8}  Ingester: ACTIVE          ║")
        print(f"  ║                                                  ║")
        print(f"  ║  POST /auth/token   — get a Bearer token         ║")
        print(f"  ║  POST /query        — query the graph            ║")
        print(f"  ║  POST /index        — index text                 ║")
        print(f"  ║  POST /search       — search semantic map        ║")
        print(f"  ║  POST /ingest       — trigger ingestion cycle    ║")
        print(f"  ║  GET  /stats        — graph statistics           ║")
        print(f"  ║  GET  /emerge       — ASI emergence checklist    ║")
        print(f"  ║  GET  /health       — liveness check             ║")
        print(f"  ╚══════════════════════════════════════════════════╝\n")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n  [*] Shutting down. One love 🤧")
            ingester.stop()
            server.stop()

    # ── Terminal mode (Phase 0-2) ─────────────────────────────────────────
    else:
        terminal = Terminal(graph=graph, auth=auth, n_nodes=args.nodes)
        terminal.run()


if __name__ == "__main__":
    main()
