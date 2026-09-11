"""
Graph data structure representing the street and junction network.
"""

import math
from typing import Dict, List, Tuple, Optional, Any
from models import Node, Edge


class Graph:
    """
    Adjacency-list based weighted graph representing a navigable street network.
    Supports node/edge lookups, neighbor iteration, and spatial Haversine distance heuristics.
    """

    EARTH_RADIUS_KM = 6371.0088

    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        # adjacency: node_id -> list of (neighbor_id, edge)
        self.adjacency: Dict[str, List[Tuple[str, Edge]]] = {}
        # direct lookup for (u, v) -> edge
        self.edge_map: Dict[Tuple[str, str], Edge] = {}

    def add_node(self, node: Node) -> None:
        """Register a node in the graph."""
        self.nodes[node.id] = node
        if node.id not in self.adjacency:
            self.adjacency[node.id] = []

    def add_edge(self, edge: Edge, bidirectional: bool = True) -> None:
        """Add a directed or bidirectional edge between two existing nodes."""
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise ValueError(f"Edge references unknown nodes: {edge.source} -> {edge.target}")

        self.adjacency[edge.source].append((edge.target, edge))
        self.edge_map[(edge.source, edge.target)] = edge

        if bidirectional and not edge.is_one_way:
            # reverse edge for bidirectional streets
            rev_edge = Edge(
                edge_id=f"{edge.id}_REV",
                source=edge.target,
                target=edge.source,
                distance_km=edge.distance_km,
                speed_limit_kmh=edge.speed_limit_kmh,
                traffic_factor=edge.traffic_factor,
                road_name=edge.road_name,
                is_one_way=False
            )
            self.adjacency[edge.target].append((edge.source, rev_edge))
            self.edge_map[(edge.target, edge.source)] = rev_edge

    def get_neighbors(self, node_id: str) -> List[Tuple[str, Edge]]:
        """Return list of (neighbor_node_id, edge) for a given node."""
        return self.adjacency.get(node_id, [])

    def get_edge(self, source_id: str, target_id: str) -> Optional[Edge]:
        """Retrieve edge connecting two adjacent nodes."""
        return self.edge_map.get((source_id, target_id))

    def haversine_distance(self, node_a_id: str, node_b_id: str) -> float:
        """
        Calculate straight-line great-circle distance between two nodes in kilometers.
        This provides an admissible (never overestimating) heuristic for A* pathfinding.
        """
        node_a = self.nodes.get(node_a_id)
        node_b = self.nodes.get(node_b_id)
        if not node_a or not node_b:
            return 0.0

        lat1_rad = math.radians(node_a.lat)
        lon1_rad = math.radians(node_a.lng)
        lat2_rad = math.radians(node_b.lat)
        lon2_rad = math.radians(node_b.lng)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = (
            math.sin(dlat / 2.0) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * (math.sin(dlon / 2.0) ** 2)
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return self.EARTH_RADIUS_KM * c

    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to a JSON-compatible dictionary."""
        edges_out = []
        seen = set()
        for (u, v), edge in self.edge_map.items():
            canonical = tuple(sorted([u, v]))
            if canonical in seen:
                continue
            seen.add(canonical)
            edges_out.append(edge.to_dict())

        return {
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": edges_out
        }

    @classmethod
    def from_network_data(cls, data: Dict[str, Any]) -> "Graph":
        """Factory method to construct a Graph instance from a JSON network definition."""
        graph = cls()
        for node_data in data.get("nodes", []):
            node = Node(
                node_id=node_data["id"],
                name=node_data["name"],
                lat=node_data["lat"],
                lng=node_data["lng"],
                node_type=node_data.get("type", "customer"),
                description=node_data.get("description", "")
            )
            graph.add_node(node)

        for edge_data in data.get("edges", []):
            edge = Edge(
                edge_id=edge_data["id"],
                source=edge_data["source"],
                target=edge_data["target"],
                distance_km=edge_data["distance_km"],
                speed_limit_kmh=edge_data.get("speed_limit_kmh", 40.0),
                traffic_factor=edge_data.get("traffic_factor", 1.0),
                road_name=edge_data.get("road_name", ""),
                is_one_way=edge_data.get("is_one_way", False)
            )
            graph.add_edge(edge, bidirectional=not edge.is_one_way)

        return graph
