"""
Flask REST API for Intelligent Route and Delivery Optimization System.
Provides endpoints for graph network, order management, fleet control,
algorithm optimization (Dijkstra, A*, VRP), and performance comparisons.
"""

import os
import json
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from models import Node, Edge, Order, Vehicle
from graph import Graph
from algorithms.dijkstra import Dijkstra
from algorithms.astar import AStar
from algorithms.dispatcher import Dispatcher
from algorithms.metrics import MetricsCalculator

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

# Load network graph from JSON
network_file = os.path.join(DATA_DIR, "mumbai_network.json")
with open(network_file, "r", encoding="utf-8") as f:
    network_data = json.load(f)

graph = Graph.from_network_data(network_data)

# In-memory orders and vehicles state (initialized from json)
def load_initial_orders():
    orders_file = os.path.join(DATA_DIR, "sample_orders.json")
    with open(orders_file, "r", encoding="utf-8") as f:
        items = json.load(f)
    return [
        Order(
            order_id=item["id"],
            customer=item["customer"],
            pickup=item["pickup"],
            dropoff=item["dropoff"],
            weight_kg=item["weight_kg"],
            priority=item.get("priority", "NORMAL"),
            deadline_mins=item.get("deadline_mins", 120),
            description=item.get("description", "")
        )
        for item in items
    ]

def load_initial_vehicles():
    vehicles_file = os.path.join(DATA_DIR, "sample_vehicles.json")
    with open(vehicles_file, "r", encoding="utf-8") as f:
        items = json.load(f)
    return [
        Vehicle(
            vehicle_id=item["id"],
            name=item["name"],
            vehicle_type=item.get("type", "van"),
            base_node=item.get("base_node", "DEPOT_BKC"),
            capacity_kg=item.get("capacity_kg", 60.0),
            speed_kmh=item.get("speed_kmh", 40.0),
            color=item.get("color", "#00f0ff"),
            icon=item.get("icon", "truck")
        )
        for item in items
    ]

active_orders = load_initial_orders()
active_vehicles = load_initial_vehicles()


# ==========================================
# Frontend Static File Serving
# ==========================================
@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    if os.path.exists(os.path.join(FRONTEND_DIR, path)):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index.html")


# ==========================================
# Network Endpoints
# ==========================================
@app.route("/api/network", methods=["GET"])
def get_network():
    """Returns the full road network graph definition (nodes, edges, traffic)."""
    return jsonify({
        "city": network_data.get("city", "Mumbai"),
        "center": network_data.get("center", [19.0178, 72.8478]),
        "zoom": network_data.get("zoom", 12),
        "nodes": [node.to_dict() for node in graph.nodes.values()],
        "edges": network_data.get("edges", [])
    })


# ==========================================
# Order Management Endpoints
# ==========================================
@app.route("/api/orders", methods=["GET"])
def get_orders():
    """Retrieve all current orders."""
    return jsonify([o.to_dict() for o in active_orders])


@app.route("/api/orders", methods=["POST"])
def add_order():
    """Create a new delivery order."""
    data = request.get_json() or {}
    pickup = data.get("pickup")
    dropoff = data.get("dropoff")

    if not pickup or pickup not in graph.nodes:
        return jsonify({"error": f"Invalid or missing pickup node '{pickup}'"}), 400
    if not dropoff or dropoff not in graph.nodes:
        return jsonify({"error": f"Invalid or missing dropoff node '{dropoff}'"}), 400
    if pickup == dropoff:
        return jsonify({"error": "Pickup and dropoff nodes cannot be identical"}), 400

    new_id = data.get("id") or f"ORD-{uuid.uuid4().hex[:6].upper()}"
    new_order = Order(
        order_id=new_id,
        customer=data.get("customer", "Direct Client"),
        pickup=pickup,
        dropoff=dropoff,
        weight_kg=float(data.get("weight_kg", 10.0)),
        priority=data.get("priority", "NORMAL"),
        deadline_mins=int(data.get("deadline_mins", 90)),
        description=data.get("description", "Custom order created from UI")
    )
    active_orders.append(new_order)
    return jsonify(new_order.to_dict()), 201


