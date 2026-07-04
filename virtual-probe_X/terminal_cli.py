import json
import shlex
from typing import Any

from node_graph import NodeGraph
from ping_manager import PingManager
from hashgate import XSpace


class TerminalCLI:
    def __init__(self, graph: NodeGraph, pings: PingManager, xspace: XSpace) -> None:
        self.graph = graph
        self.pings = pings
        self.xspace = xspace
        self.running = True

    def run(self) -> None:
        print("=" * 60)
        print("Light-ASI LLM Gateway — Interactive Terminal")
        print("=" * 60)
        print("Commands:")
        print("  add-node <label>          Add a concept node")
        print("  ping-check <host>         Check a single host")
        print("  ping-list <host1,host2>   Check multiple hosts")
        print("  ping-active              Show active ping results")
        print("  ping-inactive            Show inactive ping results")
        print("  index <text>             Index text into graph")
        print("  search <query>           Semantic search")
        print("  stats                    Graph statistics")
        print("  emerge                   Emergence status")
        print("  xspace                   Show XSpace nodes/mirrors")
        print("  xspace show gate <hash>  Find gate by hash (>=0.8)")
        print("  xspace show mirror <hash> Find mirror by hash (>=0.8)")
        print("  xspace retrieve mirror <content_hash> Retrieve mirror objects")
        print("  help                     Show this help")
        print("  exit                     Quit")
        print("=" * 60)
        while self.running:
            try:
                line = input("lasi> ").strip()
                if not line:
                    continue
                self._dispatch(line)
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                break

    def _dispatch(self, line: str) -> None:
        parts = shlex.split(line)
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "help":
            self._print_help()
        elif cmd == "exit":
            print("Goodbye.")
            self.running = False
        elif cmd == "add-node":
            self._cmd_add_node(args)
        elif cmd == "ping-check":
            self._cmd_ping_check(args)
        elif cmd == "ping-list":
            self._cmd_ping_list(args)
        elif cmd == "ping-active":
            self._cmd_ping_list_view("active")
        elif cmd == "ping-inactive":
            self._cmd_ping_list_view("inactive")
        elif cmd == "index":
            self._cmd_index(args)
        elif cmd == "search":
            self._cmd_search(args)
        elif cmd == "stats":
            print(json.dumps(self.graph.get_stats(), indent=2))
        elif cmd == "emerge":
            print(json.dumps(self.graph.emerge_status(), indent=2))
        elif cmd == "xspace":
            self._cmd_xspace(args)
        else:
            print(f"Unknown command: {cmd}. Type 'help' for available commands.")

    def _print_help(self) -> None:
        help_text = """
Commands:
  add-node <label>          Add a concept node to the graph
  ping-check <host>         Ping a single host (IP or hostname)
  ping-list <h1,h2,h3>      Ping multiple comma-separated hosts
  ping-active              List all currently active ping results
  ping-inactive            List all currently inactive ping results
  index <text>             Index text into the semantic graph
  search <query>           Perform semantic search on the graph
  stats                    Show graph statistics
  emerge                   Show ASI emergence checklist status
  xspace                   Show full XSpace graph
  xspace show gate <hash>  Query open gate by hash (>=0.8 similarity)
  xspace show mirror <hash> Query mirror by hash (>=0.8 similarity)
  xspace retrieve mirror <content_hash> Retrieve matching mirror objects (>=0.8)
  help                     Show this help message
  exit                     Quit the terminal
"""
        print(help_text)

    def _cmd_add_node(self, args: list[str]) -> None:
        if not args:
            print("Usage: add-node <label>")
            return
        label = " ".join(args)
        node = self.graph.add_node(label=label)
        print(f"Added node: {node.id} -> {node.label}")

    def _cmd_ping_check(self, args: list[str]) -> None:
        if not args:
            print("Usage: ping-check <host>")
            return
        host = args[0]
        result = self.pings.check_host(host)
        self.pings.results[result.host] = result
        self.pings.get_lists()
        self.pings.register_to_graph()
        state = "ACTIVE" if result.is_active else "INACTIVE"
        latency = f"{result.latency_ms}ms" if result.latency_ms else "N/A"
        print(f"[{state}] {result.host} ({result.ip}) latency={latency}")

    def _cmd_ping_list(self, args: list[str]) -> None:
        if not args:
            print("Usage: ping-list <host1,host2,host3>")
            return
        raw = " ".join(args)
        hosts = [h.strip() for h in raw.split(",") if h.strip()]
        if not hosts:
            print("No hosts provided.")
            return
        result = self.pings.check_list(hosts)
        self.pings.register_to_graph()
        print(f"Checked {len(hosts)} hosts: {len(result['active'])} active, {len(result['inactive'])} inactive")
        print(json.dumps(result, indent=2))

    def _cmd_ping_list_view(self, which: str) -> None:
        data = self.pings.get_lists()
        if which == "active":
            items = data["active"]
        else:
            items = data["inactive"]
        if not items:
            print(f"No {which} results.")
            return
        print(f"{which.capitalize()} ping results ({len(items)}):")
        for item in items:
            state = "ACTIVE" if item["is_active"] else "INACTIVE"
            latency = f"{item['latency_ms']}ms" if item["latency_ms"] else "N/A"
            print(f"  [{state}] {item['host']} ({item['ip']}) latency={latency}")

    def _cmd_index(self, args: list[str]) -> None:
        if not args:
            print("Usage: index <text>")
            return
        text = " ".join(args)
        node = self.graph.index_text(text)
        print(f"Indexed: {node.id} -> {node.label}")

    def _cmd_search(self, args: list[str]) -> None:
        if not args:
            print("Usage: search <query>")
            return
        query = " ".join(args)
        results = self.graph.search(query)
        if not results:
            print("No results.")
        else:
            print(f"Results for '{query}':")
            for r in results:
                print(f"  [{r['score']}] {r['id']} -> {r['label']}")

    def _cmd_xspace(self, args: list[str]) -> None:
        if not args:
            print(json.dumps(self.xspace.get_x_space(), indent=2))
            return
        sub = args[0].lower()
        rest = args[1:]
        if sub == "show" and len(rest) >= 2:
            target = rest[0].lower()
            value = rest[1]
            if target == "gate":
                results = self.xspace.query_gates(gate_hash=value, threshold=0.8)
                print(json.dumps({"gates": results}, indent=2))
            elif target == "mirror":
                results = self.xspace.query_mirrors(mirror_hash=value, threshold=0.8)
                print(json.dumps({"mirrors": results}, indent=2))
            else:
                print("Usage: xspace show gate|mirror <hash>")
        elif sub == "retrieve" and len(rest) >= 2 and rest[0].lower() == "mirror":
            content_hash = rest[1]
            mirrors = self.xspace.retrieve_mirror(content_hash, threshold=0.8)
            print(json.dumps({"query": content_hash, "threshold": 0.8, "mirrors": mirrors}, indent=2))
        elif sub == "find" and len(rest) >= 1:
            host = rest[0]
            gates = self.xspace.query_gates(host=host)
            mirrors = []
            for gate in gates:
                mirrors.extend(self.xspace.query_mirrors(source_gate_id=gate["id"]))
            print(json.dumps({"gates": gates, "mirrors": mirrors}, indent=2))
        else:
            print("Usage: xspace | xspace show gate|mirror <hash> | xspace retrieve mirror <content_hash> | xspace find <host>")
