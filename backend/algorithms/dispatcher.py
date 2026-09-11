"""
Intelligent Dispatcher & Multi-Vehicle Routing Problem (VRP) Engine.
Combines priority scheduling, capacity constraints, Nearest-Neighbor tour construction,
and 2-Opt local search refinement. Also computes naive baseline for comparison.
"""

from typing import Dict, List, Tuple, Any, Optional
from models import Order, Vehicle
from graph import Graph
from algorithms.dijkstra import Dijkstra
from algorithms.astar import AStar


class Dispatcher:
    """Dispatches orders to a fleet of vehicles and computes optimized delivery routes."""

    def __init__(self, graph: Graph):
        self.graph = graph

    def run_optimization(
        self,
        vehicles: List[Vehicle],
        orders: List[Order],
        cost_metric: str = "time"
    ) -> Dict[str, Any]:
        """
        Execute full multi-vehicle route optimization:
        1. Priority & capacity based vehicle assignment
        2. Precedence-aware tour ordering (Nearest Neighbor + 2-Opt)
        3. Street-level path interpolation using A*
        4. Computation of naive baseline for direct performance comparison
        """
        # 1. Run Intelligent Optimization
        optimized_result = self._solve_vrp(vehicles, orders, cost_metric, apply_2opt=True)

        # 2. Run Naive Baseline (FIFO, no spatial clustering, direct sequential execution)
        naive_result = self._solve_naive(vehicles, orders, cost_metric)

        # 3. Calculate comparative delta
        opt_dist = optimized_result["summary"]["total_distance_km"]
        naive_dist = max(0.1, naive_result["summary"]["total_distance_km"])
        dist_saved_km = round(max(0.0, naive_dist - opt_dist), 2)
        dist_saved_pct = round((dist_saved_km / naive_dist) * 100.0, 1)

        opt_time = optimized_result["summary"]["total_time_mins"]
        naive_time = max(0.1, naive_result["summary"]["total_time_mins"])
        time_saved_mins = round(max(0.0, naive_time - opt_time), 1)
        time_saved_pct = round((time_saved_mins / naive_time) * 100.0, 1)

        # Fuel and CO2 calculations (Avg van ~0.11 L/km, 2.31 kg CO2/L)
        fuel_saved_liters = round(dist_saved_km * 0.11, 2)
        co2_saved_kg = round(fuel_saved_liters * 2.31, 2)

        return {
            "optimized": optimized_result,
            "naive": naive_result,
            "comparison": {
                "distance_saved_km": dist_saved_km,
                "distance_saved_percent": dist_saved_pct,
                "time_saved_mins": time_saved_mins,
                "time_saved_percent": time_saved_pct,
                "fuel_saved_liters": fuel_saved_liters,
                "co2_saved_kg": co2_saved_kg,
                "assigned_orders_count": optimized_result["summary"]["assigned_orders_count"],
                "unassigned_orders_count": len(optimized_result["unassigned_orders"])
            }
        }

    def _solve_vrp(
        self,
        vehicles: List[Vehicle],
        orders: List[Order],
        cost_metric: str,
        apply_2opt: bool = True
    ) -> Dict[str, Any]:
        """Vehicle routing solver with capacity, priority, and 2-Opt local search."""
        # Sort orders: URGENT (3) -> HIGH (2) -> NORMAL (1), then by deadline
        sorted_orders = sorted(
            orders,
            key=lambda o: (-o.priority_score, o.deadline_mins, o.weight_kg)
        )

        vehicle_assignments: Dict[str, List[Order]] = {v.id: [] for v in vehicles}
        vehicle_load: Dict[str, float] = {v.id: 0.0 for v in vehicles}
        unassigned_orders: List[Order] = []

        # Assign orders to best suited vehicle
        for order in sorted_orders:
            best_vehicle = None
            best_cost = float("inf")

            for v in vehicles:
                # Capacity constraint
                if vehicle_load[v.id] + order.weight_kg <= v.capacity_kg:
                    # Spatial proximity cost from vehicle base to pickup
                    prox = self.graph.haversine_distance(v.base_node, order.pickup)
                    if prox < best_cost:
                        best_cost = prox
                        best_vehicle = v

            if best_vehicle:
                vehicle_assignments[best_vehicle.id].append(order)
                vehicle_load[best_vehicle.id] += order.weight_kg
                order.assigned_vehicle_id = best_vehicle.id
            else:
                unassigned_orders.append(order)

        # For each vehicle, construct optimized tour
        routes_by_vehicle = []
        total_fleet_dist = 0.0
        total_fleet_time = 0.0

        for v in vehicles:
            assigned = vehicle_assignments[v.id]
            if not assigned:
                routes_by_vehicle.append({
                    "vehicle": v.to_dict(),
                    "total_distance_km": 0.0,
                    "total_time_mins": 0.0,
                    "payload_kg": 0.0,
                    "stops": [],
                    "path_nodes": [v.base_node],
                    "polyline": [[self.graph.nodes[v.base_node].lat, self.graph.nodes[v.base_node].lng]],
                    "orders_handled": []
                })
                continue

            # Build sequence of stops honoring precedence: Pickup must precede Dropoff
            stops = self._order_stops_nearest_neighbor(v.base_node, assigned)

            if apply_2opt and len(stops) > 3:
                stops = self._apply_2opt(v.base_node, stops, cost_metric)

            # Build detailed path between consecutive stops
            vehicle_path, dist, duration, polyline = self._build_detailed_route(
                v.base_node, stops, cost_metric
            )

            total_fleet_dist += dist
            total_fleet_time += duration

            routes_by_vehicle.append({
                "vehicle": v.to_dict(),
                "total_distance_km": round(dist, 2),
                "total_time_mins": round(duration, 1),
                "payload_kg": round(vehicle_load[v.id], 1),
                "stops": stops,
                "path_nodes": vehicle_path,
                "polyline": polyline,
                "orders_handled": [o.to_dict() for o in assigned]
            })

        return {
            "vehicles": routes_by_vehicle,
            "unassigned_orders": [o.to_dict() for o in unassigned_orders],
            "summary": {
                "total_distance_km": round(total_fleet_dist, 2),
                "total_time_mins": round(total_fleet_time, 1),
                "assigned_orders_count": len(orders) - len(unassigned_orders),
                "active_vehicles": sum(1 for r in routes_by_vehicle if r["total_distance_km"] > 0)
            }
        }

    def _solve_naive(
        self,
        vehicles: List[Vehicle],
        orders: List[Order],
        cost_metric: str
    ) -> Dict[str, Any]:
        """
        Naive baseline: First-In First-Out sequential execution.
        Assigns orders blindly to vehicles without clustering or 2-opt.
        """
        vehicle_assignments: Dict[str, List[Order]] = {v.id: [] for v in vehicles}
        vehicle_load: Dict[str, float] = {v.id: 0.0 for v in vehicles}

        # Naive: iterate in original order, assign to first vehicle with room
        for order in orders:
            for v in vehicles:
                if vehicle_load[v.id] + order.weight_kg <= v.capacity_kg:
                    vehicle_assignments[v.id].append(order)
                    vehicle_load[v.id] += order.weight_kg
                    break

        routes_by_vehicle = []
        total_dist = 0.0
        total_time = 0.0

        for v in vehicles:
            assigned = vehicle_assignments[v.id]
            if not assigned:
                continue

            # Naive stop sequence: for each order, go to pickup then dropoff in arrival order
            stops = []
            for o in assigned:
                stops.append({"node_id": o.pickup, "type": "pickup", "order_id": o.id})
                stops.append({"node_id": o.dropoff, "type": "dropoff", "order_id": o.id})

            vehicle_path, dist, duration, polyline = self._build_detailed_route(
                v.base_node, stops, cost_metric
            )

            total_dist += dist
            total_time += duration

            routes_by_vehicle.append({
                "vehicle_id": v.id,
                "total_distance_km": round(dist, 2),
                "total_time_mins": round(duration, 1),
                "stops_count": len(stops)
            })

        return {
            "routes": routes_by_vehicle,
            "summary": {
                "total_distance_km": round(total_dist, 2),
                "total_time_mins": round(total_time, 1)
            }
        }

    def _order_stops_nearest_neighbor(
        self,
        start_node_id: str,
        orders: List[Order]
    ) -> List[Dict[str, Any]]:
        """
        Greedy Nearest Neighbor with precedence enforcement:
        Dropoff for an order cannot be visited until its pickup is visited.
        """
        picked_up = set()
        delivered = set()
        stops = []
        current_node = start_node_id

        # Total stops to make = 2 * len(orders)
        remaining_count = len(orders) * 2

        while len(stops) < remaining_count:
            best_candidate = None
            best_dist = float("inf")

            for order in orders:
                # Can we pick it up?
                if order.id not in picked_up:
                    dist = self.graph.haversine_distance(current_node, order.pickup)
                    # Urgent orders get distance bonus to prioritize earlier visitation
                    priority_factor = 0.6 if order.priority == "URGENT" else (0.8 if order.priority == "HIGH" else 1.0)
                    adj_dist = dist * priority_factor

                    if adj_dist < best_dist:
                        best_dist = adj_dist
                        best_candidate = {
                            "node_id": order.pickup,
                            "type": "pickup",
                            "order_id": order.id,
                            "customer": order.customer,
                            "priority": order.priority,
                            "weight_kg": order.weight_kg
                        }

                # Can we drop it off? (Only if already picked up)
                elif order.id in picked_up and order.id not in delivered:
                    dist = self.graph.haversine_distance(current_node, order.dropoff)
                    if dist < best_dist:
                        best_dist = dist
                        best_candidate = {
                            "node_id": order.dropoff,
                            "type": "dropoff",
                            "order_id": order.id,
                            "customer": order.customer,
                            "priority": order.priority,
                            "weight_kg": order.weight_kg
                        }

            if not best_candidate:
                break

            stops.append(best_candidate)
            current_node = best_candidate["node_id"]

            if best_candidate["type"] == "pickup":
                picked_up.add(best_candidate["order_id"])
            else:
                delivered.add(best_candidate["order_id"])

        return stops

    def _is_precedence_valid(self, stops: List[Dict[str, Any]]) -> bool:
        """Verify that every pickup appears before its corresponding dropoff."""
        seen_pickups = set()
        for stop in stops:
            if stop["type"] == "pickup":
                seen_pickups.add(stop["order_id"])
            elif stop["type"] == "dropoff":
                if stop["order_id"] not in seen_pickups:
                    return False
        return True

    def _apply_2opt(
        self,
        base_node: str,
        stops: List[Dict[str, Any]],
        cost_metric: str,
        max_iterations: int = 40
    ) -> List[Dict[str, Any]]:
        """
        2-Opt heuristic optimization for stop sequences:
        Attempts pairwise edge reversals to untangle tour crossovers while ensuring
        pickup-before-dropoff precedence constraints remain satisfied.
        """
        best_stops = list(stops)
        n = len(best_stops)

        def tour_cost(seq):
            cost = 0.0
            prev = base_node
            for s in seq:
                cost += self.graph.haversine_distance(prev, s["node_id"])
                prev = s["node_id"]
            return cost

        best_cost = tour_cost(best_stops)
        improved = True
        iterations = 0

        while improved and iterations < max_iterations:
            improved = False
            iterations += 1

            for i in range(n - 1):
                for j in range(i + 1, n):
                    # Invert subsegment [i:j+1]
                    new_stops = best_stops[:i] + best_stops[i:j + 1][::-1] + best_stops[j + 1:]

                    # Check validity of precedence
                    if not self._is_precedence_valid(new_stops):
                        continue

                    new_cost = tour_cost(new_stops)
                    if new_cost < best_cost - 0.01:
                        best_stops = new_stops
                        best_cost = new_cost
                        improved = True
                        break
                if improved:
                    break

        return best_stops

    def _build_detailed_route(
        self,
        base_node: str,
        stops: List[Dict[str, Any]],
        cost_metric: str
    ) -> Tuple[List[str], float, float, List[List[float]]]:
        """
        Connects consecutive stops using A* shortest path search and builds
        the complete turn-by-turn node sequence and GPS coordinates for polyline rendering.
        """
        full_path: List[str] = [base_node]
        total_dist = 0.0
        total_time = 0.0
        current = base_node

        for stop in stops:
            target = stop["node_id"]
            if current != target:
                res = AStar.find_shortest_path(self.graph, current, target, cost_metric)
                if res["found"]:
                    # Append intermediate nodes (skipping duplicate current node)
                    segment_nodes = res["path"][1:]
                    full_path.extend(segment_nodes)
                    total_dist += res["distance_km"]
                    total_time += res["time_mins"]
                else:
                    # Fallback straight link if disconnected
                    full_path.append(target)
                    straight_dist = self.graph.haversine_distance(current, target)
                    total_dist += straight_dist
                    total_time += (straight_dist / 40.0) * 60.0
            current = target

        # Build GPS polyline coordinates for map drawing
        polyline = []
        for nid in full_path:
            node = self.graph.nodes.get(nid)
            if node:
                polyline.append([node.lat, node.lng])

        return full_path, total_dist, total_time, polyline
