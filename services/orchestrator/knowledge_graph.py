"""
Security Knowledge Graph — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

Entity-relationship graph, attack path analysis, dependency mapping.
"""

import hashlib, logging, threading, time
from collections import defaultdict, deque
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger("qwen.knowledge_graph")


# ============================================================================
#  KNOWLEDGE GRAPH
# ============================================================================

class NodeType(str, Enum):
    ASSET = "asset"
    IDENTITY = "identity"
    VULNERABILITY = "vulnerability"
    THREAT = "threat"
    CONTROL = "control"
    SERVICE = "service"
    DATA_STORE = "data_store"
    NETWORK = "network"
    CERTIFICATE = "certificate"
    SECRET = "secret"


class EdgeType(str, Enum):
    ACCESSES = "accesses"
    OWNS = "owns"
    DEPENDS_ON = "depends_on"
    EXPLOITS = "exploits"
    MITIGATES = "mitigates"
    CONNECTS_TO = "connects_to"
    STORES_DATA = "stores_data"
    AUTHENTICATES = "authenticates"
    EXPOSES = "exposes"
    CONTAINS = "contains"


class GraphNode:
    def __init__(self, node_id: str, node_type: NodeType, name: str,
                 properties: Dict = None, risk_score: float = 0):
        self.node_id = node_id
        self.node_type = node_type
        self.name = name
        self.properties = properties or {}
        self.risk_score = risk_score
        self.created_at = datetime.now(timezone.utc)

    def to_dict(self):
        return {"id": self.node_id, "type": self.node_type.value,
                "name": self.name, "risk": self.risk_score}


class GraphEdge:
    def __init__(self, source_id: str, target_id: str, edge_type: EdgeType,
                 weight: float = 1.0, properties: Dict = None):
        self.source_id = source_id
        self.target_id = target_id
        self.edge_type = edge_type
        self.weight = weight
        self.properties = properties or {}

    def to_dict(self):
        return {"source": self.source_id, "target": self.target_id,
                "type": self.edge_type.value, "weight": self.weight}


