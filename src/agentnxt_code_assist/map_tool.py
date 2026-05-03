"""Map and location tool: provides maps, traffic, geolocation, and nearby info.

Provides:
- Geocoding (address to coords)
- Reverse geocoding (coords to address)
- Directions/routing
- Traffic information
- Nearby places search
- Distance calculations
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import json
import os


# === Location Types ===

@dataclass
class Location:
    """A geographic location."""
    latitude: float
    longitude: float
    name: str = ""
    address: str = ""
    city: str = ""
    country: str = ""
    
    def to_tuple(self) -> tuple[float, float]:
        return (self.latitude, self.longitude)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "lat": self.latitude,
            "lon": self.longitude,
            "name": self.name,
            "address": self.address,
            "city": self.city,
        }


@dataclass
class Route:
    """Directions route."""
    origin: Location
    destination: Location
    
    distance_km: float = 0.0
    duration_minutes: float = 0.0
    
    steps: list[dict[str, Any]] = None
    
    # Traffic-aware
    traffic_distance_km: float = 0.0
    traffic_duration_minutes: float = 0.0
    
    # Alternative routes
    alternatives: list[dict[str, Any]] = None
    
    def get_recommendation(self) -> str:
        """Get travel recommendation."""
        if self.traffic_duration_minutes > self.duration_minutes * 1.5:
            return f"Heavy traffic - allow {self.traffic_duration_minutes:.0f} min"
        
        if self.distance_km > 50:
            if self.duration_minutes / self.distance_km > 2:
                return f"Traffic is bad - consider public transit ({self.duration_minutes:.0f} min)"
            return f"Drive yourself ({self.duration_minutes:.0f} min)"
        
        if self.distance_km < 5:
            return "Walking distance" if self.duration_minutes < 45 else f"Bike or walk ({self.duration_minutes:.0f} min)"
        
        return f"Take route ({self.duration_minutes:.0f} min, {self.distance_km:.1f} km)"


@dataclass
class Place:
    """A place/point of interest."""
    name: str
    address: str
    
    location: Location
    
    category: str = ""  # restaurant, gas_station, parking, etc.
    rating: float = 0.0
    
    # Business hours
    hours: str = ""
    is_open: bool = True
    
    # Price level
    price_level: int = 0  # 1-4
    
    # Distance
    distance_km: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "address": self.address,
            "category": self.category,
            "rating": self.rating,
            "distance": f"{self.distance_km:.1f} km",
            "open": self.is_open,
        }


# === Map Tool ===

class MapTool:
    """Tool for map and location services."""
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY") or ""
    
    # === Geocoding ===
    
    def geocode(self, address: str) -> Location | None:
        """Convert address to coordinates."""
        if not self.api_key:
            return self._nominatim_geocode(address)
        
        return self._google_geocode(address)
    
    def reverse_geocode(self, lat: float, lon: float) -> Location | None:
        """Convert coordinates to address."""
        if not self.api_key:
            return None
        
        return self._google_reverse_geocode(lat, lon)
    
    def _google_geocode(self, address: str) -> Location | None:
        """Google Maps geocoding."""
        try:
            import urllib.request
            import urllib.parse
            
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {"address": address, "key": self.api_key}
            
            req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}")
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            if data.get("status") == "OK":
                result = data["results"][0]
                geometry = result["geometry"]["location"]
                components = result.get("address_components", [])
                
                city = ""
                country = ""
                for comp in components:
                    if "locality" in comp.get("types", []):
                        city = comp["long_name"]
                    if "country" in comp.get("types", []):
                        country = comp["long_name"]
                
                return Location(
                    latitude=geometry["lat"],
                    longitude=geometry["lng"],
                    name=result.get("formatted_address", ""),
                    address=result.get("formatted_address", ""),
                    city=city,
                    country=country,
                )
        
        except Exception:
            pass
        
        return None
    
    def _google_reverse_geocode(self, lat: float, lon: float) -> Location | None:
        """Google Maps reverse geocoding."""
        try:
            import urllib.request
            import urllib.parse
            
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {"latlng": f"{lat},{lon}", "key": self.api_key}
            
            req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}")
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            if data.get("status") == "OK":
                result = data["results"][0]
                return Location(
                    latitude=lat,
                    longitude=lon,
                    name=result.get("formatted_address", ""),
                    address=result.get("formatted_address", ""),
                )
        
        except Exception:
            pass
        
        return None
    
    def _nominatim_geocode(self, address: str) -> Location | None:
        """OpenStreetMap Nominatim (free)."""
        try:
            import urllib.request
            import urllib.parse
            
            url = "https://nominatim.openstreetmap.org/search"
            params = {"q": address, "format": "json", "limit": 1}
            
            req = urllib.request.Request(
                f"{url}?{urllib.parse.urlencode(params)}",
                headers={"User-Agent": "CodeAssist/1.0"},
            )
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            if data:
                result = data[0]
                return Location(
                    latitude=float(result.get("lat", 0)),
                    longitude=float(result.get("lon", 0)),
                    name=result.get("display_name", ""),
                    address=result.get("display_name", ""),
                )
        
        except Exception:
            pass
        
        return None
    
    # === Directions ===
    
    def get_directions(
        self,
        origin: str | Location,
        destination: str | Location,
        mode: str = "driving",
    ) -> Route | None:
        """Get directions between two points."""
        if not self.api_key:
            return None
        
        try:
            import urllib.request
            import urllib.parse
            
            # Convert to strings
            orig = origin if isinstance(origin, str) else f"{origin.latitude},{origin.longitude}"
            dest = destination if isinstance(destination, str) else f"{destination.latitude},{destination.longitude}"
            
            url = "https://maps.googleapis.com/maps/api/directions/json"
            params = {
                "origin": orig,
                "destination": dest,
                "mode": mode,
                "key": self.api_key,
            }
            
            req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}")
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            if data.get("status") == "OK":
                route = data["routes"][0]
                legs = route["legs"][0]
                
                return Route(
                    origin=Location(0, 0),  # Simplified
                    destination=Location(0, 0),
                    distance_km=legs["distance"]["value"] / 1000,
                    duration_minutes=legs["duration"]["value"] / 60,
                    steps=[
                        {"instruction": step.get("html_instructions", ""), "distance": step.get("distance", {})}
                        for step in legs.get("steps", [])
                    ],
                )
        
        except Exception:
            pass
        
        return None
    
    # === Traffic ===
    
    def get_traffic_info(
        self,
        origin: str,
        destination: str,
    ) -> dict[str, Any]:
        """Get traffic information."""
        route = self.get_directions(origin, destination)
        
        if not route:
            return {"error": "Could not get traffic info"}
        
        # Calculate traffic impact
        if route.traffic_duration_minutes > route.duration_minutes:
            delay = route.traffic_duration_minutes - route.duration_minutes
            return {
                "traffic_level": "heavy" if delay > 15 else "moderate",
                "delay_minutes": delay,
                "recommended_duration": route.traffic_duration_minutes,
            }
        
        return {
            "traffic_level": "light",
            "delay_minutes": 0,
            "recommended_duration": route.duration_minutes,
        }
    
    # === Nearby Places ===
    
    def nearby_search(
        self,
        location: str | Location,
        radius_m: int = 1000,
        type: str = "",  # restaurant, gas_station, etc.
        keyword: str = "",
    ) -> list[Place]:
        """Search nearby places."""
        if not self.api_key:
            return []
        
        try:
            import urllib.request
            import urllib.parse
            
            loc = location if isinstance(location, str) else f"{location.latitude},{location.longitude}"
            
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                "location": loc,
                "radius": radius_m,
                "key": self.api_key,
            }
            
            if type:
                params["type"] = type
            if keyword:
                params["keyword"] = keyword
            
            req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}")
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            places = []
            for result in data.get("results", []):
                geometry = result.get("geometry", {}).get("location", {})
                place = Place(
                    name=result.get("name", ""),
                    address=result.get("vicinity", ""),
                    location=Location(
                        latitude=geometry.get("lat", 0),
                        longitude=geometry.get("lng", 0),
                    ),
                    category=result.get("types", [""])[0],
                    rating=result.get("rating", 0),
                )
                places.append(place)
            
            return places
        
        except Exception:
            return []
    
    # === Distance Matrix ===
    
    def distance_matrix(
        self,
        origins: list[str | Location],
        destinations: list[str | Location],
    ) -> list[list[dict[str, Any]]]:
        """Get distance matrix between multiple points."""
        if not self.api_key:
            return []
        
        try:
            import urllib.request
            import urllib.parse
            
            orig_str = "|".join(
                o if isinstance(o, str) else f"{o.latitude},{o.longitude}"
                for o in origins
            )
            dest_str = "|".join(
                d if isinstance(d, str) else f"{d.latitude},{d.longitude}"
                for d in destinations
            )
            
            url = "https://maps.googleapis.com/maps/api/distancematrix/json"
            params = {
                "origins": orig_str,
                "destinations": dest_str,
                "key": self.api_key,
            }
            
            req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}")
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            matrix = []
            for row in data.get("rows", []):
                row_data = []
                for elem in row.get("elements", []):
                    if elem.get("status") == "OK":
                        row_data.append({
                            "distance": elem["distance"]["text"],
                            "duration": elem["duration"]["text"],
                        })
                    else:
                        row_data.append({"error": elem.get("status")})
                matrix.append(row_data)
            
            return matrix
        
        except Exception:
            return []


# === Place Categories Helper ===

def get_nearby_essentials(
    location: str | Location,
    include: list[str] | None = None,
) -> dict[str, list[Place]]:
    """Get nearby essential places.
    
    Categories: gas_station, restaurant, pharmacy, hospital, parking
    """
    if include is None:
        include = ["gas_station", "restaurant", "pharmacy"]
    
    tool = MapTool()
    results = {}
    
    for category in include:
        results[category] = tool.nearby_search(
            location,
            type=category,
            radius_m=2000,
        )[:3]
    
    return results


def get_fastest_route(
    origin: str,
    destination: str,
) -> dict[str, Any]:
    """Get fastest route with traffic consideration."""
    tool = MapTool()
    
    # Get driving
    driving = tool.get_directions(origin, destination, "driving")
    
    # Get transit
    transit = tool.get_directions(origin, destination, "transit")
    
    results = {
        "driving": driving.get_recommendation() if driving else "Not available",
        "transit": transit.get_recommendation() if transit else "Not available",
    }
    
    # Compare
    if driving and transit:
        if driving.duration_minutes > transit.duration_minutes * 1.5:
            results["recommendation"] = "Take transit - faster in traffic"
        else:
            results["recommendation"] = "Drive yourself"
    
    return results


# === Singleton ===

_map_tool: MapTool | None = None


def get_map_tool() -> MapTool:
    global _map_tool
    
    if _map_tool is None:
        _map_tool = MapTool()
    
    return _map_tool