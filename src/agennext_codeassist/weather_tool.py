"""Weather tool: fetches weather information.

Provides:
- Current conditions
- Forecast
- Weather alerts
- Location-based weather
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import json


# === Weather Types ===

@dataclass
class WeatherCondition:
    """Current weather condition."""
    temperature_c: float
    condition: str  # sunny, cloudy, rain, storm, snow, fog
    humidity: int = 0
    wind_speed_kmh: float = 0.0
    feels_like_c: float = 0.0
    uv_index: int = 0
    
    # Visibility
    visibility_km: float = 10.0
    
    # Precipitation
    precipitation_chance: int = 0
    precipitation_mm: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "temperature": self.temperature_c,
            "condition": self.condition,
            "humidity": self.humidity,
            "wind": self.wind_speed_kmh,
            "feels_like": self.feels_like_c,
            "uv": self.uv_index,
            "visibility": self.visibility_km,
            "rain_chance": self.precipitation_chance,
        }


@dataclass
class WeatherForecast:
    """Weather forecast for a day."""
    date: str  # YYYY-MM-DD
    high_c: float
    low_c: float
    condition: str
    precipitation_chance: int
    
    # Hourly detail
    hourly: list[dict[str, Any]] = field(default_factory=list)
    
    def get_recommendation(self) -> str:
        """Get activity recommendation based on forecast."""
        if self.precipitation_chance > 70:
            return "Stay indoors or bring rain gear"
        elif self.precipitation_chance > 40:
            return "Consider bringing umbrella"
        elif "rain" in self.condition.lower():
            return "Pack rain gear just in case"
        elif "storm" in self.condition.lower():
            return "Watch for severe weather"
        elif "snow" in self.condition.lower():
            return "Dress warmly for snow"
        elif self.high_c > 30:
            return "Stay cool, stay hydrated"
        elif self.low_c < 0:
            return "Bundle up, stay warm"
        
        return "Good weather for outdoor activities"


@dataclass
class WeatherAlerts:
    """Weather alerts/warnings."""
    alert_type: str  # watch, warning, advisory
    severity: str  # minor, moderate, severe, extreme
    title: str
    description: str
    start_time: str
    end_time: str
    
    def is_active(self) -> bool:
        """Check if alert is currently active."""
        now = datetime.now()
        
        try:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            return start <= now <= end
        except Exception:
            return False


# === Weather Tool ===

class WeatherTool:
    """Tool for fetching weather information."""
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or ""
    
    def get_current(
        self,
        location: str,  # city name or "auto"
    ) -> WeatherCondition | None:
        """Get current weather for location."""
        # Try WeatherAPI.com first (free tier available)
        if self.api_key:
            return self._weatherapi_current(location)
        
        # Fallback to OpenWeatherMap free
        return self._openweather_current(location)
    
    def get_forecast(
        self,
        location: str,
        days: int = 3,
    ) -> list[WeatherForecast]:
        """Get forecast for location."""
        if self.api_key:
            return self._weatherapi_forecast(location, days)
        
        return self._openweather_forecast(location, days)
    
    def get_alerts(self, location: str) -> list[WeatherAlerts]:
        """Get weather alerts for location."""
        if not self.api_key:
            return []
        
        return self._weatherapi_alerts(location)
    
    def _weatherapi_current(self, location: str) -> WeatherCondition | None:
        """WeatherAPI.com current weather."""
        try:
            import urllib.request
            
            url = (
                f"https://api.weatherapi.com/v1/current.json"
                f"?key={self.api_key}&q={location}&aqi=no"
            )
            
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            if "current" in data:
                c = data["current"]
                return WeatherCondition(
                    temperature_c=c["temp_c"],
                    condition=c["condition"]["text"].lower(),
                    humidity=c["humidity"],
                    wind_speed_kmh=c["wind_kph"],
                    feels_like_c=c["feelslike_c"],
                    uv_index=c.get("uv", 0),
                    visibility_km=c.get("vis_km", 10),
                    precipitation_chance=data.get("forecast", {}).get("forecastday", [{}])[0]
                    .get("day", {}).get("daily_chance_of_rain", 0),
                )
        except Exception as e:
            print(f"WeatherAPI error: {e}")
            return None
        
        return None
    
    def _weatherapi_forecast(
        self,
        location: str,
        days: int,
    ) -> list[WeatherForecast]:
        """WeatherAPI.com forecast."""
        try:
            import urllib.request
            
            url = (
                f"https://api.weatherapi.com/v1/forecast.json"
                f"?key={self.api_key}&q={location}&days={days}"
            )
            
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            forecasts = []
            for day in data.get("forecast", {}).get("forecastday", []):
                d = day.get("day", {})
                forecasts.append(WeatherForecast(
                    date=day.get("date", ""),
                    high_c=d.get("maxtemp_c", 0),
                    low_c=d.get("mintemp_c", 0),
                    condition=d.get("condition", {}).get("text", "").lower(),
                    precipitation_chance=d.get("daily_chance_of_rain", 0),
                ))
            
            return forecasts
        
        except Exception:
            return []
    
    def _weatherapi_alerts(self, location: str) -> list[WeatherAlerts]:
        """WeatherAPI.com alerts."""
        try:
            import urllib.request
            
            url = (
                f"https://api.weatherapi.com/v1/forecast.json"
                f"?key={self.api_key}&q={location}&alerts=yes"
            )
            
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            alerts = []
            for alert in data.get("alerts", {}).get("alert", []):
                alerts.append(WeatherAlerts(
                    alert_type=alert.get("event", ""),
                    severity=alert.get("severity", ""),
                    title=alert.get("headline", ""),
                    description=alert.get("desc", ""),
                    start_time=alert.get("effective", ""),
                    end_time=alert.get("expires", ""),
                ))
            
            return alerts
        
        except Exception:
            return []
    
    def _openweather_current(self, location: str) -> WeatherCondition | None:
        """OpenWeatherMap free API."""
        try:
            import urllib.request
            import os
            
            api_key = os.getenv("OPENWEATHER_API_KEY", "")
            if not api_key:
                return None
            
            # Get coordinates for location first
            geo_url = (
                f"https://api.openweathermap.org/geo/1.0/direct"
                f"?q={location}&limit=1&appid={api_key}"
            )
            
            req = urllib.request.Request(geo_url)
            resp = urllib.request.urlopen(req, timeout=10)
            geo_data = json.loads(resp.read().decode())
            
            if not geo_data:
                return None
            
            lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]
            
            # Get weather
            weather_url = (
                f"https://api.openweathermap.org/data/2.5/weather"
                f"?lat={lat}&lon={lon}&appid={api_key}&units=metric"
            )
            
            req = urllib.request.Request(weather_url)
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            main = data.get("main", {})
            weather = data.get("weather", [{}])[0]
            wind = data.get("wind", {})
            
            return WeatherCondition(
                temperature_c=main.get("temp", 0),
                condition=weather.get("main", "").lower(),
                humidity=main.get("humidity", 0),
                wind_speed_kmh=wind.get("speed", 0) * 3.6,  # m/s to km/h
                feels_like_c=main.get("feels_like", 0),
            )
        
        except Exception:
            return None
    
    def _openweather_forecast(self, location: str, days: int) -> list[WeatherForecast]:
        """OpenWeatherMap forecast (requires paid API)."""
        # Free tier doesn't include forecast
        return []


# === Weather Integration ===

def get_weather_for_context(
    location: str = "auto",
) -> dict[str, Any]:
    """Get weather info for situation context."""
    import os
    
    api_key = os.getenv("WEATHER_API_KEY") or os.getenv("OPENWEATHER_API_KEY")
    tool = WeatherTool(api_key)
    
    # Get current
    current = tool.get_current(location)
    
    # Get forecast
    forecast = tool.get_forecast(location, 3)
    
    # Build context
    ctx = {
        "weather_condition": "unknown",
        "temperature_c": None,
        "rain_probability": 0,
        "recommendation": "",
    }
    
    if current:
        ctx["weather_condition"] = current.condition
        ctx["temperature_c"] = current.temperature_c
        ctx["rain_probability"] = current.precipitation_chance
        
        if current.precipitation_chance > 60:
            ctx["recommendation"] = "Bring rain gear"
        elif current.condition in ["rain", "thunderstorm", "storm"]:
            ctx["recommendation"] = "Stay dry, avoid outdoors"
        elif current.temperature_c > 30:
            ctx["recommendation"] = "Stay cool"
        elif current.temperature_c < 0:
            ctx["recommendation"] = "Bundle up"
    
    if forecast:
        today = forecast[0]
        ctx["rain_probability"] = today.precipitation_chance
        ctx["recommendation"] = today.get_recommendation()
        
        if len(forecast) > 1:
            tomorrow = forecast[1]
            if tomorrow.precipitation_chance > today.precipitation_chance:
                ctx["recommendation"] += f", Tomorrow: {tomorrow.get_recommendation()}"
    
    return ctx


def update_situation_with_weather(
    situation_location: str = "auto",
) -> None:
    """Update environment with weather info."""
    import os
    
    weather = get_weather_for_context(situation_location)
    
    if weather.get("temperature_c"):
        os.environ["TEMPERATURE_C"] = str(weather["temperature_c"])
    
    if weather.get("weather_condition"):
        cond = weather["weather_condition"].upper()
        if cond in ["CLEAR", "SUNNY"]:
            os.environ["WEATHER_CONDITION"] = "CLEAR"
        elif "RAIN" in cond or "DRIZZLE" in cond:
            os.environ["WEATHER_CONDITION"] = "RAINING"
        elif "THUNDER" in cond or "STORM" in cond:
            os.environ["WEATHER_CONDITION"] = "STORMING"
        elif "CLOUD" in cond:
            os.environ["WEATHER_CONDITION"] = "CLOUDY"
        elif "SNOW" in cond:
            os.environ["WEATHER_CONDITION"] = "SNOWING"
        elif "FOG" in cond or "MIST" in cond:
            os.environ["WEATHER_CONDITION"] = "FOGGY"
    
    if weather.get("rain_probability", 0) > 40:
        os.environ["WEATHER_FORECAST"] = "POSSIBLE_RAIN"


# === Singleton ===

_weather_tool: WeatherTool | None = None


def get_weather_tool() -> WeatherTool:
    import os
    global _weather_tool
    
    if _weather_tool is None:
        api_key = os.getenv("WEATHER_API_KEY") or os.getenv("OPENWEATHER_API_KEY")
        _weather_tool = WeatherTool(api_key)
    
    return _weather_tool