"""
Base data collector interface
All data source collectors inherit from this class
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class DataSource(str, Enum):
    """Data source enumeration"""
    FBI = "FBI"
    MIAMI_OPEN_DATA = "MIAMI_OPEN_DATA"
    NASA_FIRMS = "NASA_FIRMS"
    NOAA = "NOAA"
    OSM = "OSM"
    REDDIT = "REDDIT"
    NEWS_API = "NEWS_API"
    TWITTER = "TWITTER"
    USER_REPORT = "USER_REPORT"


class CollectionStatus(str, Enum):
    """Collection job status"""
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class BaseCollector(ABC):
    """
    Abstract base class for all data collectors
    
    Each collector must implement:
    - collect(): Fetch data from source
    - validate(): Validate fetched data
    - transform(): Transform to common schema
    - store(): Store in database
    """
    
    def __init__(self, source: DataSource):
        self.source = source
        self.logger = logging.getLogger(f"{__name__}.{source.value}")
    
    @abstractmethod
    async def collect(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Collect raw data from source
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            **kwargs: Additional source-specific parameters
        
        Returns:
            List of raw data records
        """
        pass
    
    @abstractmethod
    def validate(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate collected data
        
        Args:
            records: Raw data records
        
        Returns:
            Valid records only
        """
        pass
    
    @abstractmethod
    def transform(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform data to common schema
        
        Args:
            records: Validated records
        
        Returns:
            Transformed records ready for storage
        """
        pass
    
    @abstractmethod
    async def store(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Store transformed data in database
        
        Args:
            records: Transformed records
        
        Returns:
            Statistics: inserted, updated, failed counts
        """
        pass
    
    async def run(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute full collection pipeline
        
        Returns:
            Collection statistics and status
        """
        started_at = datetime.utcnow()
        stats = {
            "source": self.source.value,
            "started_at": started_at,
            "status": CollectionStatus.SUCCESS,
            "records_fetched": 0,
            "records_inserted": 0,
            "records_updated": 0,
            "records_failed": 0,
            "error_message": None
        }
        
        try:
            self.logger.info(f"Starting data collection from {self.source.value}")
            
            # Step 1: Collect
            raw_records = await self.collect(start_date, end_date, **kwargs)
            stats["records_fetched"] = len(raw_records)
            self.logger.info(f"Fetched {len(raw_records)} records")
            
            if not raw_records:
                self.logger.warning("No records fetched")
                return stats
            
            # Step 2: Validate
            valid_records = self.validate(raw_records)
            self.logger.info(f"{len(valid_records)} valid records")
            
            # Step 3: Transform
            transformed_records = self.transform(valid_records)
            self.logger.info(f"Transformed {len(transformed_records)} records")
            
            # Step 4: Store
            storage_stats = await self.store(transformed_records)
            stats.update(storage_stats)
            
            # Determine final status
            if stats["records_failed"] > 0:
                stats["status"] = CollectionStatus.PARTIAL
            
            completed_at = datetime.utcnow()
            stats["completed_at"] = completed_at
            stats["duration_seconds"] = (completed_at - started_at).total_seconds()
            
            self.logger.info(
                f"Collection completed: {stats['records_inserted']} inserted, "
                f"{stats['records_updated']} updated, {stats['records_failed']} failed"
            )
            
        except Exception as e:
            stats["status"] = CollectionStatus.FAILED
            stats["error_message"] = str(e)
            self.logger.error(f"Collection failed: {e}", exc_info=True)
        
        return stats
    
    def normalize_coordinates(self, lat: float, lng: float) -> Optional[tuple]:
        """
        Normalize and validate coordinates
        
        Args:
            lat: Latitude
            lng: Longitude
        
        Returns:
            (lat, lng) tuple if valid, None otherwise
        """
        try:
            lat = float(lat)
            lng = float(lng)
            
            # Validate ranges
            if not (-90 <= lat <= 90):
                self.logger.warning(f"Invalid latitude: {lat}")
                return None
            
            if not (-180 <= lng <= 180):
                self.logger.warning(f"Invalid longitude: {lng}")
                return None
            
            return (lat, lng)
        
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Coordinate normalization error: {e}")
            return None
