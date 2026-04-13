"""
Spatial aggregation utilities
Aggregates events and POIs into H3 cells for analysis
"""
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime, timedelta
import logging

from .h3_grid import get_h3_generator

logger = logging.getLogger(__name__)


class SpatialAggregator:
    """
    Aggregates spatial data (events, POIs) into H3 cells
    for density calculation and risk scoring
    """
    
    def __init__(self):
        self.h3_gen = get_h3_generator()
    
    def aggregate_events_by_cell(
        self,
        events: List[Dict[str, Any]],
        time_window_days: int = 30
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate events into H3 cells
        
        Args:
            events: List of event dictionaries with 'location' (lat, lng) and metadata
            time_window_days: Only count events within this many days
        
        Returns:
            Dictionary mapping H3 cell ID -> aggregated metrics
        """
        cell_data = defaultdict(lambda: {
            "total_events": 0,
            "crime_events": 0,
            "fire_events": 0,
            "environmental_events": 0,
            "osint_events": 0,
            "severity_critical": 0,
            "severity_high": 0,
            "severity_medium": 0,
            "severity_low": 0,
            "recent_events_7d": 0,
            "recent_events_30d": 0,
            "event_types": defaultdict(int),
            "latest_event_date": None
        })
        
        cutoff_7d = datetime.utcnow() - timedelta(days=7)
        cutoff_30d = datetime.utcnow() - timedelta(days=time_window_days)
        
        for event in events:
            # Get H3 cell for event location
            lat, lng = event.get("location", (None, None))
            if not lat or not lng:
                continue
            
            h3_cell = self.h3_gen.get_cell_from_point(lat, lng)
            
            # Aggregate metrics
            cell = cell_data[h3_cell]
            cell["total_events"] += 1
            
            # By category
            category = event.get("event_category", "").upper()
            if "CRIME" in category:
                cell["crime_events"] += 1
            elif "FIRE" in category or "ENVIRONMENTAL" in category:
                cell["environmental_events"] += 1
            elif "OSINT" in category:
                cell["osint_events"] += 1
            
            # By severity
            severity = event.get("severity", "").lower()
            if severity == "critical":
                cell["severity_critical"] += 1
            elif severity == "high":
                cell["severity_high"] += 1
            elif severity == "medium":
                cell["severity_medium"] += 1
            else:
                cell["severity_low"] += 1
            
            # By event type
            event_type = event.get("event_type", "UNKNOWN")
            cell["event_types"][event_type] += 1
            
            # Time-based metrics
            occurred_at = event.get("occurred_at")
            if occurred_at:
                if isinstance(occurred_at, str):
                    occurred_at = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
                
                if occurred_at >= cutoff_7d:
                    cell["recent_events_7d"] += 1
                if occurred_at >= cutoff_30d:
                    cell["recent_events_30d"] += 1
                
                # Track latest event
                if not cell["latest_event_date"] or occurred_at > cell["latest_event_date"]:
                    cell["latest_event_date"] = occurred_at
        
        # Convert defaultdicts to regular dicts
        result = {}
        for cell_id, metrics in cell_data.items():
            metrics["event_types"] = dict(metrics["event_types"])
            result[cell_id] = metrics
        
        logger.info(f"Aggregated {len(events)} events into {len(result)} H3 cells")
        return result
    
    def aggregate_pois_by_cell(
        self,
        pois: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate POIs into H3 cells
        
        Args:
            pois: List of POI dictionaries with 'location' and 'poi_type'
        
        Returns:
            Dictionary mapping H3 cell ID -> POI counts by type
        """
        cell_data = defaultdict(lambda: {
            "total_pois": 0,
            "poi_types": defaultdict(int)
        })
        
        for poi in pois:
            lat, lng = poi.get("location", (None, None))
            if not lat or not lng:
                continue
            
            h3_cell = self.h3_gen.get_cell_from_point(lat, lng)
            
            cell = cell_data[h3_cell]
            cell["total_pois"] += 1
            
            poi_type = poi.get("poi_type", "unknown")
            cell["poi_types"][poi_type] += 1
        
        # Convert defaultdicts to regular dicts
        result = {}
        for cell_id, metrics in cell_data.items():
            metrics["poi_types"] = dict(metrics["poi_types"])
            result[cell_id] = metrics
        
        logger.info(f"Aggregated {len(pois)} POIs into {len(result)} H3 cells")
        return result
    
    def calculate_density_metrics(
        self,
        cell_aggregations: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate density metrics (events/POIs per km²)
        
        Args:
            cell_aggregations: Output from aggregate_events_by_cell or aggregate_pois_by_cell
        
        Returns:
            Dictionary with density metrics added
        """
        cell_area_km2 = self.h3_gen.get_grid_stats()["cell_area_km2"]
        
        result = {}
        for cell_id, metrics in cell_aggregations.items():
            densities = metrics.copy()
            
            # Calculate densities
            if "total_events" in metrics:
                densities["event_density_per_km2"] = metrics["total_events"] / cell_area_km2
                densities["crime_density_per_km2"] = metrics.get("crime_events", 0) / cell_area_km2
                densities["fire_density_per_km2"] = metrics.get("fire_events", 0) / cell_area_km2
            
            if "total_pois" in metrics:
                densities["poi_density_per_km2"] = metrics["total_pois"] / cell_area_km2
            
            result[cell_id] = densities
        
        return result
    
    def calculate_risk_scores(
        self,
        event_aggregations: Dict[str, Dict[str, Any]],
        poi_aggregations: Dict[str, Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Calculate composite risk score for each H3 cell
        
        Risk score is based on:
        - Event frequency (recent events weighted more)
        - Event severity (critical > high > medium > low)
        - Event types (violent crime weighted more)
        - POI density (high traffic areas = higher risk)
        
        Args:
            event_aggregations: Event metrics by cell
            poi_aggregations: POI metrics by cell (optional)
        
        Returns:
            Dictionary mapping H3 cell ID -> risk score (0-100)
        """
        risk_scores = {}
        
        for cell_id, metrics in event_aggregations.items():
            score = 0.0
            
            # Severity weighting
            score += metrics.get("severity_critical", 0) * 10.0
            score += metrics.get("severity_high", 0) * 5.0
            score += metrics.get("severity_medium", 0) * 2.0
            score += metrics.get("severity_low", 0) * 1.0
            
            # Recent activity boost
            score += metrics.get("recent_events_7d", 0) * 3.0
            score += metrics.get("recent_events_30d", 0) * 1.5
            
            # Crime type weighting
            event_types = metrics.get("event_types", {})
            if "VIOLENT_CRIME" in event_types or "VIOLENT" in str(event_types):
                score += event_types.get("VIOLENT_CRIME", 0) * 5.0
            
            # POI density factor (optional)
            if poi_aggregations and cell_id in poi_aggregations:
                poi_count = poi_aggregations[cell_id].get("total_pois", 0)
                # More POIs = more people = potentially higher risk
                score += poi_count * 0.1
            
            # Normalize to 0-100 scale (cap at 100)
            risk_scores[cell_id] = min(score, 100.0)
        
        logger.info(f"Calculated risk scores for {len(risk_scores)} cells")
        return risk_scores


# Singleton instance
_spatial_aggregator = None

def get_spatial_aggregator() -> SpatialAggregator:
    """Get singleton spatial aggregator instance"""
    global _spatial_aggregator
    if _spatial_aggregator is None:
        _spatial_aggregator = SpatialAggregator()
    return _spatial_aggregator
