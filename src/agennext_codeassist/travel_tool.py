"""Travel tool: integrates with Uber, Lyft, and travel APIs.

Provides:
- Ride estimation and booking
- Real-time driver availability
- Travel history
- Multi-modal transport options
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import json
import os


# === Travel Types ===

@dataclass
class RideEstimate:
    """Ride fare estimate."""
    pickup: str
    dropoff: str
    
    # Fare
    estimate: str = ""
    low_estimate: float = 0.0
    high_estimate: float = 0.0
    
    # Type
    ride_type: str = ""  # uberx, black, xl, pool
    display_name: str = ""
    
    # Time
    estimated_pickup_minutes: int = 0
    
    # Distance
    distance_km: float = 0.0
    
    # Multiplier (surge pricing)
    surge_multiplier: float = 1.0
    
    def get_summary(self) -> str:
        """Get summary."""
        parts = [self.display_name or self.ride_type]
        
        if self.estimated_pickup_minutes > 0:
            parts.append(f"Pickup: {self.estimated_pickup_minutes} min")
        
        if self.surge_multiplier > 1.0:
            parts.append(f"⚠️ Surge: {self.surge_multiplier:.1f}x")
        
        if self.low_estimate > 0:
            parts.append(f"${self.low_estimate:.0f}-${self.high_estimate:.0f}")
        
        return " | ".join(parts)


@dataclass
class DriverInfo:
    """Driver information."""
    name: str
    photo_url: str = ""
    
    vehicle_info: str = ""  # "Silver Honda Civic"
    license_plate: str = ""
    
    rating: float = 0.0
    trips_completed: int = 0
    
    eta_minutes: int = 0
    
    current_location: tuple[float, float] | None = None


@dataclass
class TripStatus:
    """Current trip status."""
    trip_id: str
    
    status: str  # request, accepted, arriving, in_progress, completed
    
    driver: DriverInfo | None = None
    
    eta_dropoff: str = ""
    
    pickup_eta: int = 0
    
    current_fare_estimate: str = ""
    
    trip_progress: int = 0  # 0-100%


# === Travel Tool ===

class TravelTool:
    """Uber/Lyft integration."""
    
    def __init__(
        self,
        uber_token: str | None = None,
        lyft_token: str | None = None,
    ):
        self.uber_token = uber_token or os.getenv("UBER_SERVER_TOKEN") or os.getenv("UBER_ACCESS_TOKEN") or ""
        self.lyft_token = lyft_token or os.getenv("LYFT_ACCESS_TOKEN") or ""
    
    # === Uber Estimates ===
    
    def get_ride_estimates(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
    ) -> list[RideEstimate]:
        """GetUber ride estimates."""
        if not self.uber_token:
            return self._mock_estimates(start_lat, start_lon, end_lat, end_lon)
        
        try:
            import urllib.request
            import urllib.parse
            
            url = "https://api.uber.com/v1.2/estimates/price"
            
            params = {
                "start_latitude": start_lat,
                "start_longitude": start_lon,
                "end_latitude": end_lat,
                "end_longitude": end_lon,
            }
            
            headers = {
                "Authorization": f"Bearer {self.uber_token}",
                "Content-Type": "application/json",
            }
            
            req = urllib.request.Request(
                f"{url}?{urllib.parse.urlencode(params)}",
                headers=headers,
            )
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            estimates = []
            for product in data.get("prices", []):
                estimates.append(RideEstimate(
                    pickup=f"{start_lat},{start_lon}",
                    dropoff=f"{end_lat},{end_lon}",
                    ride_type=product.get("localized_display_name", "").lower().replace(" ", "_"),
                    display_name=product.get("localized_display_name", ""),
                    estimate=product.get("estimate", ""),
                    low_estimate=float(product.get("low_estimate", 0).replace("$", "").replace(" ", "0")),
                    high_estimate=float(product.get("high_estimate", 0).replace("$", "").replace(" ", "0")),
                    distance_km=float(product.get("distance", 0)),
                    surge_multiplier=float(product.get("surge_multiplier", 1)),
                ))
            
            return estimates
        
        except Exception:
            return self._mock_estimates(start_lat, start_lon, end_lat, end_lon)
    
    def _mock_estimates(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
    ) -> list[RideEstimate]:
        """Mock estimates for demo."""
        # Calculate rough distance
        import math
        dist = math.sqrt((end_lat - start_lat)**2 + (end_lon - start_lon)**2) * 111  # km
        
        return [
            RideEstimate(
                pickup=f"{start_lat},{start_lon}",
                dropoff=f"{end_lat},{end_lon}",
                ride_type="uberx",
                display_name="UberX",
                low_estimate=dist * 1.5 + 5,
                high_estimate=dist * 2 + 8,
                estimated_pickup_minutes=5,
                distance_km=dist,
            ),
            RideEstimate(
                pickup=f"{start_lat},{start_lon}",
                dropoff=f"{end_lat},{end_lon}",
                ride_type="black",
                display_name="Uber Black",
                low_estimate=dist * 2.5 + 15,
                high_estimate=dist * 3 + 20,
                estimated_pickup_minutes=10,
                distance_km=dist,
            ),
            RideEstimate(
                pickup=f"{start_lat},{start_lon}",
                dropoff=f"{end_lat},{end_lon}",
                ride_type="uberxl",
                display_name="Uber XL",
                low_estimate=dist * 2 + 10,
                high_estimate=dist * 2.5 + 15,
                estimated_pickup_minutes=8,
                distance_km=dist,
            ),
        ]
    
    # === Uber Time Estimate ===
    
    def get_driver_eta(
        self,
        start_lat: float,
        start_lon: float,
    ) -> list[DriverInfo]:
        """Get nearby driver ETAs."""
        if not self.uber_token:
            return self._mock_drivers()
        
        try:
            import urllib.request
            import urllib.parse
            
            url = "https://api.uber.com/v1.2/timeestimates"
            params = {
                "start_latitude": start_lat,
                "start_longitude": start_lon,
            }
            
            headers = {
                "Authorization": f"Bearer {self.uber_token}",
            }
            
            req = urllib.request.Request(
                f"{url}?{urllib.parse.urlencode(params)}",
                headers=headers,
            )
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            drivers = []
            for product in data.get("times", []):
                drivers.append(DriverInfo(
                    name="Nearby Driver",
                    eta_minutes=product.get("estimate", 0) // 60,
                ))
            
            return drivers
        
        except Exception:
            return self._mock_drivers()
    
    def _mock_drivers(self) -> list[DriverInfo]:
        """Mock drivers."""
        return [
            DriverInfo(name="John D.", eta_minutes=4, rating=4.8, trips_completed=2500),
            DriverInfo(name="Sarah M.", eta_minutes=7, rating=4.9, trips_completed=4200),
            DriverInfo(name="Mike T.", eta_minutes=3, rating=4.7, trips_completed=1800),
        ]
    
    # === Trip History ===
    
    def get_trip_history(
        self,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get trip history."""
        if not self.uber_token:
            return []
        
        try:
            import urllib.request
            
            url = f"https://api.uber.com/v1.2/history?limit={limit}"
            
            headers = {
                "Authorization": f"Bearer {self.uber_token}",
            }
            
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            return [
                {
                    "id": trip.get("uuid", ""),
                    "status": trip.get("status", ""),
                    "distance": trip.get("distance", 0),
                    "start_time": trip.get("start_time", ""),
                    "end_time": trip.get("end_time", ""),
                }
                for trip in data.get("trips", [])
            ]
        
        except Exception:
            return []