@app.route("/api/orders/<order_id>", methods=["DELETE"])
def delete_order(order_id):
    """Delete an order by ID."""
    global active_orders
    initial_len = len(active_orders)
    active_orders = [o for o in active_orders if o.id != order_id]
    if len(active_orders) == initial_len:
        return jsonify({"error": "Order not found"}), 404
    return jsonify({"success": True, "message": f"Order {order_id} removed"})


@app.route("/api/orders/reset", methods=["POST"])
def reset_orders():
    """Reset orders back to default initial sample set."""
    global active_orders
    active_orders = load_initial_orders()
    return jsonify({"success": True, "orders": [o.to_dict() for o in active_orders]})


# ==========================================
# Vehicle Fleet Endpoints
# ==========================================
@app.route("/api/vehicles", methods=["GET"])
def get_vehicles():
    """Retrieve all current fleet vehicles."""
    return jsonify([v.to_dict() for v in active_vehicles])


@app.route("/api/vehicles", methods=["POST"])
def add_vehicle():
    """Register a new vehicle into the fleet."""
    data = request.get_json() or {}
    base_node = data.get("base_node", "DEPOT_BKC")
    if base_node not in graph.nodes:
        return jsonify({"error": f"Invalid base depot node '{base_node}'"}), 400

    new_id = data.get("id") or f"VEH-{len(active_vehicles) + 1}"
    new_vehicle = Vehicle(
        vehicle_id=new_id,
        name=data.get("name", f"Delivery Unit {new_id}"),
        vehicle_type=data.get("type", "van"),
        base_node=base_node,
        capacity_kg=float(data.get("capacity_kg", 50.0)),
        speed_kmh=float(data.get("speed_kmh", 40.0)),
        color=data.get("color", "#ec4899"),
        icon=data.get("icon", "truck")
    )
    active_vehicles.append(new_vehicle)
    return jsonify(new_vehicle.to_dict()), 201


# ==========================================
# Optimization & Dispatch Endpoint
# ==========================================
@app.route("/api/optimize", methods=["POST"])
def run_optimization():
    """
    Run full multi-vehicle route optimization:
    Dispatches active orders across active fleet vehicles with capacity & priority constraints,
    solves stop sequences using Nearest Neighbor + 2-Opt local search,
    interpolates exact road path coordinates via A*,
    and calculates empirical savings against a Naive (FIFO) baseline.
    """
    data = request.get_json() or {}
    cost_metric = data.get("cost_metric", "time")  # 'time' or 'distance'

    dispatcher = Dispatcher(graph)
    result = dispatcher.run_optimization(active_vehicles, active_orders, cost_metric=cost_metric)

    return jsonify(result)


# ==========================================
# Algorithm Comparison Playground (Dijkstra vs A*)
# ==========================================
@app.route("/api/pathfind", methods=["POST"])
def compare_pathfinding():
    """
    Point-to-point shortest path benchmark comparing Dijkstra's Algorithm vs A* Search.
    Returns visited nodes order, path length, explored node counts, and run times.
    """
    data = request.get_json() or {}
    start_id = data.get("start")
    goal_id = data.get("goal")
    cost_metric = data.get("cost_metric", "time")

    if not start_id or start_id not in graph.nodes:
        return jsonify({"error": f"Invalid start node '{start_id}'"}), 400
    if not goal_id or goal_id not in graph.nodes:
        return jsonify({"error": f"Invalid goal node '{goal_id}'"}), 400

    dijkstra_res = Dijkstra.find_shortest_path(graph, start_id, goal_id, cost_metric)
    astar_res = AStar.find_shortest_path(graph, start_id, goal_id, cost_metric)

    # Calculate explored nodes difference
    nodes_saved = dijkstra_res["nodes_explored"] - astar_res["nodes_explored"]
    nodes_saved_pct = round((nodes_saved / max(1, dijkstra_res["nodes_explored"])) * 100.0, 1)

    return jsonify({
        "dijkstra": dijkstra_res,
        "astar": astar_res,
        "comparison": {
            "dijkstra_explored": dijkstra_res["nodes_explored"],
            "astar_explored": astar_res["nodes_explored"],
            "nodes_saved": nodes_saved,
            "nodes_saved_percent": nodes_saved_pct,
            "dijkstra_time_ms": dijkstra_res["execution_time_ms"],
            "astar_time_ms": astar_res["execution_time_ms"]
        }
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Starting Route Optimization Engine on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=True)
