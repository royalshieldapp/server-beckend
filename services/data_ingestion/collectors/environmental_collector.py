"""
NASA FIRMS fire detection collector
Collects active fire hotspots from MODIS and VIIRS satellites
"""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import csv
from io import StringIO

from ..base_collector import BaseCollector, DataSource
from config.settings import settings

logger = logging.getLogger(__name__)


class NASAFIRMSCollector(BaseCollector):
    """
    Collector for NASA FIRMS (Fire Information for Resource Management System)
    
    API Docs: https://firms.modaps.eosdis.nasa.gov/api/area/
    Data: MODIS and VIIRS active fire hotspots
    """
    
    BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
    
    def __init__(self):
        super().__init__(DataSource.NASA_FIRMS)
        self.map_key = settings.nasa_firms_api_key
        
        if not self.map_key:
            logger.warning("NASA FIRMS MAP_KEY not configured")
    
    async def collect(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Collect fire hotspot data from NASA FIRMS
        
        Args:
            start_date: Not used (FIRMS API uses day_range parameter)
            end_date: Not used
            **kwargs: Can include 'source' (MODIS_NRT, VIIRS_NOAA20_NRT, VIIRS_SNPP_NRT)
        """
        if not self.map_key:
            logger.warning("MAP_KEY not configured, skipping collection")
            return []
        
        try:
            # Miami-Dade bounding box
            bbox = f"{settings.bbox_min_lng},{settings.bbox_min_lat},{settings.bbox_max_lng},{settings.bbox_max_lat}"
            
            # Data source (default: MODIS Near Real-Time)
            source = kwargs.get("source", "MODIS_NRT")
            
            # Day range (default: last 7 days)
            day_range = kwargs.get("day_range", 7)
            
            # Build URL
            url = f"{self.BASE_URL}/{self.map_key}/{source}/{bbox}/{day_range}/{datetime.now().strftime('%Y-%m-%d')}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=60.0)
                response.raise_for_status()
                
                # Parse CSV response
                csv_data = response.text
                records = self._parse_csv(csv_data)
                
                logger.info(f"Fetched {len(records)} fire hotspots from NASA FIRMS ({source})")
                return records
        
        except Exception as e:
            logger.error(f"Error fetching NASA FIRMS data: {e}")
            return []
    
    def validate(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate fire hotspot records"""
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
            
            # Must have acquisition date
            if not record.get("acq_date"):
                continue
            
            # Must have brightness (fire radiative power indicator)
            if not record.get("brightness"):
                continue
            
            valid_records.append(record)
        
        logger.info(f"{len(valid_records)}/{len(records)} fire records are valid")
        return valid_records
    
    def transform(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform NASA FIRMS data to common environmental event schema"""
        transformed = []
        
        for record in records:
            # Parse acquisition datetime
            acq_date = record.get("acq_date")
            acq_time = str(record.get("acq_time", "0000")).zfill(4)  # Ensure 4 digits
            occurred_at = self._parse_datetime(acq_date, acq_time)
            
            # Determine severity based on confidence and brightness
            severity = self._determine_severity(
                int(record.get("confidence", 0)),
                float(record.get("brightness", 0)),
                float(record.get("frp", 0))
            )
            
            event = {
                "external_id": f"FIRMS_{record.get('satellite')}_{acq_date}_{acq_time}_{record.get('latitude')}_{record.get('longitude')}",
                "source": self.source.value,
                "event_type": "FIRE",
                "event_category": "ENVIRONMENTAL",
                "severity": severity,
                "location": (float(record["latitude"]), float(record["longitude"])),
                "occurred_at": occurred_at,
                "description": self._build_description(record),
                "raw_data": record,
                "metadata": {
                    "satellite": record.get("satellite"),
                    "instrument": record.get("instrument"),
                    "confidence": int(record.get("confidence", 0)),
                    "brightness": float(record.get("brightness", 0)),
                    "bright_t31": float(record.get("bright_t31", 0)),
                    "frp": float(record.get("frp", 0)),  # Fire Radiative Power
                    "scan": float(record.get("scan", 0)),
                    "track": float(record.get("track", 0)),
                    "daynight": record.get("daynight")
                }
            }
            
            transformed.append(event)
        
        return transformed
    
    async def store(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Store fire hotspot data in database"""
        # TODO: Implement database storage using SQLAlchemy
        logger.info(f"Would store {len(records)} fire hotspot records")
        
        return {
            "records_inserted": len(records),  # Simulated
            "records_updated": 0,
            "records_failed": 0
        }
    
    def _parse_csv(self, csv_text: str) -> List[Dict[str, Any]]:
        """Parse CSV response from FIRMS API"""
        records = []
        
        try:
            csv_file = StringIO(csv_text)
            reader = csv.DictReader(csv_file)
            
            for row in reader:
                records.append(row)
        
        except Exception as e:
            logger.error(f"Error parsing CSV: {e}")
        
        return records
    
    def _parse_datetime(self, date_str: str, time_str: str) -> datetime:
        """Parse FIRMS datetime (date: YYYY-MM-DD, time: HHMM)"""
        try:
            # Combine date and time
            hour = int(time_str[:2])
            minute = int(time_str[2:])
            
            year, month, day = date_str.split("-")
            
            return datetime(int(year), int(month), int(day), hour, minute)
        
        except Exception as e:
            logger.warning(f"Failed to parse datetime '{date_str} {time_str}': {e}")
            return datetime.utcnow()
    
    def _determine_severity(self, confidence: int, brightness: float, frp: float) -> str:
        """
        Determine fire severity based on confidence, brightness, and FRP
        
        Confidence: 0-100 (percentage)
        Brightness: Temperature in Kelvin
        FRP: Fire Radiative Power in MW
        """
        # High confidence + high FRP = critical
        if confidence >= 80 and frp >= 50:
            return "CRITICAL"
        
        # High FRP or brightness
        if frp >= 30 or brightness >= 350:
            return "HIGH"
        
        # Moderate
        if confidence >= 50 or frp >= 10:
            return "MEDIUM"
        
        # Low confidence or small fire
        return "LOW"
    
    def _build_description(self, record: Dict[str, Any]) -> str:
        """Build human-readable description"""
        satellite = record.get("satellite", "Unknown")
        confidence = record.get("confidence", "Unknown")
        frp = record.get("frp", "Unknown")
        daynight = "daytime" if record.get("daynight") == "D" else "nighttime"
        
        return (
            f"Active fire detected by {satellite} satellite with {confidence}% confidence. "
            f"Fire Radiative Power: {frp} MW. Detection time: {daynight}."
        )
