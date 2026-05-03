"""Situational awareness: understands context for smart recommendations.

Factors:
- Location awareness (home, office, travel)
- Time awareness (working hours, night, weekends)
- Weather awareness (rain, sun, extreme temps)
- Resource awareness (battery, data, money)
- Situation-aware recommendations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Any

import json
import os


# === Context Types ===

class LocationType(Enum):
    HOME = "home"
    OFFICE = "office"
    TRAVEL = "travel"
    OUTDOORS = "outdoors"
    INDOORS = "indoors"
    VEHICLE = "vehicle"
    PUBLIC = "public"
    UNKNOWN = "unknown"


class TimeOfDay(Enum):
    NIGHT = "night"  # 10pm - 6am
    MORNING = "morning"  # 6am - 12pm
    AFTERNOON = "afternoon"  # 12pm - 6pm
    EVENING = "evening"  # 6pm - 10pm


class WeatherCondition(Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAINING = "raining"
    STORMING = "storming"
    SNOWING = "snowing"
    FOGGY = "foggy"
    WINDY = "windy"
    HOT = "hot"  # > 35C
    COLD = "cold"  # < 0C
    UNKNOWN = "unknown"


class ResourceState(Enum):
    PLENTY = "plenty"  # > 50%
    MODERATE = "moderate"  # 20-50%
    LOW = "low"  # < 20%
    CRITICAL = "critical"  # < 5%


@dataclass
class Situation:
    """Current situational context."""
    location: LocationType = LocationType.UNKNOWN
    time_of_day: TimeOfDay = TimeOfDay.MORNING
    day_of_week: str = ""  # Monday, etc.
    
    weather: WeatherCondition = WeatherCondition.UNKNOWN
    temperature_c: float | None = None  # If known
    
    battery_percent: int | None = None
    network_type: str | None = None  # wifi, 5g, 4g, none
    internet_available: bool = True
    
    money_saved_mode: bool = False
    
    # Resources
    data_remaining_gb: float | None = None
    storage_remaining_gb: float | None = None
    
    # People nearby
    people_nearby: int = 0  # 0 = alone
    
    # Noise level
    noise_level: str = "quiet"  # quiet, moderate, loud
    
    # Safety
    is_safe_outdoors: bool = True
    crime_rate_area: str = "normal"  # low, normal, high
    
    def get_time_period(self) -> str:
        hour = datetime.now(UTC).hour
        
        if 0 <= hour < 6 or hour >= 22:
            return "night"
        elif 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        else:
            return "evening"
    
    def determine_time_of_day(self) -> TimeOfDay:
        period = self.get_time_period()
        
        if period == "night":
            return TimeOfDay.NIGHT
        elif period == "morning":
            return TimeOfDay.MORNING
        elif period == "afternoon":
            return TimeOfDay.AFTERNOON
        else:
            return TimeOfDay.EVENING
    
    def determine_resource_state(self, resource: str) -> ResourceState:
        if resource == "battery" and self.battery_percent:
            if self.battery_percent > 50:
                return ResourceState.PLENTY
            elif self.battery_percent > 20:
                return ResourceState.MODERATE
            elif self.battery_percent > 5:
                return ResourceState.LOW
            else:
                return ResourceState.CRITICAL
        
        return ResourceState.PLENTY


# === Situation-Aware Recommendations ===

@dataclass
class Recommendation:
    """A situation-aware recommendation."""
    suggestion: str
    reason: str
    
    # Context
    condition: str  # When this applies
    priority: str = "normal"  # low, normal, high, critical
    
    # Trade-offs
    saves_money: bool = False
    saves_time: bool = False
    saves_energy: bool = False
    improves_safety: bool = False


class SituationAwareRecommender:
    """Makes smart recommendations based on situation."""
    
    def __init__(self, situation: Situation | None = None):
        self.situation = situation or self._detect_situation()
    
    def _detect_situation(self) -> Situation:
        """Detect current situation from environment."""
        from datetime import datetime
        
        sit = Situation()
        
        # Time detection
        sit.time_of_day = sit.determine_time_of_day()
        sit.day_of_week = datetime.now(UTC).strftime("%A")
        
        # Location (rough detection from env)
        cwd = os.getcwd().lower()
        if "home" in cwd:
            sit.location = LocationType.HOME
        elif "office" in cwd or "work" in cwd:
            sit.location = LocationType.OFFICE
        else:
            sit.location = LocationType.INDOORS
        
        # Battery (if available)
        battery = os.getenv("BATTERY_PERCENT")
        if battery:
            try:
                sit.battery_percent = int(battery)
            except ValueError:
                pass
        
        # Network
        sit.internet_available = self._check_internet()
        
        # Weather (from env vars or API)
        sit.weather = self._get_weather_condition()
        
        # Time-sensitive settings
        sit.money_saved_mode = os.getenv("MONEY_SAVER_MODE", "").lower() == "true"
        
        return sit
    
    def _check_internet(self) -> bool:
        """Check if internet is available."""
        import urllib.request
        try:
            urllib.request.urlopen("https://api.github.com", timeout=3)
            return True
        except Exception:
            return False
    
    def _get_weather_condition(self) -> WeatherCondition:
        """Get weather from environment or API."""
        # Check env first
        weather = os.getenv("WEATHER_CONDITION", "").upper()
        if weather:
            try:
                return WeatherCondition[weather]
            except KeyError:
                pass
        
        # Check temp
        temp = os.getenv("TEMPERATURE_C")
        if temp:
            try:
                t = float(temp)
                if t > 35:
                    return WeatherCondition.HOT
                elif t < 0:
                    return WeatherCondition.COLD
            except ValueError:
                pass
        
        return WeatherCondition.UNKNOWN
    
    def get_recommendations(self) -> list[Recommendation]:
        """Get situation-aware recommendations."""
        recs = []
        sit = self.situation
        
        # === WEATHER-BASED ===
        
        if sit.weather in [WeatherCondition.RAINING, WeatherCondition.STORMING]:
            recs.append(Recommendation(
                suggestion="Use a car or rideshare instead of walking",
                reason="It's raining - walking in rain is unpleasant and you could get sick",
                condition="rainy",
                priority="high",
                improves_safety=True,
            ))
            recs.append(Recommendation(
                suggestion="Bring an umbrella or rain jacket",
                reason="Rain is expected - stay dry",
                condition="rainy",
                priority="high",
            ))
        
        elif sit.weather == WeatherCondition.CLEAR and sit.temperature_c and sit.temperature_c > 30:
            recs.append(Recommendation(
                suggestion="Stay hydrated, wear sunscreen",
                reason="It's hot outside - prevent dehydration and sunburn",
                condition="hot",
                priority="high",
            ))
            recs.append(Recommendation(
                suggestion="Consider going outside in early morning or evening",
                reason="Hot midday - safer to avoid direct sun",
                condition="hot",
                priority="normal",
            ))
        
        elif sit.weather == WeatherCondition.CLEAR and sit.temperature_c and sit.temperature_c < 5:
            recs.append(Recommendation(
                suggestion="Dress warmly in layers",
                reason="It's cold - dress for the temperature",
                condition="cold",
                priority="high",
            ))
        
        # === MONEY VS CONVENIENCE ===
        
        if sit.money_saved_mode or sit.weather == WeatherCondition.CLEAR:
            # Nice weather = good for walking
            recs.append(Recommendation(
                suggestion="Walk to save money",
                reason="Nice weather - walking is pleasant and free",
                condition="clear_weather",
                saves_money=True,
                priority="low",
            ))
        
        if sit.money_saved_mode and sit.weather in [WeatherCondition.RAINING, WeatherCondition.STORMING]:
            # If it's raining AND money-saving mode
            recs.append(Recommendation(
                suggestion="Consider public transit instead of rideshare",
                reason="Saving money in rain - transit is cheaper than rideshare",
                condition="rainy_cheap",
                saves_money=True,
                priority="normal",
            ))
        
        # === TIME-BASED ===
        
        if sit.time_of_day == TimeOfDay.NIGHT:
            recs.append(Recommendation(
                suggestion="Let someone know your ETA",
                reason="Night time - safety check-in",
                condition="night",
                priority="high",
                improves_safety=True,
            ))
            recs.append(Recommendation(
                suggestion="Stay in well-lit areas",
                reason="Night - visibility matters for safety",
                condition="night",
                priority="high",
                improves_safety=True,
            ))
        
        if sit.time_of_day == TimeOfDay.MORNING:
            if sit.day_of_week in ["Saturday", "Sunday"]:
                recs.append(Recommendation(
                    suggestion="Weekend - good time for errands",
                    reason="Weekend morning - less crowds",
                    condition="weekend",
                    priority="low",
                ))
        
        # === RESOURCE-BASED ===
        
        battery_state = sit.determine_resource_state("battery")
        
        if battery_state == ResourceState.CRITICAL:
            recs.append(Recommendation(
                suggestion="Find a charger soon",
                reason="Battery critically low",
                condition="low_battery",
                priority="critical",
            ))
            recs.append(Recommendation(
                suggestion="Use airplane mode to extend battery",
                reason="Save remaining battery",
                condition="low_battery",
                priority="high",
                saves_energy=True,
            ))
        elif battery_state == ResourceState.LOW:
            recs.append(Recommendation(
                suggestion="Start looking for charging option",
                reason="Battery getting low",
                condition="low_battery",
                priority="normal",
            ))
        
        # === NETWORK-BASED ===
        
        if not sit.internet_available:
            if sit.location == LocationType.OFFICE:
                recs.append(Recommendation(
                    suggestion="Use office WiFi for large downloads",
                    reason="Office has better connectivity",
                    condition="no_internet",
                    priority="normal",
                ))
            else:
                recs.append(Recommendation(
                    suggestion="Download content for offline use",
                    reason="Limited connectivity - prepare offline",
                    condition="no_internet",
                    priority="normal",
                ))
        
        # === LOCATION-BASED ===
        
        if sit.location == LocationType.OUTDOORS:
            if sit.weather == WeatherCondition.CLEAR:
                recs.append(Recommendation(
                    suggestion="Perfect weather to be outside",
                    reason="Enjoy the good weather",
                    condition="outdoor_clear",
                    priority="low",
                ))
        
        if sit.location == LocationType.PUBLIC:
            if sit.noise_level == "loud":
                recs.append(Recommendation(
                    suggestion="Find quieter spot for calls",
                    reason="Too noisy here",
                    condition="noisy",
                    priority="normal",
                ))
        
        return recs
    
    def get_critical_warnings(self) -> list[str]:
        """Get critical warnings for current situation."""
        warnings = []
        sit = self.situation
        
        # Weather dangers
        if sit.weather == WeatherCondition.STORMING:
            warnings.append("⚠️ StORM WARNING: Stay indoors if possible")
        
        if sit.weather == WeatherCondition.RAINING and sit.crime_rate_area == "high":
            warnings.append("⚠️ Rain in high-crime area - stay alert")
        
        # Resource dangers
        if sit.battery_percent and sit.battery_percent < 5:
            warnings.append(f"⚠️ Battery critical: {sit.battery_percent}%")
        
        # Time dangers  
        if sit.time_of_day == TimeOfDay.NIGHT and sit.location == LocationType.OUTDOORS:
            warnings.append("⚠️ Night time outdoors - stay in lit areas")
        
        return warnings
    
    def should_suggest(self, suggestion_type: str) -> tuple[bool, str]:
        """Check if we should make a certain type of suggestion."""
        sit = self.situation
        
        # Money vs convenience
        if suggestion_type == "walk_to_save_money":
            if sit.money_saved_mode and sit.weather in [WeatherCondition.RAINING, WeatherCondition.STORMING]:
                return False, "Not in rain - would be unpleasant"
            return True, ""
        
        if suggestion_type == "umbrella":
            if sit.weather in [WeatherCondition.RAINING, WeatherCondition.STORMING]:
                return True, "Rain expected"
            # Check forecast
            forecast = os.getenv("WEATHER_FORECAST", "").upper()
            if "RAIN" in forecast:
                return True, f"Forecast: {forecast}"
            return False, ""
        
        return True, ""
    
    def get_prompt_context(self) -> str:
        """Get situation context for prompt."""
        sit = self.situation
        
        lines = [
            "## Situation Context",
            f"- Location: {sit.location.value}",
            f"- Time: {sit.time_of_day.value} ({sit.get_time_period()})",
            f"- Day: {sit.day_of_week}",
        ]
        
        if sit.weather != WeatherCondition.UNKNOWN:
            lines.append(f"- Weather: {sit.weather.value}" + 
                       (f" ({sit.temperature_c}°C)" if sit.temperature_c else ""))
        
        if sit.battery_percent:
            lines.append(f"- Battery: {sit.battery_percent}%")
        
        lines.append(f"- Internet: {'yes' if sit.internet_available else 'no'}")
        
        # Warnings
        warnings = self.get_critical_warnings()
        if warnings:
            lines.append("\n## Critical Warnings")
            lines.extend(warnings)
        
        # Recommendations
        recs = self.get_recommendations()
        if recs:
            lines.append("\n## Situation Recommendations")
            for rec in recs[:5]:
                if rec.priority in ["high", "critical"]:
                    lines.append(f"- 🔴 {rec.suggestion} ({rec.condition})")
                else:
                    lines.append(f"- {rec.suggestion} ({rec.condition})")
        
        return "\n".join(lines)


# === Singleton ===

 recommender: SituationAwareRecommender | None = None


def get_situation_aware_recommender() -> SituationAwareRecommender:
    global _recommender
    if _recommender is None:
        _recommender = SituationAwareRecommender()
    return _recommender


def get_current_situation() -> Situation:
    return get_situation_aware_recommender().situation


def should_suggest(suggestion_type: str) -> tuple[bool, str]:
    return get_situation_aware_recommender().should_suggest(suggestion_type)


def get_situation_prompt() -> str:
    return get_situation_aware_recommender().get_prompt_context()