# === Multi-Modal Travel ===

def compare_transport_options(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    traffic_level: str = "light",
) -> list[dict[str, Any]]:
    """Compare all transport options."""
    travel_tool = TravelTool()
    
    options = []
    
    # 1. Uber rides
    rides = travel_tool.get_ride_estimates(start_lat, start_lon, end_lat, end_lon)
    
    for ride in rides:
        options.append({
            "type": "rideshare",
            "name": ride.display_name,
            "estimate": f"${ride.low_estimate:.0f}-{ride.high_estimate:.0f}",
            "time_minutes": int(ride.estimated_pickup_minutes + (ride.distance_km * 3)),
            "surge": ride.surge_multiplier > 1.0,
        })
    
    # 2. Walk
    import math
    walk_dist = math.sqrt((end_lat - start_lat)**2 + (end_lon - start_lon)**2) * 111000
    walk_time = int(walk_dist / 80)  # 80m/min walking
    
    options.append({
        "type": "walking",
        "name": "Walk",
        "estimate": "Free",
        "time_minutes": walk_time,
    })
    
    # 3. Bike (if < 10km)
    bike_dist_km = math.sqrt((end_lat - start_lat)**2 + (end_lon - start_lon)**2) * 111
    if bike_dist_km < 10:
        bike_time = int(bike_dist_km / 15 * 60)  # 15km/h
        
        options.append({
            "type": "cycling",
            "name": "Bike",
            "estimate": "Free (rent)",
            "time_minutes": bike_time,
        })
    
    # 4. Transit (mock - would need real API)
    if bike_dist_km > 2:
        options.append({
            "type": "transit",
            "name": "Transit",
            "estimate": "$2-5",
            "time_minutes": int(bike_time * 1.5),
        })
    
    # Sort by time
    options.sort(key=lambda x: x["time_minutes"])
    
    return options


