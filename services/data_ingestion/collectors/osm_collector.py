"""
OpenStreetMap data collector
Collects Points of Interest, buildings, and road networks
"""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import asyncio

from ..base_collector import BaseCollector, DataSource
from config.settings import settings

logger = logging.getLogger(__name__)


class OpenStreetMapCollector(BaseCollector):
    """
    Collector for OpenStreetMap data via Overpass API
    
    API Docs: https://wiki.openstreetmap.org/wiki/Overpass_API
    No API key required
    """
    
    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    
    # POI categories of interest for risk analysis
    POI_CATEGORIES = {
        "schools": '["amenity"="school"]',
        "hospitals": '["amenity"="hospital"]',
        "police_stations": '["amenity"="police"]',
        "banks": '["amenity"="bank"]',
        "atms": '["amenity"="atm"]',
        "bars": '["amenity"="bar"]',
        "nightclubs": '["amenity"="nightclub"]',
        "parking": '["amenity"="parking"]',
        "gas_stations": '["amenity"="fuel"]',
        "shops": '["shop"]'
    }
    
    def __init__(self):
        super().__init__(DataSource.OSM)
    
    async def collect(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Collect POI data from OpenStreetMap
        
        Note: OSM data is not time-based, so dates are ignored
        """
        all_pois = []
        
        # Miami-Dade bounding box
        bbox = f"{settings.bbox_min_lat},{settings.bbox_min_lng},{settings.bbox_max_lat},{settings.bbox_max_lng}"
        
        try:
            async with httpx.AsyncClient() as client:
                # Collect each POI category
                for category, filter_string in self.POI_CATEGORIES.items():
                    query = self._build_overpass_query(bbox, filter_string)
                    
                    response = await client.post(
                        self.OVERPASS_URL,
                        data={"data": query},
                        timeout=60.0
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    elements = data.get("elements", [])
                    
                    # Add category to each element
                    for element in elements:
                        element["poi_category"] = category
                    
                    all_pois.extend(elements)
                    logger.info(f"Fetched {len(elements)} {category} from OSM")
                    
                    # Rate limiting - OSM asks for 1 second between requests
                    await asyncio.sleep(1)
            
            logger.info(f"Total POIs collected: {len(all_pois)}")
            return all_pois
        
        except Exception as e:
            logger.error(f"Error fetching OSM data: {e}")
            return []
    
    def validate(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate OSM POI records"""
        valid_records = []
        
        for record in records:
            # Must have ID
            if not record.get("id"):
                continue
            
            # Must have coordinates
            lat = record.get("lat")
            lon = record.get("lon")
            
            # For ways/areas, use center point
            if not lat or not lon:
                if record.get("center"):
                    lat = record["center"].get("lat")
                    lon = record["center"].get("lon")
            
            if not lat or not lon:
                continue
            
            # Normalize coordinates
            coords = self.normalize_coordinates(lat, lon)
            if not coords:
                continue
            
            valid_records.append(record)
        
        logger.info(f"{len(valid_records)}/{len(records)} POIs are valid")
        return valid_records
    
    def transform(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform OSM data to common POI schema"""
        transformed = []
        
        for record in records:
            # Get coordinates
            lat = record.get("lat")
            lon = record.get("lon")
            
            # For ways, use center
            if not lat or not lon:
                if record.get("center"):
                    lat = record["center"]["lat"]
                    lon = record["center"]["lon"]
            
            # Extract tags
            tags = record.get("tags", {})
            
            poi = {
                "external_id": f"OSM_{record.get('id')}",
                "source": self.source.value,
                "poi_type": record.get("poi_category", "unknown"),
                "name": tags.get("name", "Unnamed"),
                "location": (float(lat), float(lon)),
                "raw_data": record,
                "metadata": {
                    "osm_type": record.get("type"),  # node, way, relation
                    "amenity": tags.get("amenity"),
                    "shop": tags.get("shop"),
                    "address": self._extract_address(tags),
                    "phone": tags.get("phone"),
                    "website": tags.get("website"),
                    "opening_hours": tags.get("opening_hours")
                }
            }
            
            transformed.append(poi)
        
        return transformed
    
    async def store(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Store OSM POI data in database"""
        # TODO: Implement database storage
        logger.info(f"Would store {len(records)} OSM POIs")
        
        return {
            "records_inserted": len(records),
            "records_updated": 0,
            "records_failed": 0
        }
    
    def _build_overpass_query(self, bbox: str, filter_string: str) -> str:
        """
        Build Overpass QL query
        
        Args:
            bbox: "min_lat,min_lon,max_lat,max_lon"
            filter_string: OSM filter like '["amenity"="school"]'
        """
        query = f"""
        [out:json][timeout:60];
        (
          node{filter_string}({bbox});
          way{filter_string}({bbox});
          relation{filter_string}({bbox});
        );
        out center;
        """
        return query
    
    def _extract_address(self, tags: Dict[str, str]) -> Optional[str]:
        """Extract address from OSM tags"""
        address_parts = []
        
        if tags.get("addr:housenumber"):
            address_parts.append(tags["addr:housenumber"])
        if tags.get("addr:street"):
            address_parts.append(tags["addr:street"])
        if tags.get("addr:city"):
            address_parts.append(tags["addr:city"])
        if tags.get("addr:postcode"):
            address_parts.append(tags["addr:postcode"])
        
        if address_parts:
            return ", ".join(address_parts)
        
        return None
