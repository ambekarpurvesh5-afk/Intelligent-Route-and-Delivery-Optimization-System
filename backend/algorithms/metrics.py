"""
Performance and environmental metrics calculator for delivery routes.
"""

from typing import Dict, Any


class MetricsCalculator:
    """Computes carbon footprints, fuel consumption, and performance analytics."""

    # Parameters
    VAN_FUEL_L_PER_KM = 0.11        # Diesel/Petrol equivalent for light commercial vehicle
    BIKE_FUEL_L_PER_KM = 0.035      # Two-wheeler fuel efficiency
    CO2_KG_PER_LITER = 2.31         # Standard emission factor (kg CO2 / liter of fuel)
    AVG_DRIVER_COST_PER_HR_INR = 180.0
    FUEL_PRICE_PER_LITER_INR = 104.2

    @classmethod
    def compute_route_cost(cls, distance_km: float, time_mins: float, vehicle_type: str = "van") -> Dict[str, float]:
        """Compute financial and environmental footprint of a given route."""
        fuel_rate = cls.VAN_FUEL_L_PER_KM if vehicle_type == "van" else cls.BIKE_FUEL_L_PER_KM
        fuel_liters = distance_km * fuel_rate
        co2_emissions_kg = fuel_liters * cls.CO2_KG_PER_LITER
        fuel_cost_inr = fuel_liters * cls.FUEL_PRICE_PER_LITER_INR
        driver_cost_inr = (time_mins / 60.0) * cls.AVG_DRIVER_COST_PER_HR_INR
        total_cost_inr = fuel_cost_inr + driver_cost_inr

        return {
            "fuel_liters": round(fuel_liters, 2),
            "co2_emissions_kg": round(co2_emissions_kg, 2),
            "fuel_cost_inr": round(fuel_cost_inr, 2),
            "driver_cost_inr": round(driver_cost_inr, 2),
            "total_cost_inr": round(total_cost_inr, 2)
        }
