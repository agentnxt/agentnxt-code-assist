"""User profile: tracks user interests, preferences, and personalization.

Tracks:
- Interests and hobbies
- Favorite sports, teams
- Favorite food, cuisines
- Preferences
- Activity history
- Syncs with sports/food APIs
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import json
import os


# === Interest Types ===

class InterestCategory(Enum):
    SPORTS = "sports"
    FOOD = "food"
    MUSIC = "music"
    MOVIES = "movies"
    BOOKS = "books"
    TRAVEL = "travel"
    TECH = "tech"
    GAMING = "gaming"
    NEWS = "news"
    OTHER = "other"


@dataclass
class UserInterest:
    """A user interest."""
    name: str
    category: InterestCategory
    
    # Level
    level: str = "casual"  # casual, interested, fanatic
    
    # Activity
    last_active: str = ""  # ISO timestamp
    
    # Engagement
    engagement_score: int = 0  # 0-100


@dataclass
class SportsPreference:
    """Sports preferences."""
    favorite_sports: list[str] = field(default_factory=list)
    favorite_teams: list[dict[str, Any]] = field(default_factory=list)
    favorite_players: list[dict[str, Any]] = field(default_factory=list)
    
    # Watch habits
    watch_frequency: str = "weekly"  # daily, weekly, monthly, rarely
    favorite_times: list[str] = field(default_factory=list)  # "evening", "morning"


@dataclass
class FoodPreference:
    """Food preferences."""
    favorite_cuisines: list[str] = field(default_factory=list)
    dietary_restrictions: list[str] = field(default_factory=list)  # vegetarian, vegan, gluten-free
    allergies: list[str] = field(default_factory=list)
    
    # Preferences
    spice_level: str = "medium"  # mild, medium, hot
    price_range: str = "moderate"  # budget, moderate, premium
    
    # Favorite restaurants (tracked)
    favorite_places: list[dict[str, Any]] = field(default_factory=list)
    
    # Ordering
    delivery_preference: bool = True


@dataclass
class UserProfile:
    """Complete user profile."""
    user_id: str
    
    # Basic
    name: str = ""
    email: str = ""
    
    # Location
    location: str = ""  # City for local recommendations
    coordinates: tuple[float, float] | None = None
    
    # Preferences
    sports: SportsPreference = field(default_factory=SportsPreference)
    food: FoodPreference = field(default_factory=FoodPreference)
    
    # Other interests
    interests: list[UserInterest] = field(default_factory=list)
    
    # Tracking
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = ""
    
    def add_interest(self, name: str, category: InterestCategory, level: str = "interested"):
        """Add an interest."""
        # Check if exists
        for interest in self.interests:
            if interest.name.lower() == name.lower():
                interest.level = level
                interest.engagement_score += 10
                return
        
        # Add new
        self.interests.append(UserInterest(
            name=name,
            category=category,
            level=level,
            engagement_score=10,
        ))
    
    def get_top_interests(self, category: InterestCategory | None = None, limit: int = 5) -> list[UserInterest]:
        """Get top interests."""
        interests = self.interests
        
        if category:
            interests = [i for i in interests if i.category == category]
        
        interests.sort(key=lambda x: x.engagement_score, reverse=True)
        return interests[:limit]


# === Sports Integration ===

class SportsFeed:
    """Sports news and scores integration."""
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("SPORTS_API_KEY") or os.getenv("THE_ODDS_API_KEY") or ""
    
    def get_team_news(
        self,
        team_name: str,
        league: str = "",
    ) -> list[dict[str, Any]]:
        """Get news for a team."""
        import urllib.request
        
        # Try TheRundown API (free)
        if self.api_key:
            try:
                url = f"https://api.therundown.com/thedb/properties/{team_name.replace(' ', '-').lower()}"
                req = urllib.request.Request(url, headers={"Authorization": f"Key {self.api_key}"})
                resp = urllib.request.urlopen(req, timeout=10)
                return json.loads(resp.read().decode())
            except Exception:
                pass
        
        # Fallback: return placeholder
        return [{"title": f"Recent {team_name} news", "source": "sports"}]
    
    def get_league_scores(
        self,
        league: str = "nfl",  # nfl, nba, mlb, nhl
    ) -> list[dict[str, Any]]:
        """Get live scores."""
        if not self.api_key:
            return []
        
        import urllib.request
        
        try:
            url = f"https://api.therundown.com/mlb/{league}/scores"
            req = urllib.request.Request(url, headers={"Authorization": f"Key {self.api_key}"})
            resp = urllib.request.urlopen(req, timeout=10)
            return json.loads(resp.read().decode()).get("games", [])
        except Exception:
            return []
    
    def get_team_schedule(
        self,
        team_name: str,
    ) -> list[dict[str, Any]]:
        """Get upcoming games for team."""
        # Placeholder - would integrate with real API
        return []


# === Food Integration (Zomato-style) ===

class FoodDiscovery:
    """Food and restaurant discovery."""
    
    def __init__(
        self,
        api_key: str | None = None,
    ):
        self.api_key = api_key or os.getenv("ZOMATO_API_KEY") or os.getenv("YELP_API_KEY") or ""
    
    def search_restaurants(
        self,
        location: str | tuple[float, float],
        cuisine: str = "",
        sort_by: str = "rating",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search restaurants."""
        if not self.api_key:
            return self._mock_restaurants(location, cuisine, limit)
        
        try:
            import urllib.request
            import urllib.parse
            
            # Try Yelp Fusion API
            url = "https://api.yelp.com/v3/businesses/search"
            
            params = {
                "limit": limit,
                "sort_by": sort_by,
            }
            
            if isinstance(location, str):
                params["location"] = location
            else:
                params["latitude"] = location[0]
                params["longitude"] = location[1]
            
            if cuisine:
                params["categories"] = cuisine
            
            req = urllib.request.Request(
                f"{url}?{urllib.parse.urlencode(params)}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            return [
                {
                    "name": b.get("name", ""),
                    "address": ", ".join(b.get("location", {}).get("display_address", [])),
                    "rating": b.get("rating", 0),
                    "price": b.get("price", ""),
                    "categories": [c.get("title", "") for c in b.get("categories", [])],
                    "url": b.get("url", ""),
                }
                for b in data.get("businesses", [])
            ]
        
        except Exception:
            return self._mock_restaurants(location, cuisine, limit)
    
    def _mock_restaurants(
        self,
        location: str | tuple[float, float],
        cuisine: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Return mock restaurants for demo."""
        return [
            {
                "name": f"Popular {cuisine} Place {i+1}",
                "address": "123 Main St" if isinstance(location, str) else "Nearby",
                "rating": 4.5 - (i * 0.3),
                "price": "$$" if i % 2 else "$$$",
                "categories": [cuisine] if cuisine else ["Italian"],
            }
            for i in range(limit)
        ]
    
    def get_reviews(
        self,
        restaurant_id: str,
    ) -> list[dict[str, Any]]:
        """Get restaurant reviews."""
        return []
    
    def get_cuisine_trending(
        self,
        location: str,
    ) -> list[dict[str, Any]]:
        """Get trending cuisines."""
        # Could integrate with real API
        return [
            {"cuisine": "Japanese", "growth": 25},
            {"cuisine": "Mexican", "growth": 18},
            {"cuisine": "Thai", "growth": 15},
        ]


# === User Profile Manager ===

class ProfileManager:
    """Manages user profiles."""
    
    def __init__(self, storage_path: str = ".agennext/profiles"):
        self.storage_path = os.path.expanduser(storage_path)
        os.makedirs(self.storage_path, exist_ok=True)
        
        self.profiles: dict[str, UserProfile] = {}
    
    def get_profile(
        self,
        user_id: str,
    ) -> UserProfile:
        """Get or create profile."""
        if user_id in self.profiles:
            return self.profiles[user_id]
        
        # Try load from storage
        profile = self._load_profile(user_id)
        
        if profile:
            self.profiles[user_id] = profile
            return profile
        
        # Create new
        profile = UserProfile(user_id=user_id)
        self.profiles[user_id] = profile
        return profile
    
    def update_from_activity(
        self,
        user_id: str,
        activity: str,
        interest: str,
    ):
        """Update profile based on activity."""
        profile = self.get_profile(user_id)
        
        # Category detection
        if activity in ["watched", "played", "team", "score"]:
            cat = InterestCategory.SPORTS
        elif activity in ["ordered", "cooked", "restaurant", "cuisine"]:
            cat = InterestCategory.FOOD
        else:
            cat = InterestCategory.OTHER
        
        # Add/update interest
        profile.add_interest(interest, cat, level="interested")
        profile.last_updated = datetime.now().isoformat()
        
        # Save
        self._save_profile(profile)
        
        return profile
    
    def get_recommendations(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """Get personalized recommendations."""
        profile = self.get_profile(user_id)
        
        recs = {"sports": [], "food": [], "news": []}
        
        # Sports recommendations based on favorites
        for team in profile.sports.favorite_teams:
            recs["sports"].append({
                "team": team.get("name", ""),
                "recommendation": f"Check {team.get('name')} latest news",
            })
        
        # Food recommendations based on cuisine
        for cuisine in profile.food.favorite_cuisines[:2]:
            recs["food"].append({
                "cuisine": cuisine,
                "recommendation": f"Find {cuisine} restaurants nearby",
            })
        
        return recs
    
    def _save_profile(self, profile: UserProfile):
        """Save profile to storage."""
        import pickle
        
        path = os.path.join(self.storage_path, f"{profile.user_id}.json")
        
        data = {
            "user_id": profile.user_id,
            "name": profile.name,
            "location": profile.location,
            "sports": {
                "favorite_sports": profile.sports.favorite_sports,
                "favorite_teams": profile.sports.favorite_teams,
            },
            "food": {
                "favorite_cuisines": profile.food.favorite_cuisines,
                "dietary_restrictions": profile.food.dietary_restrictions,
                "spice_level": profile.food.spice_level,
            },
            "interests": [
                {"name": i.name, "category": i.category.value, "level": i.level, "score": i.engagement_score}
                for i in profile.interests
            ],
            "last_updated": profile.last_updated,
        }
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    
    def _load_profile(self, user_id: str) -> UserProfile | None:
        """Load profile from storage."""
        path = os.path.join(self.storage_path, f"{user_id}.json")
        
        if not os.path.exists(path):
            return None
        
        try:
            with open(path) as f:
                data = json.load(f)
            
            profile = UserProfile(
                user_id=data.get("user_id", user_id),
                name=data.get("name", ""),
                location=data.get("location", ""),
            )
            
            # Load sports
            sports = data.get("sports", {})
            profile.sports.favorite_sports = sports.get("favorite_sports", [])
            profile.sports.favorite_teams = sports.get("favorite_teams", [])
            
            # Load food
            food = data.get("food", {})
            profile.food.favorite_cuisines = food.get("favorite_cuisines", [])
            profile.food.dietary_restrictions = food.get("dietary_restrictions", [])
            
            # Load interests
            for interest in data.get("interests", []):
                profile.interests.append(UserInterest(
                    name=interest.get("name", ""),
                    category=InterestCategory(interest.get("category", "other")),
                    level=interest.get("level", "interested"),
                    engagement_score=interest.get("score", 0),
                ))
            
            profile.last_updated = data.get("last_updated", "")
            
            return profile
        
        except Exception:
            return None


# === Integration with Discovery ===

def get_personalized_sports_feed(
    user_id: str,
) -> list[dict[str, Any]]:
    """Get sports feed based on user preferences."""
    manager = ProfileManager()
    profile = manager.get_profile(user_id)
    
    sports_feed = SportsFeed()
    
    articles = []
    
    # Get news for favorite teams
    for team in profile.sports.favorite_teams[:3]:
        news = sports_feed.get_team_news(team.get("name", ""))
        articles.extend(news)
    
    return articles


def get_personalized_food_options(
    user_id: str,
    location: str | tuple[float, float],
) -> list[dict[str, Any]]:
    """Get food options based on user preferences."""
    manager = ProfileManager()
    profile = manager.get_profile(user_id)
    
    food_tool = FoodDiscovery()
    
    options = []
    
    # Get restaurants for favorite cuisines
    for cuisine in profile.food.favorite_cuisines[:2]:
        restaurants = food_tool.search_restaurants(location, cuisine=cuisine, limit=5)
        options.extend(restaurants)
    
    return options


# === Singleton ===

_profile_manager: ProfileManager | None = None


def get_profile_manager() -> ProfileManager:
    global _profile_manager
    
    if _profile_manager is None:
        _profile_manager = ProfileManager()
    
    return _profile_manager


def get_user_profile(user_id: str) -> UserProfile:
    return get_profile_manager().get_profile(user_id)