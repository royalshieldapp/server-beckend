"""
Miami-Dade Open Data crime collector
Uses Socrata API to collect geocoded crime incidents
"""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from ..base_collector import BaseCollector, DataSource
from config.settings import settings

logger = logging.getLogger(__name__)


class MiamiDadeCrimeCollector(BaseCollector):
    """
    Collector for Miami-Dade Open Data Portal (Socrata)
    
    Datasets:
    - Crime Incidents: https://opendata.miamidade.gov/Public-Safety/Crime-Incidents/3njt-7w7c
    
    API Docs: https://dev.socrata.com/
    """
    BASE_URL = "https://opendata.miamidade.gov/resource"
    CRIME_DATASET_ID = "3njt-7w7c"  # Crime Incidents dataset
    
    def __init__(self):
        super().__init__(DataSource.MIAMI_OPEN_DATA)
        self.app_token = settings.miami_dade_app_token
        
        if not self.app_token:
            logger.warning("Miami-Dade App Token not configured - using mock data")
    
    async def collect(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Collect crime data from Miami-Dade Open Data"""
        if not self.app_token:
            return self._generate_mock_data()
        
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.BASE_URL}/{self.CRIME_DATASET_ID}.json"
                
                # Build SoQL query
                where_clause = self._build_where_clause(start_date, end_date)
                
                params = {
                    "$where": where_clause,
                    "$limit": 10000,  # Adjust based on data volume
                    "$offset": 0,
                    "$order": "incident_datetime DESC"
                }
                
                headers = {
                    "X-App-Token": self.app_token
                }
                
                response = await client.get(url, params=params, headers=headers, timeout=60.0)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Fetched {len(data)} Miami-Dade crime records")
                
                return data
        
        except Exception as e:
            logger.error(f"Error fetching Miami-Dade data: {e}")
            return []
    
    def validate(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate Miami-Dade crime records"""
        valid_records = []
        
        for record in records:
            # Must have coordinates
            lat = record.get("latitude")
            lng = record.get("longitude")
            
            if not lat or not lng:
                continue
            
            # Normalize coordinates
            coords = self.normalize_coordinates(lat, lng)
            if not coords:
                continue
            
            # Must have incident date
            if not record.get("incident_datetime"):
                continue
            
            # Must have offense type
            if not record.get("offense"):
                continue
            
            valid_records.append(record)
        
        logger.info(f"{len(valid_records)}/{len(records)} records are valid")
        return valid_records
    
    def transform(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform Miami-Dade data to common crime event schema"""
        transformed = []
        
        for record in records:
            event = {
                "external_id": f"MIAMI_{record.get('incident_id', '')}",
                "source": self.source.value,
                "event_type": record.get("offense", "UNKNOWN"),
                "event_category": self._categorize_offense(record.get("offense", "")),
                "severity": self._determine_severity(record.get("offense", "")),
                "location": (float(record["latitude"]), float(record["longitude"])),
                "address": record.get("address"),
                "occurred_at": self._parse_datetime(record.get("incident_datetime")),
                "description": f"{record.get('offense')} at {record.get('address')}",
                "raw_data": record
            }
            
            transformed.append(event)
        
        return transformed
    
    async def store(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Store Miami-Dade crime data in database"""
        # TODO: Implement database storage using SQLAlchemy
        # For now, return zero stats (will implement with ORM models)
        
        logger.info(f"Would store {len(records)} Miami-Dade crime records")
        
        return {
            "records_inserted": len(records),  # Simulated
            "records_updated": 0,
            "records_failed": 0
        }
    
    def _build_where_clause(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> str:
        """Build SoQL WHERE clause for date filtering"""
        if not start_date and not end_date:
            # Default: last 30 days
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
        elif not start_date:
            start_date = end_date - timedelta(days=30)
        elif not end_date:
            end_date = datetime.utcnow()
        
        # SoQL date format: '2024-01-01T00:00:00'
        return (
            f"incident_datetime >= '{start_date.isoformat()}' AND "
            f"incident_datetime <= '{end_date.isoformat()}'"
        )
    
    def _categorize_offense(self, offense: str) -> str:
        """Categorize offense type"""
        offense_lower = offense.lower()
        
        if any(word in offense_lower for word in ["murder", "assault", "battery", "robbery", "rape", "homicide"]):
            return "VIOLENT"
        elif any(word in offense_lower for word in ["burglary", "larceny", "theft", "stolen", "shoplifting"]):
            return "PROPERTY"
        elif any(word in offense_lower for word in ["drug", "narcotic", "marijuana", "cocaine"]):
            return "DRUG"
        elif any(word in offense_lower for word in ["vandalism", "trespass", "disorderly"]):
            return "DISORDER"
        else:
            return "OTHER"
    
    def _determine_severity(self, offense: str) -> str:
        """Determine severity based on offense type"""
        offense_lower = offense.lower()
        
        if any(word in offense_lower for word in ["murder", "homicide", "rape", "armed robbery"]):
            return "CRITICAL"
        elif any(word in offense_lower for word in ["aggravated", "assault", "battery", "robbery"]):
            return "HIGH"
        elif any(word in offense_lower for word in ["burglary", "theft", "drug"]):
            return "MEDIUM"
        else:
            return "LOW"
    
    def _parse_datetime(self, dt_str: str) -> datetime:
        """Parse Socrata datetime string"""
        try:
            # Socrata format: "2024-01-15T14:30:00.000"
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except Exception as e:
            logger.warning(f"Failed to parse datetime '{dt_str}': {e}")
            return datetime.utcnow()
    
    def _generate_mock_data(self) -> List[Dict[str, Any]]:
        """Generate mock Miami-Dade data for testing"""
        logger.info("Generating mock Miami-Dade crime data")
        
        # Mock data with realistic Miami-Dade coordinates
        mock_data = [
            {
                "incident_id": "202401150001",
                "incident_datetime": "2024-01-15T14:30:00.000",
                "offense": "BURGLARY - RESIDENCE",
                "address": "123 NW 1ST ST, MIAMI, FL",
                "latitude": "25.7817",
                "longitude": "-80.1918"
            },
            {
                "incident_id": "202401150002",
                "incident_datetime": "2024-01-15T18:45:00.000",
                "offense": "ROBBERY - STREET",
                "address": "456 BISCAYNE BLVD, MIAMI, FL",
                "latitude": "25.7743",
                "longitude": "-80.1937"
            },
            {
                "incident_id": "202401160001",
                "incident_datetime": "2024-01-16T22:15:00.000",
                "offense": "ASSAULT - AGGRAVATED",
                "address": "789 OCEAN DR, MIAMI BEACH, FL",
                "latitude": "25.7814",
                "longitude": "-80.1300"
            },
            {
                "incident_id": "202401170001",
                "incident_datetime": "2024-01-17T03:30:00.000",
                "offense": "THEFT - AUTO",
                "address": "321 SW 8TH ST, MIAMI, FL",
                "latitude": "25.7663",
                "longitude": "-80.2103"
            },
            {
                "incident_id": "202401170002",
                "incident_datetime": "2024-01-17T11:00:00.000",
                "offense": "DRUG POSSESSION",
                "address": "654 NE 2ND AVE, MIAMI, FL",
                "latitude": "25.7801",
                "longitude": "-80.1904"
            }
        ]
        
        return mock_data
