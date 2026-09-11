"""
A* Search Algorithm with Admissible Haversine Heuristic.
Demonstrates guided/informed graph exploration vs uninformed Dijkstra.
"""

import heapq
import time
from typing import Dict, List, Optional, Tuple, Any
from graph import Graph


class AStar:
    """Computes shortest path between nodes using the A* algorithm."""

    # Maximum speed limit across Mumbai arterial expressways (e.g. Sea Link / Freeway)
    MAX_NETWORK_SPEED_KMH = 75.0

    @classmethod
    def heuristic(cls, graph: Graph, current_id: str, goal_id: str, cost_metric: str) -> float:
        """
        Admissible heuristic function h(n).
        For distance: Straight-line Haversine distance (great-circle).
        For time: Straight-line Haversine distance traversed at MAX_NETWORK_SPEED_KMH.
        Since straight-line distance is the shortest possible spatial distance and
        max speed is the fastest possible velocity, this never overestimates the actual cost.
        """
        dist_km = graph.haversine_distance(current_id, goal_id)
        if cost_metric == "distance":
            return dist_km
        else:
            return (dist_km / cls.MAX_NETWORK_SPEED_KMH) * 60.0

    @classmethod
    def find_shortest_path(
        cls,
        graph: Graph,
        start_id: str,
        goal_id: str,
        cost_metric: str = "time"  # 'time' or 'distance'
    ) -> Dict[str, Any]:
        """
        Find shortest path from start_id to goal_id using A* search.
        Returns path, total cost, distance, time, explored nodes count, and execution time.
        """
        t_start = time.perf_counter()

        if start_id not in graph.nodes:
            raise ValueError(f"Start node {start_id} not found in graph")
        if goal_id not in graph.nodes:
            raise ValueError(f"Goal node {goal_id} not found in graph")

        if start_id == goal_id:
            return {
                "algorithm": "A*",
                "start": start_id,
                "goal": goal_id,
                "cost_metric": cost_metric,
                "found": True,
                "path": [start_id],
                "total_cost": 0.0,
                "distance_km": 0.0,
                "time_mins": 0.0,
                "nodes_explored": 1,
                "explored_order": [start_id],
                "execution_time_ms": round((time.perf_counter() - t_start) * 1000, 3)
            }

        counter = 0
        h_start = cls.heuristic(graph, start_id, goal_id, cost_metric)
        # Priority queue stores: (f_score, counter, current_node)
        open_set: List[Tuple[float, int, str]] = [(h_start, counter, start_id)]

        g_score: Dict[str, float] = {start_id: 0.0}
        parent: Dict[str, Optional[str]] = {start_id: None}
        visited = set()
        explored_order: List[str] = []

        while open_set:
            f_curr, _, curr_id = heapq.heappop(open_set)

            if curr_id in visited:
                continue
            visited.add(curr_id)
            explored_order.append(curr_id)

            if curr_id == goal_id:
                break

            curr_g = g_score[curr_id]

            for neighbor_id, edge in graph.get_neighbors(curr_id):
                if neighbor_id in visited:
                    continue

                edge_cost = edge.travel_time_mins if cost_metric == "time" else edge.distance_km
                tentative_g = curr_g + edge_cost

                if neighbor_id not in g_score or tentative_g < g_score[neighbor_id]:
                    g_score[neighbor_id] = tentative_g
                    parent[neighbor_id] = curr_id
                    h = cls.heuristic(graph, neighbor_id, goal_id, cost_metric)
                    f_score = tentative_g + h
                    counter += 1
                    heapq.heappush(open_set, (f_score, counter, neighbor_id))

        exec_time = round((time.perf_counter() - t_start) * 1000, 3)

        if goal_id not in parent:
            return {
                "algorithm": "A*",
                "start": start_id,
                "goal": goal_id,
                "cost_metric": cost_metric,
                "found": False,
                "path": [],
                "total_cost": float("inf"),
                "distance_km": 0.0,
                "time_mins": 0.0,
                "nodes_explored": len(visited),
                "explored_order": explored_order,
                "execution_time_ms": exec_time
            }

        # Reconstruct path
        path = []
        curr = goal_id
        while curr is not None:
            path.append(curr)
            curr = parent[curr]
        path.reverse()

        total_dist = 0.0
        total_time = 0.0
        for i in range(len(path) - 1):
            edge = graph.get_edge(path[i], path[i + 1])
            if edge:
                total_dist += edge.distance_km
                total_time += edge.travel_time_mins

        return {
            "algorithm": "A*",
            "start": start_id,
            "goal": goal_id,
            "cost_metric": cost_metric,
            "found": True,
            "path": path,
            "total_cost": round(g_score[goal_id], 3),
            "distance_km": round(total_dist, 2),
            "time_mins": round(total_time, 2),
            "nodes_explored": len(visited),
            "explored_order": explored_order,
            "execution_time_ms": exec_time
        }
