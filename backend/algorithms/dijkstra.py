"""
Dijkstra's Algorithm implementation for single-pair and all-pairs shortest paths.
Tracks nodes explored and execution metrics for academic and visual comparison.
"""

import heapq
import time
from typing import Dict, List, Optional, Tuple, Any
from graph import Graph


class Dijkstra:
    """Computes shortest path between nodes using a Min-Heap priority queue."""

    @staticmethod
    def find_shortest_path(
        graph: Graph,
        start_id: str,
        goal_id: str,
        cost_metric: str = "time"  # 'time' or 'distance'
    ) -> Dict[str, Any]:
        """
        Find shortest path from start_id to goal_id using Dijkstra's algorithm.
        Returns path, total cost, distance, time, nodes explored count, and execution time.
        """
        t_start = time.perf_counter()

        if start_id not in graph.nodes:
            raise ValueError(f"Start node {start_id} not found in graph")
        if goal_id not in graph.nodes:
            raise ValueError(f"Goal node {goal_id} not found in graph")

        if start_id == goal_id:
            return {
                "algorithm": "Dijkstra",
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

        # Priority queue stores: (current_cost, counter, node_id)
        counter = 0
        pq: List[Tuple[float, int, str]] = [(0.0, counter, start_id)]
        
        # Best known costs to reach each node
        best_cost: Dict[str, float] = {start_id: 0.0}
        parent: Dict[str, Optional[str]] = {start_id: None}
        visited = set()
        explored_order: List[str] = []

        while pq:
            curr_cost, _, curr_id = heapq.heappop(pq)

            if curr_id in visited:
                continue
            visited.add(curr_id)
            explored_order.append(curr_id)

            if curr_id == goal_id:
                break

            for neighbor_id, edge in graph.get_neighbors(curr_id):
                if neighbor_id in visited:
                    continue

                edge_cost = edge.travel_time_mins if cost_metric == "time" else edge.distance_km
                new_cost = curr_cost + edge_cost

                if neighbor_id not in best_cost or new_cost < best_cost[neighbor_id]:
                    best_cost[neighbor_id] = new_cost
                    parent[neighbor_id] = curr_id
                    counter += 1
                    heapq.heappush(pq, (new_cost, counter, neighbor_id))

        exec_time = round((time.perf_counter() - t_start) * 1000, 3)

        if goal_id not in parent:
            return {
                "algorithm": "Dijkstra",
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

        # Reconstruct path from goal to start
        path = []
        curr = goal_id
        while curr is not None:
            path.append(curr)
            curr = parent[curr]
        path.reverse()

        # Compute accurate distance and travel time along path
        total_dist = 0.0
        total_time = 0.0
        for i in range(len(path) - 1):
            edge = graph.get_edge(path[i], path[i + 1])
            if edge:
                total_dist += edge.distance_km
                total_time += edge.travel_time_mins

        return {
            "algorithm": "Dijkstra",
            "start": start_id,
            "goal": goal_id,
            "cost_metric": cost_metric,
            "found": True,
            "path": path,
            "total_cost": round(best_cost[goal_id], 3),
            "distance_km": round(total_dist, 2),
            "time_mins": round(total_time, 2),
            "nodes_explored": len(visited),
            "explored_order": explored_order,
            "execution_time_ms": exec_time
        }