class SecurityKnowledgeGraph:
    """Entity-relationship graph for security intelligence."""

    def __init__(self):
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._adjacency: Dict[str, List[Tuple[str, GraphEdge]]] = defaultdict(list)
        self._lock = threading.Lock()
        self._seed()

    def _seed(self):
        # Core infrastructure nodes
        nodes = [
            ("api-gw", NodeType.SERVICE, "API Gateway", 15),
            ("auth-svc", NodeType.SERVICE, "Auth Service", 25),
            ("verify-eng", NodeType.SERVICE, "Verification Engine", 20),
            ("sec-hub", NodeType.SERVICE, "Security Hub", 10),
            ("pg-primary", NodeType.DATA_STORE, "PostgreSQL Primary", 30),
            ("redis-cache", NodeType.DATA_STORE, "Redis Cache", 15),
            ("obj-store", NodeType.DATA_STORE, "Object Storage", 20),
            ("vpn-gw", NodeType.NETWORK, "VPN Gateway", 20),
            ("lb-ext", NodeType.NETWORK, "External Load Balancer", 25),
            ("tls-cert", NodeType.CERTIFICATE, "TLS Wildcard Cert", 15),
            ("db-cred", NodeType.SECRET, "DB Credentials", 35),
            ("api-key", NodeType.SECRET, "API Master Key", 30),
            ("admin-user", NodeType.IDENTITY, "Admin User", 40),
            ("svc-account", NodeType.IDENTITY, "Service Account", 25),
            ("cve-runc", NodeType.VULNERABILITY, "CVE-2024-21626 runc escape", 85),
            ("cve-xz", NodeType.VULNERABILITY, "CVE-2024-3094 XZ backdoor", 95),
            ("apt-lazarus", NodeType.THREAT, "Lazarus Group APT", 90),
            ("fw-waf", NodeType.CONTROL, "WAF Firewall", 5),
            ("ctrl-mfa", NodeType.CONTROL, "MFA Policy", 5),
            ("ctrl-rbac", NodeType.CONTROL, "RBAC Engine", 5),
        ]
        for nid, ntype, name, risk in nodes:
            self._nodes[nid] = GraphNode(nid, ntype, name, risk_score=risk)

        # Edges
        edges = [
            ("admin-user", "api-gw", EdgeType.ACCESSES),
            ("admin-user", "pg-primary", EdgeType.ACCESSES),
            ("svc-account", "verify-eng", EdgeType.AUTHENTICATES),
            ("api-gw", "auth-svc", EdgeType.DEPENDS_ON),
            ("auth-svc", "pg-primary", EdgeType.DEPENDS_ON),
            ("auth-svc", "redis-cache", EdgeType.DEPENDS_ON),
            ("verify-eng", "pg-primary", EdgeType.STORES_DATA),
            ("verify-eng", "obj-store", EdgeType.STORES_DATA),
            ("lb-ext", "api-gw", EdgeType.CONNECTS_TO),
            ("api-gw", "tls-cert", EdgeType.AUTHENTICATES),
            ("auth-svc", "db-cred", EdgeType.ACCESSES),
            ("api-gw", "api-key", EdgeType.ACCESSES),
            ("cve-runc", "verify-eng", EdgeType.EXPLOITS),
            ("cve-xz", "api-gw", EdgeType.EXPLOITS),
            ("apt-lazarus", "cve-xz", EdgeType.EXPLOITS),
            ("fw-waf", "cve-xz", EdgeType.MITIGATES),
            ("ctrl-mfa", "admin-user", EdgeType.MITIGATES),
            ("ctrl-rbac", "svc-account", EdgeType.MITIGATES),
            ("sec-hub", "api-gw", EdgeType.CONTAINS),
            ("sec-hub", "auth-svc", EdgeType.CONTAINS),
        ]
        for src, tgt, etype in edges:
            edge = GraphEdge(src, tgt, etype)
            self._edges.append(edge)
            self._adjacency[src].append((tgt, edge))
            self._adjacency[tgt].append((src, edge))

    def add_node(self, node_id: str, node_type: NodeType, name: str,
                 risk_score: float = 0) -> Dict:
        self._nodes[node_id] = GraphNode(node_id, node_type, name, risk_score=risk_score)
        return {"added": True, "node": node_id}

    def add_edge(self, source: str, target: str, edge_type: EdgeType) -> Dict:
        if source not in self._nodes or target not in self._nodes:
            return {"error": "Node not found"}
        edge = GraphEdge(source, target, edge_type)
        self._edges.append(edge)
        self._adjacency[source].append((target, edge))
        self._adjacency[target].append((source, edge))
        return {"added": True, "edge": f"{source}→{target}"}

    def get_neighbors(self, node_id: str, edge_type: EdgeType = None) -> List[Dict]:
        neighbors = self._adjacency.get(node_id, [])
        if edge_type:
            neighbors = [(n, e) for n, e in neighbors if e.edge_type == edge_type]
        return [{"node": self._nodes[n].to_dict(), "edge": e.to_dict()}
                for n, e in neighbors if n in self._nodes]

    def blast_radius(self, node_id: str, max_hops: int = 3) -> Dict:
        """BFS to find all nodes within N hops — the blast radius."""
        visited: Set[str] = set()
        queue = deque([(node_id, 0)])
        layers: Dict[int, List[str]] = defaultdict(list)
        while queue:
            current, depth = queue.popleft()
            if current in visited or depth > max_hops:
                continue
            visited.add(current)
            layers[depth].append(current)
            for neighbor, _ in self._adjacency.get(current, []):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))
        total_risk = sum(self._nodes[n].risk_score for n in visited if n in self._nodes)
        return {
            "origin": node_id, "max_hops": max_hops,
            "affected_nodes": len(visited),
            "layers": {k: v for k, v in layers.items()},
            "total_risk_score": total_risk,
        }

    def query(self, node_type: NodeType = None, min_risk: float = 0) -> List[Dict]:
        results = []
        for node in self._nodes.values():
            if node_type and node.node_type != node_type:
                continue
            if node.risk_score >= min_risk:
                results.append(node.to_dict())
        return sorted(results, key=lambda x: x["risk"], reverse=True)

    def get_stats(self) -> Dict:
        return {"nodes": len(self._nodes), "edges": len(self._edges),
                "node_types": len(set(n.node_type for n in self._nodes.values()))}


# ============================================================================
#  ATTACK PATH ANALYZER
# ============================================================================

class AttackPath:
    def __init__(self, path_id, steps, total_risk, exploitability):
        self.path_id = path_id
        self.steps = steps
        self.total_risk = total_risk
        self.exploitability = exploitability
        self.discovered_at = datetime.now(timezone.utc)

    def to_dict(self):
        return {"id": self.path_id, "steps": self.steps,
                "hops": len(self.steps), "risk": self.total_risk,
                "exploitability": self.exploitability}


class AttackPathAnalyzer:
    """Graph traversal to discover multi-hop attack paths."""

    def __init__(self, graph: SecurityKnowledgeGraph):
        self._graph = graph
        self._paths: List[AttackPath] = []
        self._counter = 0

    def find_paths(self, source_id: str, target_id: str,
                   max_depth: int = 5) -> List[Dict]:
        """DFS to find all paths from source to target."""
        all_paths = []
        self._dfs(source_id, target_id, set(), [], max_depth, all_paths)
        results = []
        for path in all_paths:
            self._counter += 1
            risk = sum(self._graph._nodes[n].risk_score
                      for n in path if n in self._graph._nodes)
            exploitability = min(1.0, risk / (len(path) * 50))
            ap = AttackPath(f"AP-{self._counter:06d}", path, risk, round(exploitability, 3))
            self._paths.append(ap)
            results.append(ap.to_dict())
        return sorted(results, key=lambda x: x["risk"], reverse=True)

    def _dfs(self, current: str, target: str, visited: Set[str],
             path: List[str], max_depth: int, results: List):
        if len(path) > max_depth:
            return
        path.append(current)
        visited.add(current)
        if current == target and len(path) > 1:
            results.append(list(path))
        else:
            for neighbor, edge in self._graph._adjacency.get(current, []):
                if neighbor not in visited:
                    if edge.edge_type in (EdgeType.ACCESSES, EdgeType.DEPENDS_ON,
                                         EdgeType.CONNECTS_TO, EdgeType.EXPLOITS):
                        self._dfs(neighbor, target, visited, path, max_depth, results)
        path.pop()
        visited.discard(current)

    def find_crown_jewel_paths(self) -> List[Dict]:
        """Find all paths to high-value targets (risk > 50)."""
        crown_jewels = [n.node_id for n in self._graph._nodes.values()
                       if n.risk_score >= 50]
        entry_points = [n.node_id for n in self._graph._nodes.values()
                       if n.node_type in (NodeType.NETWORK, NodeType.IDENTITY)]
        all_paths = []
        for entry in entry_points:
            for jewel in crown_jewels:
                paths = self.find_paths(entry, jewel, max_depth=4)
                all_paths.extend(paths)
        return sorted(all_paths, key=lambda x: x["risk"], reverse=True)[:20]

    def get_stats(self) -> Dict:
        return {"paths_discovered": len(self._paths)}


