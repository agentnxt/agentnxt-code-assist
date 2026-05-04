"""Travel discovery: hotels, attractions, things to do.

Integrates with TripAdvisor-style APIs for:
- Hotels and accommodations
- Attractions and activities
- Restaurants when traveling
- Travel guides
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import json
import os


# === Hotel Types ===

@dataclass
class Hotel:
    """A hotel or accommodation."""
    name: str
    address: str
    
    location: tuple[float, float]
    
    # Rating
    rating: float = 0.0
    review_count: int = 0
    
    # Price
    price_level: int = 0  # 1-4
    low_season: float = 0.0
    high_season: float = 0.0
    
    # Amenities
    amenities: list[str] = None
    
    # Images
    photos: list[str] = None
    
    def get_price_range(self) -> str:
        if self.price_level <= 1:
            return "$"
        elif self.price_level == 2:
            return "$$"
        elif self.price_level == 3:
            return "$$$"
        return "$$$$"
    
    def get_summary(self) -> str:
        rating = f"⭐ {self.rating:.1f}" if self.rating else ""
        price = self.get_price_range()
        return f"{self.name} {rating} {price}"


@dataclass
class Attraction:
    """Tourist attraction or activity."""
    name: str
    description: str
    
    location: tuple[float, float]
    
    # Category
    category: str = ""  # museum, park, landmark, tour
    
    # Rating
    rating: float = 0.0
    review_count: int = 0
    
    # Time
    recommended_duration_minutes: int = 0
    
    # Cost
    admission_free: bool = True
    price: str = ""
    
    # Hours
    hours: str = ""
    
    def get_summary(self) -> str:
        time = f"{self.recommended_duration_minutes // 60}h" if self.recommended_duration_minutes else ""
        cost = "Free" if self.admission_free else self.price
        rating = f"⭐ {self.rating:.1f}" if self.rating else ""
        return f"{self.name} {rating} {time} {cost}"


# === Travel Discovery Tool ===

class TravelDiscovery:
    """TripAdvisor-style travel discovery."""
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("TRIPADVISOR_API_KEY") or os.getenv("TEQUILA_API_KEY") or ""
    
    # === Hotels ===
    
    def search_hotels(
        self,
        location: str | tuple[float, float],
        checkin: str = "",
        checkout: str = "",
        guests: int = 2,
        rooms: int = 1,
        sort_by: str = "rating",
        limit: int = 10,
    ) -> list[Hotel]:
        """Search hotels."""
        if self.api_key:
            return self._api_hotels(location, checkin, checkout, guests, rooms, sort_by, limit)
        
        return self._mock_hotels(location, limit)
    
    def _api_hotels(
        self,
        location: str | tuple[float, float],
        checkin: str,
        checkout: str,
        guests: int,
        rooms: int,
        sort_by: str,
        limit: int,
    ) -> list[Hotel]:
        """API-based hotel search (Amadeus/tequila style)."""
        # Placeholder - would integrate with real API
        return self._mock_hotels(location, limit)
    
    def _mock_hotels(
        self,
        location: str | tuple[float, float],
        limit: int,
    ) -> list[Hotel]:
        """Mock hotels for demo."""
        loc_name = location if isinstance(location, str) else "Destination"
        
        return [
            Hotel(
                name=f"Luxury Hotel {i+1}",
                address=f"123 Main Street, {loc_name}",
                location=(0, 0) if isinstance(location, str) else location,
                rating=4.5 - (i * 0.2),
                review_count=500 - (i * 50),
                price_level=4 - (i % 2),
                amenities=["WiFi", "Pool", "Gym", "Spa"],
            )
            for i in range(limit)
        ]
    
    def get_hotel_details(
        self,
        hotel_id: str,
    ) -> dict[str, Any]:
        """Get detailed hotel info."""
        return {
            "id": hotel_id,
            "description": "Beautiful hotel in great location",
            "amenities": ["WiFi", "Pool", "Gym", "Spa", "Restaurant"],
            "rooms": "Standard, Deluxe, Suite",
            "check_in": "3PM",
            "check_out": "11AM",
        }
    
    # === Attractions ===
    
    def search_attractions(
        self,
        location: str | tuple[float, float],
        category: str = "",
        limit: int = 10,
    ) -> list[Attraction]:
        """Search attractions."""
        return self._mock_attractions(location, category, limit)
    
    def _mock_attractions(
        self,
        location: str | tuple[float, float],
        category: str,
        limit: int,
    ) -> list[Attraction]:
        """Mock attractions."""
        loc_name = location if isinstance(location, str) else "Destination"
        
        types = [
            ("Museum", "museum", True, "2h", 0),
            ("Park", "park", True, "3h", 0),
            ("Landmark", "landmark", False, "1h", "$25"),
            ("Tour", "tour", False, "4h", "$50"),
            ("Beach", "beach", True, "5h", 0),
            ("Market", "market", True, "2h", 0),
        ]
        
        attractions = []
        for i, (name, cat, free, dur, price) in enumerate(types[:limit]):
            attractions.append(Attraction(
                name=f"{name} {i+1}",
                description=f"Famous {name.lower()} in {loc_name}",
                location=(0, 0) if isinstance(location, str) else location,
                category=cat,
                rating=4.5 - (i * 0.15),
                review_count=200 - (i * 20),
                recommended_duration_minutes=int(dur.replace("h", "")) * 60 if dur else 60,
                admission_free=free,
                price=price if price else "",
            ))
        
        return attractions
    
    # === Things To Do ===
    
    def get_things_to_do(
        self,
        location: str | tuple[float, float],
        duration_hours: int = 4,
    ) -> list[dict[str, Any]]:
        """Generate full day itinerary."""
        attractions = self.search_attractions(location, limit=8)
        
        # Group by morning/afternoon/evening
        morning = []
        afternoon = []
        evening = []
        
        for i, attr in enumerate(attractions):
            if i < 3:
                morning.append(attr)
            elif i < 6:
                afternoon.append(attr)
            else:
                evening.append(attr)
        
        return [
            {"time": "Morning", "activities": [a.get_summary() for a in morning]},
            {"time": "Afternoon", "activities": [a.get_summary() for a in afternoon]},
            {"time": "Evening", "activities": [a.get_summary() for a in evening]},
        ]
    
    # === Travel Guide ===
    
    def get_travel_guide(
        self,
        destination: str,
    ) -> dict[str, Any]:
        """Get complete travel guide for destination."""
        hotels = self.search_hotels(destination, limit=3)
        attractions = self.search_attractions(destination, limit=5)
        
        return {
            "destination": destination,
            "top_hotels": [
                {"name": h.name, "rating": h.rating, "price": h.get_price_range()}
                for h in hotels
            ],
            "top_attractions": [
                {"name": a.name, "category": a.category, "rating": a.rating}
                for a in attractions[:5]
            ],
            "best_time_to_visit": "Spring or Fall",
            "local_transport": "Metro or taxi",
            "currency": "USD",
        }


# === Smart Recommendations ===

def get_smart_hotel_recommendations(
    user_profile,
    location: str,
    budget: str = "moderate",
) -> list[Hotel]:
    """Get hotel recommendations based on user preferences."""
    discovery = TravelDiscovery()
    
    hotels = discovery.search_hotels(location, limit=10)
    
    # Filter by budget
    if budget == "budget":
        hotels = [h for h in hotels if h.price_level <= 2]
    elif budget == "premium":
        hotels = [h for h in hotels if h.price_level >= 3]
    
    # Filter by user interests
    # (would check user_profile for preferences)
    
    return hotels[:5]


def get_seasonal_travel_tips(
    destination: str,
    travel_date: str,
) -> list[str]:
    """Get seasonal tips for travel."""
    tips = []
    
    # Check season
    if travel_date:
        month = travel_date.split("-")[1] if "-" in travel_date else ""
        
        if month in ["06", "07", "08"]:
            tips.append("Peak summer - book ahead")
            tips.append("Hot weather - pack light")
        elif month in ["12", "01", "02"]:
            tips.append("Winter - expect crowds during holidays")
            tips.append("Cold but festive atmosphere")
        elif month in ["03", "04", "05"]:
            tips.append("Spring - pleasant weather")
            tips.append("Shoulder season - good deals")
        else:
            tips.append("Fall - fall foliage")
            tips.append("Cooler temps")
    
    return tips


def create_itinerary(
    destination: str,
    days: int = 3,
    interests: list[str] = None,
) -> dict[str, Any]:
    """Create travel itinerary."""
    discovery = TravelDiscovery()
    
    guide = discovery.get_travel_guide(destination)
    
    itinerary = {
        "destination": destination,
        "duration_days": days,
        "overview": guide,
        "daily_schedule": [],
    }
    
    # Generate daily schedules
    for day in range(1, days + 1):
        day_plan = discovery.get_things_to_do(destination, duration_hours=4)
        
        itinerary["daily_schedule"].append({
            "day": day,
            "activities": day_plan,
        })
    
    # Add tips
    itinerary["tips"] = get_seasonal_travel_tips(destination, "")
    
    return itinerary


# === Travel Context ===

def get_travel_context_for_destination(
    destination: str,
    user_id: str = "",
) -> str:
    """Get travel context for destination."""
    discovery = TravelDiscovery()
    guide = discovery.get_travel_guide(destination)
    
    lines = [f"## Travel Guide: {destination}"]
    
    if guide.get("best_time_to_visit"):
        lines.append(f"- Best time: {guide['best_time_to_visit']}")
    
    if guide.get("top_hotels"):
        lines.append("\n### Top Hotels")
        for h in guide["top_hotels"][:3]:
            lines.append(f"- {h['name']} ({h['price']}) ⭐{h['rating']}")
    
    if guide.get("top_attractions"):
        lines.append("\n### Top Attractions")
        for a in guide["top_attractions"][:5]:
            lines.append(f"- {a['name']} ({a['category']})")
    
    return "\n".join(lines)


# === Singleton ===

_discovery: TravelDiscovery | None = None


def get_travel_discovery() -> TravelDiscovery:
    global _discovery
    
    if _discovery is None:
        _discovery = TravelDiscovery()
    
    return _discovery


def search_hotels(location: str, limit: int = 10) -> list[Hotel]:
    return get_travel_discovery().search_hotels(location, limit=limit)


def get_travel_guide(destination: str) -> dict[str, Any]:
    return get_travel_discovery().get_travel_guide(destination)