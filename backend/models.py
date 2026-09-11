"""
Data models for the Intelligent Route and Delivery Optimization System.
"""

from typing import Dict, Any, List, Optional


class Node:
    """Represents a geographical location / junction / hub in the road graph."""

    def __init__(
        self,
        node_id: str,
        name: str,
        lat: float,
        lng: float,
        node_type: str = "customer",
        description: str = ""
    ):
        self.id = node_id
        self.name = name
        self.lat = float(lat)
        self.lng = float(lng)
        self.type = node_type  # 'depot', 'hub', 'customer', 'transit'
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "lat": self.lat,
            "lng": self.lng,
            "type": self.type,
            "description": self.description
        }


class Edge:
    """Represents a navigable road connecting two nodes."""

    def __init__(
        self,
        edge_id: str,
        source: str,
        target: str,
        distance_km: float,
        speed_limit_kmh: float = 40.0,
        traffic_factor: float = 1.0,
        road_name: str = "",
        is_one_way: bool = False
    ):
        self.id = edge_id
        self.source = source
        self.target = target
        self.distance_km = float(distance_km)
        self.speed_limit_kmh = float(speed_limit_kmh)
        self.traffic_factor = float(traffic_factor)  # 1.0 = clear, 1.5 = heavy
        self.road_name = road_name
        self.is_one_way = is_one_way

    @property
    def travel_time_mins(self) -> float:
        """Calculate effective travel time in minutes taking traffic into account."""
        effective_speed = max(5.0, self.speed_limit_kmh / max(0.5, self.traffic_factor))
        return (self.distance_km / effective_speed) * 60.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "distance_km": self.distance_km,
            "speed_limit_kmh": self.speed_limit_kmh,
            "traffic_factor": self.traffic_factor,
            "travel_time_mins": round(self.travel_time_mins, 2),
            "road_name": self.road_name,
            "is_one_way": self.is_one_way
        }


class Order:
    """Represents a customer delivery request with weight, priority, and deadline."""

    PRIORITY_WEIGHTS = {
        "URGENT": 3,
        "HIGH": 2,
        "NORMAL": 1
    }

    def __init__(
        self,
        order_id: str,
        customer: str,
        pickup: str,
        dropoff: str,
        weight_kg: float,
        priority: str = "NORMAL",
        deadline_mins: int = 120,
        description: str = "",
        status: str = "PENDING"
    ):
        self.id = order_id
        self.customer = customer
        self.pickup = pickup
        self.dropoff = dropoff
        self.weight_kg = float(weight_kg)
        self.priority = priority.upper() if priority.upper() in self.PRIORITY_WEIGHTS else "NORMAL"
        self.deadline_mins = int(deadline_mins)
        self.description = description
        self.status = status  # 'PENDING', 'ASSIGNED', 'IN_TRANSIT', 'DELIVERED'
        self.assigned_vehicle_id: Optional[str] = None

    @property
    def priority_score(self) -> int:
        return self.PRIORITY_WEIGHTS.get(self.priority, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "customer": self.customer,
            "pickup": self.pickup,
            "dropoff": self.dropoff,
            "weight_kg": self.weight_kg,
            "priority": self.priority,
            "priority_score": self.priority_score,
            "deadline_mins": self.deadline_mins,
            "description": self.description,
            "status": self.status,
            "assigned_vehicle_id": self.assigned_vehicle_id
        }


class Vehicle:
    """Represents an active fleet unit (van/bike)."""

    def __init__(
        self,
        vehicle_id: str,
        name: str,
        vehicle_type: str = "van",
        base_node: str = "DEPOT_BKC",
        capacity_kg: float = 60.0,
        speed_kmh: float = 40.0,
        color: str = "#00f0ff",
        icon: str = "truck"
    ):
        self.id = vehicle_id
        self.name = name
        self.type = vehicle_type
        self.base_node = base_node
        self.capacity_kg = float(capacity_kg)
        self.speed_kmh = float(speed_kmh)
        self.color = color
        self.icon = icon
        self.current_node = base_node
        self.assigned_order_ids: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "base_node": self.base_node,
            "capacity_kg": self.capacity_kg,
            "speed_kmh": self.speed_kmh,
            "color": self.color,
            "icon": self.icon,
            "current_node": self.current_node,
            "assigned_order_ids": list(self.assigned_order_ids)
        }