# ============================================================================
#  DEPENDENCY GRAPH
# ============================================================================

class DependencyNode:
    def __init__(self, name, dep_type, version, criticality):
        self.name = name
        self.dep_type = dep_type  # service, library, infra
        self.version = version
        self.criticality = criticality  # 1-10
        self.dependents: List[str] = []
        self.dependencies: List[str] = []

    def to_dict(self):
        return {"name": self.name, "type": self.dep_type,
                "version": self.version, "criticality": self.criticality,
                "dependents": len(self.dependents),
                "dependencies": len(self.dependencies)}


class DependencyGraph:
    """Full service/library dependency mapping for impact analysis."""

    def __init__(self):
        self._nodes: Dict[str, DependencyNode] = {}
        self._seed()

    def _seed(self):
        deps = [
            ("python", "runtime", "3.11", 10),
            ("stdlib.hashlib", "library", "builtin", 9),
            ("stdlib.hmac", "library", "builtin", 9),
            ("stdlib.os", "library", "builtin", 10),
            ("stdlib.threading", "library", "builtin", 8),
            ("stdlib.json", "library", "builtin", 7),
            ("stdlib.logging", "library", "builtin", 6),
            ("stdlib.re", "library", "builtin", 7),
            ("security_hub", "service", "1.0", 10),
            ("event_bus", "service", "1.0", 9),
            ("data_lake", "service", "1.0", 8),
            ("secret_vault", "service", "1.0", 10),
            ("api_gateway", "service", "1.0", 9),
            ("orchestration_fabric", "service", "1.0", 10),
            ("postgresql", "infra", "15.4", 10),
            ("redis", "infra", "7.2", 7),
            ("linux_kernel", "infra", "6.1", 10),
        ]
        for name, dtype, version, crit in deps:
            self._nodes[name] = DependencyNode(name, dtype, version, crit)

        # Wire service dependencies
        service_deps = [
            ("security_hub", ["python", "stdlib.logging", "event_bus"]),
            ("event_bus", ["python", "stdlib.threading"]),
            ("data_lake", ["python", "stdlib.hashlib", "stdlib.threading"]),
            ("secret_vault", ["python", "stdlib.hmac", "stdlib.os"]),
            ("api_gateway", ["python", "stdlib.re", "stdlib.json"]),
            ("orchestration_fabric", ["python", "security_hub", "event_bus", "data_lake"]),
        ]
        for svc, svc_deps in service_deps:
            if svc in self._nodes:
                self._nodes[svc].dependencies = svc_deps
                for dep in svc_deps:
                    if dep in self._nodes:
                        self._nodes[dep].dependents.append(svc)

    def impact_analysis(self, component: str) -> Dict:
        """What breaks if this component goes down?"""
        node = self._nodes.get(component)
        if not node:
            return {"error": "Component not found"}
        affected = set()
        queue = deque([component])
        while queue:
            current = queue.popleft()
            if current in affected:
                continue
            affected.add(current)
            n = self._nodes.get(current)
            if n:
                for dep in n.dependents:
                    if dep not in affected:
                        queue.append(dep)
        affected.discard(component)
        return {"component": component, "affected": list(affected),
                "impact_count": len(affected),
                "max_criticality": max((self._nodes[a].criticality
                                       for a in affected if a in self._nodes), default=0)}

    def get_critical_path(self) -> List[Dict]:
        """Components with most dependents (highest blast radius)."""
        ranked = sorted(self._nodes.values(),
                       key=lambda n: len(n.dependents), reverse=True)
        return [n.to_dict() for n in ranked[:10]]

    def get_stats(self) -> Dict:
        return {"components": len(self._nodes),
                "edges": sum(len(n.dependencies) for n in self._nodes.values())}


# Singletons
knowledge_graph = SecurityKnowledgeGraph()
attack_path_analyzer = AttackPathAnalyzer(knowledge_graph)
dependency_graph = DependencyGraph()
