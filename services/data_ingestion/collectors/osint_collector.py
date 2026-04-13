"""
News API OSINT collector
Collects news articles related to crime, safety, and incidents in Miami
"""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from ..base_collector import BaseCollector, DataSource
from config.settings import settings

logger = logging.getLogger(__name__)


class NewsAPICollector(BaseCollector):
    """
    Collector for News API - OSINT from news sources
    
    API Docs: https://newsapi.org/docs
    """
    
    BASE_URL = "https://newsapi.org/v2/everything"
    
    # Keywords for Miami crime/safety news
    KEYWORDS = [
        "Miami crime",
        "Miami shooting",
        "Miami robbery",
        "Miami assault",
        "Miami arrest",
        "Miami police",
        "Miami-Dade crime",
        "Miami Beach crime",
        "Miami safety"
    ]
    
    def __init__(self):
        super().__init__(DataSource.NEWS_API)
        self.api_key = settings.news_api_key
        
        if not self.api_key:
            logger.warning("News API key not configured")
    
    async def collect(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Collect news articles from News API"""
        if not self.api_key:
            logger.warning("API key not configured, skipping collection")
            return []
        
        # Default: last 7 days
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=7)
        
        all_articles = []
        
        try:
            async with httpx.AsyncClient() as client:
                # Search for each keyword
                for keyword in self.KEYWORDS[:3]:  # Limit to avoid rate limits
                    params = {
                        "apiKey": self.api_key,
                        "q": keyword,
                        "from": start_date.strftime("%Y-%m-%d"),
                        "to": end_date.strftime("%Y-%m-%d"),
                        "language": "en",
                        "sortBy": "publishedAt",
                        "pageSize": 20  # Max 20 per keyword (free tier)
                    }
                    
                    response = await client.get(self.BASE_URL, params=params, timeout=30.0)
                    response.raise_for_status()
                    
                    data = response.json()
                    articles = data.get("articles", [])
                    all_articles.extend(articles)
                    
                    logger.info(f"Fetched {len(articles)} articles for '{keyword}'")
            
            # Deduplicate by URL
            seen_urls = set()
            unique_articles = []
            for article in all_articles:
                url = article.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_articles.append(article)
            
            logger.info(f"Total unique articles: {len(unique_articles)}")
            return unique_articles
        
        except Exception as e:
            logger.error(f"Error fetching News API data: {e}")
            return []
    
    def validate(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate news articles"""
        valid_records = []
        
        for record in records:
            # Must have title and URL
            if not record.get("title") or not record.get("url"):
                continue
            
            # Must have published date
            if not record.get("publishedAt"):
                continue
            
            # Filter out removed/deleted articles
            if record.get("title") == "[Removed]":
                continue
            
            valid_records.append(record)
        
        logger.info(f"{len(valid_records)}/{len(records)} articles are valid")
        return valid_records
    
    def transform(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform News API data to common OSINT schema"""
        transformed = []
        
        for record in records:
            # Categorize article
            category = self._categorize_article(
                record.get("title", ""),
                record.get("description", "")
            )
            
            # Determine severity from content
            severity = self._determine_severity(
                record.get("title", ""),
                record.get("description", "")
            )
            
            event = {
                "external_id": f"NEWS_{record.get('url', '')[-50:]}",  # Last 50 chars of URL
                "source": self.source.value,
                "event_type": category,
                "event_category": "OSINT",
                "severity": severity,
                "occurred_at": self._parse_datetime(record.get("publishedAt")),
                "description": record.get("title"),
                "raw_data": record,
                "metadata": {
                    "source_name": record.get("source", {}).get("name"),
                    "author": record.get("author"),
                    "url": record.get("url"),
                    "image_url": record.get("urlToImage"),
                    "content_snippet": record.get("description")
                }
            }
            
            transformed.append(event)
        
        return transformed
    
    async def store(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Store news articles in database"""
        # TODO: Implement database storage
        logger.info(f"Would store {len(records)} news articles")
        
        return {
            "records_inserted": len(records),
            "records_updated": 0,
            "records_failed": 0
        }
    
    def _categorize_article(self, title: str, description: str) -> str:
        """Categorize news article based on content"""
        text = f"{title} {description}".lower()
        
        if any(word in text for word in ["shooting", "shot", "gunfire", "murder", "homicide"]):
            return "VIOLENT_CRIME"
        elif any(word in text for word in ["robbery", "burglary", "theft", "stolen"]):
            return "PROPERTY_CRIME"
        elif any(word in text for word in ["arrest", "arrested", "charged", "suspect"]):
            return "ARREST"
        elif any(word in text for word in ["police", "investigation", "officer"]):
            return "LAW_ENFORCEMENT"
        else:
            return "GENERAL_NEWS"
    
    def _determine_severity(self, title: str, description: str) -> str:
        """Determine severity from article content"""
        text = f"{title} {description}".lower()
        
        # Critical keywords
        if any(word in text for word in ["murder", "killed", "fatal", "dead", "homicide"]):
            return "CRITICAL"
        
        # High severity
        if any(word in text for word in ["shooting", "stabbing", "assault", "armed robbery"]):
            return "HIGH"
        
        # Medium
        if any(word in text for word in ["theft", "burglary", "arrest", "charges"]):
            return "MEDIUM"
        
        return "LOW"
    
    def _parse_datetime(self, dt_str: str) -> datetime:
        """Parse News API datetime (ISO 8601)"""
        try:
            # Format: 2024-01-27T15:30:00Z
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except Exception as e:
            logger.warning(f"Failed to parse datetime '{dt_str}': {e}")
            return datetime.utcnow()
