"""
Crime data collector for FBI Crime Data API
Collects federal crime statistics
"""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from ..base_collector import BaseCollector, DataSource
from config.settings import settings

logger = logging.getLogger(__name__)


class FBICrimeCollector(BaseCollector):
    """
    Collector for FBI Crime Data Explorer API
    
    API Docs: https://crime-data-explorer.fr.cloud.gov/pages/docApi
    """
    
    BASE_URL = "https://api.usa.gov/crime/fbi/cde"
    
    def __init__(self):
        super().__init__(DataSource.FBI)
        self.api_key = settings.fbi_crime_api_key
        
        if not self.api_key:
            logger.warning("FBI API key not configured - using mock data")
    
    async def collect(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Collect crime data from FBI API
        
        Note: FBI API provides aggregated data by agency/state, not individual incidents
        For individual incidents, we'll use synthetic data or enhance with other sources
        """
        if not self.api_key:
            return self._generate_mock_data()
        
        try:
            async with httpx.AsyncClient() as client:
                # FBI API structure (example - adjust based on actual API)
                # Get crime summaries for Florida
                url = f"{self.BASE_URL}/summarized/agencies/FL/offense"
                params = {
                    "api_key": self.api_key,
                    "from": start_date.year if start_date else datetime.now().year - 1,
                    "to": end_date.year if end_date else datetime.now().year
                }
                
                response = await client.get(url, params=params, timeout=30.0)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Fetched FBI crime data: {len(data.get('results', []))} records")
                
                return data.get("results", [])
        
        except Exception as e:
            logger.error(f"Error fetching FBI data: {e}")
            return []
    
    def validate(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate FBI crime records"""
        valid_records = []
        
        for record in records:
            # Basic validation
            if not record.get("offense"):
                continue
            
            # FBI data is aggregated, so we need location from agency
            if not record.get("data_year"):
                continue
            
            valid_records.append(record)
        
        return valid_records
    
    def transform(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform FBI data to common crime event schema
        
        Note: FBI data is aggregated. For actual incident-level data,
        we'll need to use Miami-Dade Open Data or other local sources.
        """
        transformed = []
        
        for record in records:
            # Since FBI data is aggregated, create representative records
            # based on counts (this is a simplified approach)
            event = {
                "external_id": f"FBI_{record.get('ori')}_{record.get('data_year')}_{record.get('offense')}",
                "source": self.source.value,
                "event_type": record.get("offense", "UNKNOWN"),
                "event_category": self._categorize_offense(record.get("offense", "")),
                "severity": self._determine_severity(record.get("offense", "")),
                "occurred_at": datetime(int(record.get("data_year")), 6, 15),  # Mid-year estimate
                "description": f"FBI aggregated data: {record.get('actual', 0)} incidents",
                "raw_data": record
            }
            
            # FBI data doesn't have precise locations, skip for now
            # We'll rely on Miami-Dade Open Data for geocoded incidents
            
            transformed.append(event)
        
        return transformed
    
    async def store(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Store FBI crime data (skipped for now, use local data instead)"""
        # FBI data is too aggregated for our use case
        # Return zero stats for now
        return {
            "records_inserted": 0,
            "records_updated": 0,
            "records_failed": 0
        }
    
    def _categorize_offense(self, offense: str) -> str:
        """Categorize offense type"""
        offense_lower = offense.lower()
        
        if any(word in offense_lower for word in ["murder", "assault", "robbery", "rape"]):
            return "VIOLENT"
        elif any(word in offense_lower for word in ["burglary", "larceny", "theft", "vehicle"]):
            return "PROPERTY"
        elif "drug" in offense_lower:
            return "DRUG"
        else:
            return "OTHER"
    
    def _determine_severity(self, offense: str) -> str:
        """Determine severity based on offense type"""
        offense_lower = offense.lower()
        
        if any(word in offense_lower for word in ["murder", "rape", "aggravated"]):
            return "CRITICAL"
        elif any(word in offense_lower for word in ["assault", "robbery"]):
            return "HIGH"
        elif any(word in offense_lower for word in ["burglary", "theft"]):
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_mock_data(self) -> List[Dict[str, Any]]:
        """Generate mock FBI data for testing"""
        logger.info("Generating mock FBI crime data")
        
        mock_data = [
            {
                "ori": "FL0250100",
                "data_year": 2024,
                "offense": "Aggravated Assault",
                "actual": 156,
                "cleared": 89
            },
            {
                "ori": "FL0250100",
                "data_year": 2024,
                "offense": "Robbery",
                "actual": 234,
                "cleared": 112
            },
            {
                "ori": "FL0250100",
                "data_year": 2024,
                "offense": "Burglary",
                "actual": 445,
                "cleared": 156
            }
        ]
        
        return mock_data
