"""News tool: provides current news and information.

Provides:
- Top headlines by category/location
- Search news by keyword
- News for specific topics
- Company/stock news
- Integration with situation awareness
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import json
import os


# === News Types ===

@dataclass
class NewsArticle:
    """A news article."""
    title: str
    description: str
    url: str
    source: str
    
    # Content
    content: str = ""
    author: str = ""
    
    # When
    published_at: str = ""
    
    # Image
    image_url: str = ""
    
    # Category
    category: str = "general"
    
    def get_summary(self) -> str:
        """Get short summary."""
        return f"{self.title} - {self.source}"
    
    def get_time_ago(self) -> str:
        """Get time since published."""
        try:
            published = datetime.fromisoformat(self.published_at.replace("Z", "+00:00"))
            now = datetime.now()
            delta = (now - published).total_seconds()
            
            hours = int(delta / 3600)
            if hours > 24:
                return f"{hours // 24}d ago"
            if hours > 0:
                return f"{hours}h ago"
            
            minutes = int(delta / 60)
            return f"{minutes}m ago"
        
        except Exception:
            return ""


@dataclass
class NewsCategory:
    """News category with articles."""
    name: str
    articles: list[NewsArticle]
    
    def get_top_headlines(self) -> list[str]:
        """Get headlines."""
        return [a.get_summary() for a in self.articles[:5]]


# === News Tool ===

class NewsTool:
    """Tool for fetching news."""
    
    def __init__(
        self,
        api_key: str | None = None,
    ):
        self.api_key = api_key or os.getenv("NEWS_API_KEY") or os.getenv("NEWSORG_API_KEY") or ""
    
    # === Top Headlines ===
    
    def get_headlines(
        self,
        country: str = "us",
        category: str = "",
        page_size: int = 10,
    ) -> list[NewsArticle]:
        """Get top headlines."""
        if self.api_key:
            return self._newsapi_headlines(country, category, page_size)
        
        return self._gnews_headlines(country, category, page_size)
    
    def _newsapi_headlines(
        self,
        country: str,
        category: str,
        page_size: int,
    ) -> list[NewsArticle]:
        """NewsAPI.org headlines."""
        try:
            import urllib.request
            
            url = "https://newsapi.org/v2/top-headlines"
            params = {
                "country": country,
                "pageSize": page_size,
                "apiKey": self.api_key,
            }
            
            if category:
                params["category"] = category
            
            import urllib.parse
            req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}")
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            articles = []
            for article in data.get("articles", []):
                articles.append(NewsArticle(
                    title=article.get("title", ""),
                    description=article.get("description", ""),
                    url=article.get("url", ""),
                    source=article.get("source", {}).get("name", ""),
                    content=article.get("content", ""),
                    author=article.get("author", ""),
                    published_at=article.get("publishedAt", ""),
                    image_url=article.get("urlToImage", ""),
                ))
            
            return articles
        
        except Exception:
            return []
    
    def _gnews_headlines(
        self,
        country: str,
        category: str,
        page_size: int,
    ) -> list[NewsArticle]:
        """GNews API headlines (free tier)."""
        try:
            import urllib.request
            
            # Use GNews free API if no key
            url = "https://gnews.io/api/v4/top-headlines"
            params = {
                "lang": "en",
                "max": page_size,
            }
            
            if category:
                # Map to GNews categories
                category_map = {
                    "business": "business",
                    "technology": "technology",
                    "science": "science",
                    "health": "health",
                    "sports": "sports",
                    "entertainment": "entertainment",
                }
                params["category"] = category_map.get(category, "general")
            
            import urllib.parse
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            
            req = urllib.request.Request(full_url)
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            articles = []
            for article in data.get("articles", []):
                articles.append(NewsArticle(
                    title=article.get("title", ""),
                    description=article.get("description", ""),
                    url=article.get("url", ""),
                    source=article.get("source", {}).get("name", ""),
                    published_at=article.get("publishedAt", ""),
                    image_url=article.get("image", ""),
                ))
            
            return articles
        
        except Exception:
            return []
    
    # === Search News ===
    
    def search(
        self,
        query: str,
        page_size: int = 10,
    ) -> list[NewsArticle]:
        """Search for news."""
        if self.api_key:
            return self._newsapi_search(query, page_size)
        
        return self._gnews_search(query, page_size)
    
    def _newsapi_search(
        self,
        query: str,
        page_size: int,
    ) -> list[NewsArticle]:
        """NewsAPI search."""
        try:
            import urllib.request
            import urllib.parse
            
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": query,
                "pageSize": page_size,
                "sortBy": "relevancy",
                "apiKey": self.api_key,
            }
            
            req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}")
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            articles = []
            for article in data.get("articles", []):
                articles.append(NewsArticle(
                    title=article.get("title", ""),
                    description=article.get("description", ""),
                    url=article.get("url", ""),
                    source=article.get("source", {}).get("name", ""),
                    published_at=article.get("publishedAt", ""),
                ))
            
            return articles
        
        except Exception:
            return []
    
    def _gnews_search(
        self,
        query: str,
        page_size: int,
    ) -> list[NewsArticle]:
        """GNews search."""
        try:
            import urllib.request
            import urllib.parse
            
            url = "https://gnews.io/api/v4/search"
            params = {
                "q": query,
                "lang": "en",
                "max": page_size,
            }
            
            req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}")
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            articles = []
            for article in data.get("articles", []):
                articles.append(NewsArticle(
                    title=article.get("title", ""),
                    description=article.get("description", ""),
                    url=article.get("url", ""),
                    source=article.get("source", {}).get("name", ""),
                    published_at=article.get("publishedAt", ""),
                ))
            
            return articles
        
        except Exception:
            return []
    
    # === Topic News ===
    
    def get_topic_news(
        self,
        topic: str,
    ) -> list[NewsArticle]:
        """Get news for specific topic."""
        return self.search(topic, page_size=5)
    
    def get_company_news(
        self,
        company: str,
    ) -> list[NewsArticle]:
        """Get news for a company."""
        return self.search(f"{company} stock OR {company} earnings OR {company} CEO", page_size=5)
    
    def get_tech_news(self) -> list[NewsArticle]:
        """Get technology news."""
        return self.get_headlines(category="technology", page_size=5)
    
    def get_business_news(self) -> list[NewsArticle]:
        """Get business news."""
        return self.get_headlines(category="business", page_size=5)
    
    def get_sports_news(self) -> list[NewsArticle]:
        """Get sports news."""
        return self.get_headlines(category="sports", page_size=5)
    
    def get_science_news(self) -> list[NewsArticle]:
        """Get science news."""
        return self.get_headlines(category="science", page_size=5)
    
    def get_health_news(self) -> list[NewsArticle]:
        """Get health news."""
        return self.get_headlines(category="health", page_size=5)


# === News Context Builder ===

def get_news_for_context(
    topics: list[str] | None = None,
) -> str:
    """Get news for context, formatted for prompt."""
    if topics is None:
        topics = ["technology", "business"]
    
    tool = NewsTool()
    lines = ["## Current News"]
    
    for topic in topics:
        articles = tool.get_topic_news(topic)
        
        if articles:
            lines.append(f"\n### {topic.title()}")
            for article in articles[:3]:
                lines.append(f"- {article.get_summary()}")
    
    return "\n".join(lines)


def get_trending_topics() -> list[str]:
    """Get trending topics from headlines."""
    tool = NewsTool()
    headlines = tool.get_headlines(page_size=10)
    
    topics = set()
    for article in headlines:
        # Extract keywords from title
        title = article.title.lower()
        
        # Common topics
        if "ai" in title or "openai" in title or "chatgpt" in title:
            topics.add("AI")
        if "trump" in title or "biden" in title:
            topics.add("Politics")
        if "stock" in title or "market" in title or "fed" in title:
            topics.add("Markets")
        if "climate" in title or "weather" in title:
            topics.add("Weather")
        if "israel" in title or "ukraine" in title:
            topics.add("World News")
    
    return list(topics)[:5]


# === Integration with situation ===

def get_local_news_summary(
    location: str,  # e.g., "New York", "San Francisco"
    categories: list[str] | None = None,
) -> str:
    """Get summary of local news."""
    if categories is None:
        categories = ["local", "sports", "weather"]
    
    tool = NewsTool()
    lines = [f"## News for {location}"]
    
    # Note: Real implementation would use local endpoints
    for category in categories:
        articles = tool.get_topic_news(f"{location} {category}")
        
        if articles:
            lines.append(f"\n### {category.title()}")
            for article in articles[:2]:
                lines.append(f"- {article.get_summary()}")
    
    return "\n".join(lines)


# === Singleton ===

_news_tool: NewsTool | None = None


def get_news_tool() -> NewsTool:
    global _news_tool
    
    if _news_tool is None:
        _news_tool = NewsTool()
    
    return _news_tool


def get_headlines(category: str = "") -> list[NewsArticle]:
    """Quick headline fetch."""
    return get_news_tool().get_headlines(category=category)