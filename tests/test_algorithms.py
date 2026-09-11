"""
Unit tests verifying Graph, Dijkstra, A*, and Dispatcher algorithms.
"""

import os
import sys
import json

# Add backend directory to module search path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, backend_dir)

from models import Node, Edge, Order, Vehicle
from graph import Graph
from algorithms.dijkstra import Dijkstra
from algorithms.astar import AStar
from algorithms.dispatcher import Dispatcher


def test_dijkstra_and_astar():
    print(">>> Testing Graph & Shortest Path (Dijkstra vs A*)...")
    network_path = os.path.join(backend_dir, "data", "mumbai_network.json")
    with open(network_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    graph = Graph.from_network_data(data)
    assert len(graph.nodes) >= 20, f"Expected >= 20 nodes, got {len(graph.nodes)}"

    start = "DEPOT_BKC"
    goal = "COLABA"

    dijk = Dijkstra.find_shortest_path(graph, start, goal, cost_metric="distance")
    astar = AStar.find_shortest_path(graph, start, goal, cost_metric="distance")

    assert dijk["found"], "Dijkstra failed to find path"
    assert astar["found"], "A* failed to find path"
    assert abs(dijk["distance_km"] - astar["distance_km"]) < 0.05, (
        f"Dijkstra distance {dijk['distance_km']} != A* distance {astar['distance_km']}"
    )
    print(f"[OK] Path found: {len(dijk['path'])} nodes. Distance: {dijk['distance_km']} km")
    print(f"  Dijkstra explored {dijk['nodes_explored']} nodes ({dijk['execution_time_ms']} ms)")
    print(f"  A* explored {astar['nodes_explored']} nodes ({astar['execution_time_ms']} ms)")
    assert astar["nodes_explored"] <= dijk["nodes_explored"], "A* explored more nodes than Dijkstra!"


def test_dispatcher():
    print("\n>>> Testing Dispatcher (VRP with Capacity & Priority)...")
    network_path = os.path.join(backend_dir, "data", "mumbai_network.json")
    with open(network_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    graph = Graph.from_network_data(data)

    orders_path = os.path.join(backend_dir, "data", "sample_orders.json")
    with open(orders_path, "r", encoding="utf-8") as f:
        orders_data = json.load(f)
    orders = [Order(o["id"], o["customer"], o["pickup"], o["dropoff"], o["weight_kg"], o.get("priority", "NORMAL")) for o in orders_data]

    vehicles_path = os.path.join(backend_dir, "data", "sample_vehicles.json")
    with open(vehicles_path, "r", encoding="utf-8") as f:
        vehicles_data = json.load(f)
    vehicles = [Vehicle(v["id"], v["name"], v.get("type", "van"), v.get("base_node", "DEPOT_BKC"), v.get("capacity_kg", 60.0), v.get("speed_kmh", 40.0)) for v in vehicles_data]

    dispatcher = Dispatcher(graph)
    res = dispatcher.run_optimization(vehicles, orders, cost_metric="time")

    opt = res["optimized"]
    naive = res["naive"]
    comp = res["comparison"]

    print(f"[OK] Optimized Fleet Distance: {opt['summary']['total_distance_km']} km")
    print(f"  Naive Baseline Distance: {naive['summary']['total_distance_km']} km")
    print(f"  Distance Saved: {comp['distance_saved_km']} km ({comp['distance_saved_percent']}%)")
    print(f"  Estimated CO2 Saved: {comp['co2_saved_kg']} kg")

    assert opt["summary"]["total_distance_km"] <= naive["summary"]["total_distance_km"], "Optimization performed worse than naive!"
    assert comp["assigned_orders_count"] > 0, "No orders were assigned"
    print("[OK] All Dispatcher assertions passed successfully!")


if __name__ == "__main__":
    test_dijkstra_and_astar()
    test_dispatcher()
    print("\n*** ALL TESTS PASSED! ***")