def suggest_best_ride_option(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    preference: str = "fastest",  # fastest, cheapest, safest
    money_saver_mode: bool = False,
) -> str:
    """Suggest best transportation."""
    options = compare_transport_options(start_lat, start_lon, end_lat, end_lon)
    
    if not options:
        return "No options available"
    
    if preference == "cheapest" or money_saver_mode:
        # Find cheapest non-free option
        for opt in options:
            if opt["type"] != "rideshare" and opt["estimate"] != "Free":
                return f"{opt['name']} - {opt['estimate']}, {opt['time_minutes']} min"
        
        # Fall back to walking
        return f"Walk - Free, {options[0]['time_minutes']} min"
    
    # Fastest
    for opt in options:
        if opt["type"] != "walking":
            return f"{opt['name']} - {opt['estimate']}, {opt['time_minutes']} min"
    
    return options[0]["name"]


# === Travel History Manager ===

class TravelHistory:
    """Manages travel history and preferences."""
    
    def __init__(self, storage_path: str = ".agennext/travel"):
        self.storage_path = storage_path
        import os
        os.makedirs(self.storage_path, exist_ok=True)
    
    def record_trip(
        self,
        user_id: str,
        trip_type: str,
        from_location: str,
        to_location: str,
        distance_km: float,
        duration_minutes: float,
        cost: float,
    ):
        """Record a trip for history."""
        import os
        import json
        from datetime import datetime
        
        path = os.path.join(self.storage_path, f"{user_id}.json")
        
        # Load existing
        if os.path.exists(path):
            with open(path) as f:
                history = json.load(f)
        else:
            history = {"trips": []}
        
        # Add trip
        history["trips"].append({
            "date": datetime.now().isoformat(),
            "type": trip_type,
            "from": from_location,
            "to": to_location,
            "distance_km": distance_km,
            "duration_minutes": duration_minutes,
            "cost": cost,
        })
        
        # Keep last 50
        history["trips"] = history["trips"][-50:]
        
        # Save
        with open(path, "w") as f:
            json.dump(history, f, indent=2)
    
    def get_travel_stats(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """Get travel statistics."""
        import os
        import json
        
        path = os.path.join(self.storage_path, f"{user_id}.json")
        
        if not os.path.exists(path):
            return {"total_trips": 0}
        
        with open(path) as f:
            history = json.load(f)
        
        trips = history.get("trips", [])
        
        if not trips:
            return {"total_trips": 0}
        
        total_cost = sum(t.get("cost", 0) for t in trips)
        total_dist = sum(t.get("distance_km", 0) for t in trips)
        
        return {
            "total_trips": len(trips),
            "total_spent": total_cost,
            "avg_cost_per_trip": total_cost / len(trips),
            "total_distance_km": total_dist,
            "favorite_type": max(set(t.get("type", "") for t in trips), default="uber"),
        }


# === Travel Context ===

def get_travel_context(
    user_id: str,
    destination: str,
) -> str:
    """Get travel context for user prompt."""
    history = TravelHistory()
    stats = history.get_travel_stats(user_id)
    
    travel_tool = TravelTool()
    estimates = travel_tool.get_ride_estimates(0, 0, 0, 0)  # Would need real coords
    
    lines = ["## Travel"]
    
    lines.append(f"- Total trips: {stats.get('total_trips', 0)}")
    lines.append(f"- Total spent: ${stats.get('total_spent', 0):.2f}")
    
    if estimates:
        lines.append("\n### Estimated Rides")
        for est in estimates[:3]:
            lines.append(f"- {est.get_summary()}")
    
    return "\n".join(lines)


# === Singleton ===

_travel_tool: TravelTool | None = None


def get_travel_tool() -> TravelTool:
    global _travel_tool
    
    if _travel_tool is None:
        _travel_tool = TravelTool()
    
    return _travel_tool


def get_ride_estimates(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> list[RideEstimate]:
    return get_travel_tool().get_ride_estimates(start_lat, start_lon, end_lat, end_lon)