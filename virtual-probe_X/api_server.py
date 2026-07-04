import os
import json
import secrets
import time
from dataclasses import asdict
from typing import Any

from node_graph import NodeGraph
from ping_manager import PingManager
from hashgate import XSpace


class AuthManager:
    def __init__(self) -> None:
        self.tokens: dict[str, dict[str, Any]] = {}
        self.admin_token = secrets.token_urlsafe(32)

    def login(self, password: str | None = None) -> str:
        token = secrets.token_urlsafe(32)
        self.tokens[token] = {
            "created_at": time.time(),
            "role": "admin" if (password or os.environ.get("ADMIN_PASSWORD")) == "admin" else "user",
        }
        return token

    def admin_login(self) -> str:
        return self.admin_token

    def validate(self, token: str | None) -> dict[str, Any]:
        if not token:
            return {"valid": False, "role": None}
        if token == self.admin_token:
            return {"valid": True, "role": "admin"}
        if token in self.tokens:
            return {"valid": True, "role": self.tokens[token]["role"]}
        return {"valid": False, "role": None}


class APIServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        self.host = host
        self.port = port
        self.graph = NodeGraph()
        self.pings = PingManager(self.graph)
        self.xspace = XSpace()
        self.auth = AuthManager()
        self.graph.bootstrap()
        self.start_time = time.time()

    def handle_request(self, method: str, path: str, headers: dict[str, str], body: bytes) -> tuple[int, str, str]:
        auth_header = headers.get("authorization", "")
        token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else None

        if path == "/auth/token" and method == "POST":
            token_resp = self.auth.login()
            body_data = json.loads(body.decode()) if body else {}
            pw = body_data.get("password")
            if pw == "admin":
                token_resp = self.auth.admin_login()
            return 200, "application/json", json.dumps({"token": token_resp, "role": "admin" if pw == "admin" else "user"})

        if path == "/health" and method == "GET":
            return 200, "application/json", json.dumps({"status": "ok", "uptime": round(time.time() - self.start_time, 2)})

        if path == "/stats" and method == "GET":
            return 200, "application/json", json.dumps(self.graph.get_stats())

        if path == "/emerge" and method == "GET":
            return 200, "application/json", json.dumps(self.graph.emerge_status())

        if method == "POST" and path == "/query":
            auth = self.auth.validate(token)
            if not auth["valid"]:
                return 401, "application/json", json.dumps({"error": "Unauthorized"})
            body_data = json.loads(body.decode()) if body else {}
            query = body_data.get("query", "")
            top_k = int(body_data.get("top_k", 5))
            results = self.graph.search(query, top_k=top_k)
            return 200, "application/json", json.dumps({"query": query, "results": results})

        if method == "POST" and path == "/index":
            auth = self.auth.validate(token)
            if not auth["valid"]:
                return 401, "application/json", json.dumps({"error": "Unauthorized"})
            body_data = json.loads(body.decode()) if body else {}
            text = body_data.get("text", "")
            if not text:
                return 400, "application/json", json.dumps({"error": "text is required"})
            node = self.graph.index_text(text)
            return 200, "application/json", json.dumps({"id": node.id, "label": node.label})

        if method == "POST" and path == "/search":
            auth = self.auth.validate(token)
            if not auth["valid"]:
                return 401, "application/json", json.dumps({"error": "Unauthorized"})
            body_data = json.loads(body.decode()) if body else {}
            query = body_data.get("query", "")
            top_k = int(body_data.get("top_k", 5))
            results = self.graph.search(query, top_k=top_k)
            return 200, "application/json", json.dumps({"query": query, "results": results})

        if method == "POST" and path == "/ingest":
            auth = self.auth.validate(token)
            if not auth["valid"]:
                return 401, "application/json", json.dumps({"error": "Unauthorized"})
            body_data = json.loads(body.decode()) if body else {}
            targets = body_data.get("targets", [])
            if not targets:
                return 400, "application/json", json.dumps({"error": "targets list is required"})
            result = self.pings.check_list(targets)
            self.pings.register_to_graph()
            return 200, "application/json", json.dumps({"ingested": len(targets), "active": len(result["active"]), "inactive": len(result["inactive"])})

        if path == "/ping/active" and method == "GET":
            return 200, "application/json", json.dumps({"active": [asdict(r) for r in self.pings.active_list]})

        if path == "/ping/inactive" and method == "GET":
            return 200, "application/json", json.dumps({"inactive": [asdict(r) for r in self.pings.inactive_list]})

        if path == "/xspace" and method == "GET":
            return 200, "application/json", json.dumps(self.xspace.get_x_space())

        if method == "POST" and path == "/xspace/gate":
            body_data = json.loads(body.decode()) if body else {}
            host = body_data.get("host", "")
            port = int(body_data.get("port", 0))
            protocol = body_data.get("protocol", "tcp")
            gate = self.xspace.add_gate(host, port, protocol)
            return 200, "application/json", json.dumps({"gate": asdict(gate)})

        if method == "POST" and path == "/xspace/mirror":
            body_data = json.loads(body.decode()) if body else {}
            host = body_data.get("host", "")
            port = int(body_data.get("port", 0))
            source_gate_id = body_data.get("source_gate_id", "")
            content_hash = body_data.get("content_hash", "")
            mirror = self.xspace.add_mirror(host, port, source_gate_id, content_hash)
            return 200, "application/json", json.dumps({"mirror": asdict(mirror)})

        if method == "POST" and path == "/xspace/query":
            body_data = json.loads(body.decode()) if body else {}
            query = body_data.get("query", "")
            results = self.xspace.git_like_query(query)
            return 200, "application/json", json.dumps(results)

        if method == "POST" and path == "/xspace/retrieve":
            auth = self.auth.validate(token)
            if not auth["valid"]:
                return 401, "application/json", json.dumps({"error": "Unauthorized"})
            body_data = json.loads(body.decode()) if body else {}
            content_hash = body_data.get("content_hash", "")
            threshold = float(body_data.get("threshold", 0.8))
            if not content_hash:
                return 400, "application/json", json.dumps({"error": "content_hash is required"})
            mirrors = self.xspace.retrieve_mirror(content_hash, threshold=threshold)
            return 200, "application/json", json.dumps({"query": content_hash, "threshold": threshold, "mirrors": mirrors})

        if method == "POST" and path == "/xspace/scan":
            auth = self.auth.validate(token)
            if not auth["valid"]:
                return 401, "application/json", json.dumps({"error": "Unauthorized"})
            body_data = json.loads(body.decode()) if body else {}
            target = body_data.get("target", "")
            if not target:
                return 400, "application/json", json.dumps({"error": "target host or CIDR is required"})
            from xspace_scanner import XSpaceScanner
            scanner = XSpaceScanner(self.xspace)
            if "/" in target:
                result = scanner.scan_network(target)
            else:
                items = scanner.scan_host(target)
                result = {"host": target, "discovered": len(items), "items": items}
            return 200, "application/json", json.dumps(result)

        return 404, "application/json", json.dumps({"error": "Not found"})

    def get_admin_token(self) -> str:
        return self.auth.admin_token

