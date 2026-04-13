"""
Feature Engineering for ML Models
Extracts and transforms features from spatial and temporal data
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from services.geospatial import get_h3_generator, get_spatial_aggregator

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Creates ML-ready features from raw event and POI data
    
    Feature Categories:
    1. Temporal: Day of week, hour, time since last event
    2. Spatial: H3 cell features, neighbor statistics
    3. Historical: Event counts, densities, trends
    4. Environmental: POI counts, land use patterns
    5. Derived: Risk scores, clustering metrics
    """
    
    def __init__(self):
        self.h3_gen = get_h3_generator()
        self.aggregator = get_spatial_aggregator()
    
    def create_training_dataset(
        self,
        events: List[Dict[str, Any]],
        pois: List[Dict[str, Any]] = None,
        lookback_days: int = 90
    ) -> pd.DataFrame:
        """
        Create complete feature dataset for ML training
        
        Args:
            events: Historical events
            pois: Points of interest
            lookback_days: Days of history to include
        
        Returns:
            DataFrame with features for each H3 cell
        """
        logger.info("Engineering features for ML training...")
        
        # Aggregate events by H3 cell
        event_metrics = self.aggregator.aggregate_events_by_cell(events, lookback_days)
        
        # Aggregate POIs if provided
        poi_metrics = None
        if pois:
            poi_metrics = self.aggregator.aggregate_pois_by_cell(pois)
        
        # Calculate densities
        density_metrics = self.aggregator.calculate_density_metrics(event_metrics)
        
        # Calculate risk scores (target variable)
        risk_scores = self.aggregator.calculate_risk_scores(event_metrics, poi_metrics)
        
        # Build feature rows
        rows = []
        for h3_cell in event_metrics.keys():
            features = self._extract_cell_features(
                h3_cell,
                event_metrics,
                poi_metrics,
                density_metrics
            )
            features["h3_cell"] = h3_cell
            features["risk_score"] = risk_scores.get(h3_cell, 0.0)
            rows.append(features)
        
        df = pd.DataFrame(rows)
        
        logger.info(f"Created dataset with {len(df)} cells and {len(df.columns)} features")
        return df
    
    def _extract_cell_features(
        self,
        h3_cell: str,
        event_metrics: Dict[str, Dict],
        poi_metrics: Dict[str, Dict] = None,
        density_metrics: Dict[str, Dict] = None
    ) -> Dict[str, float]:
        """Extract all features for a single H3 cell"""
        features = {}
        
        # Event metrics
        cell_events = event_metrics.get(h3_cell, {})
        features["total_events"] = cell_events.get("total_events", 0)
        features["crime_events"] = cell_events.get("crime_events", 0)
        features["fire_events"] = cell_events.get("fire_events", 0)
        features["environmental_events"] = cell_events.get("environmental_events", 0)
        features["osint_events"] = cell_events.get("osint_events", 0)
        
        # Severity distribution
        features["severity_critical"] = cell_events.get("severity_critical", 0)
        features["severity_high"] = cell_events.get("severity_high", 0)
        features["severity_medium"] = cell_events.get("severity_medium", 0)
        features["severity_low"] = cell_events.get("severity_low", 0)
        
        # Temporal features
        features["recent_events_7d"] = cell_events.get("recent_events_7d", 0)
        features["recent_events_30d"] = cell_events.get("recent_events_30d", 0)
        
        # Recency ratio (recent vs total)
        total = features["total_events"]
        if total > 0:
            features["recency_ratio_7d"] = features["recent_events_7d"] / total
            features["recency_ratio_30d"] = features["recent_events_30d"] / total
        else:
            features["recency_ratio_7d"] = 0.0
            features["recency_ratio_30d"] = 0.0
        
        # Density features
        if density_metrics and h3_cell in density_metrics:
            densities = density_metrics[h3_cell]
            features["event_density_km2"] = densities.get("event_density_per_km2", 0.0)
            features["crime_density_km2"] = densities.get("crime_density_per_km2", 0.0)
        else:
            features["event_density_km2"] = 0.0
            features["crime_density_km2"] = 0.0
        
        # POI features
        if poi_metrics and h3_cell in poi_metrics:
            cell_pois = poi_metrics[h3_cell]
            features["total_pois"] = cell_pois.get("total_pois", 0)
            
            # POI type counts
            poi_types = cell_pois.get("poi_types", {})
            features["pois_schools"] = poi_types.get("schools", 0)
            features["pois_hospitals"] = poi_types.get("hospitals", 0)
            features["pois_police"] = poi_types.get("police_stations", 0)
            features["pois_banks"] = poi_types.get("banks", 0)
            features["pois_bars"] = poi_types.get("bars", 0)
            features["pois_nightclubs"] = poi_types.get("nightclubs", 0)
        else:
            features["total_pois"] = 0
            features["pois_schools"] = 0
            features["pois_hospitals"] = 0
            features["pois_police"] = 0
            features["pois_banks"] = 0
            features["pois_bars"] = 0
            features["pois_nightclubs"] = 0
        
        # Neighbor features (spatial autocorrelation)
        neighbor_features = self._extract_neighbor_features(h3_cell, event_metrics)
        features.update(neighbor_features)
        
        # Derived features
        features["violence_ratio"] = self._calculate_violence_ratio(cell_events)
        features["severity_index"] = self._calculate_severity_index(cell_events)
        
        return features
    
    def _extract_neighbor_features(
        self,
        h3_cell: str,
        event_metrics: Dict[str, Dict]
    ) -> Dict[str, float]:
        """
        Calculate features from neighboring cells
        Captures spatial autocorrelation
        """
        neighbors = self.h3_gen.get_neighbors(h3_cell, ring=1)
        neighbors.remove(h3_cell)  # Exclude self
        
        neighbor_events = []
        neighbor_crimes = []
        neighbor_critical = []
        
        for neighbor in neighbors:
            if neighbor in event_metrics:
                metrics = event_metrics[neighbor]
                neighbor_events.append(metrics.get("total_events", 0))
                neighbor_crimes.append(metrics.get("crime_events", 0))
                neighbor_critical.append(metrics.get("severity_critical", 0))
        
        return {
            "neighbor_avg_events": np.mean(neighbor_events) if neighbor_events else 0.0,
            "neighbor_max_events": np.max(neighbor_events) if neighbor_events else 0.0,
            "neighbor_avg_crimes": np.mean(neighbor_crimes) if neighbor_crimes else 0.0,
            "neighbor_critical_count": np.sum(neighbor_critical) if neighbor_critical else 0.0
        }
    
    def _calculate_violence_ratio(self, cell_events: Dict) -> float:
        """Ratio of violent crimes to total crimes"""
        total_crimes = cell_events.get("crime_events", 0)
        if total_crimes == 0:
            return 0.0
        
        event_types = cell_events.get("event_types", {})
        violent_count = sum(
            count for event_type, count in event_types.items()
            if "VIOLENT" in event_type.upper() or "ASSAULT" in event_type.upper()
        )
        
        return violent_count / total_crimes
    
    def _calculate_severity_index(self, cell_events: Dict) -> float:
        """
        Weighted severity index (0-10)
        Higher = more severe events
        """
        critical = cell_events.get("severity_critical", 0)
        high = cell_events.get("severity_high", 0)
        medium = cell_events.get("severity_medium", 0)
        low = cell_events.get("severity_low", 0)
        
        total = critical + high + medium + low
        if total == 0:
            return 0.0
        
        weighted_sum = critical * 10 + high * 6 + medium * 3 + low * 1
        return weighted_sum / total
    
    def prepare_prediction_features(
        self,
        h3_cell: str,
        current_events: List[Dict[str, Any]],
        current_pois: List[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Prepare features for a single cell prediction
        
        Args:
            h3_cell: H3 cell ID to predict for
            current_events: Recent events
            current_pois: Current POIs
        
        Returns:
            Feature dictionary ready for model inference
        """
        # Aggregate current data
        event_metrics = self.aggregator.aggregate_events_by_cell(current_events)
        
        poi_metrics = None
        if current_pois:
            poi_metrics = self.aggregator.aggregate_pois_by_cell(current_pois)
        
        density_metrics = self.aggregator.calculate_density_metrics(event_metrics)
        
        # Extract features
        features = self._extract_cell_features(
            h3_cell,
            event_metrics,
            poi_metrics,
            density_metrics
        )
        
        return features


# Singleton
_feature_engineer = None

def get_feature_engineer() -> FeatureEngineer:
    """Get singleton feature engineer instance"""
    global _feature_engineer
    if _feature_engineer is None:
        _feature_engineer = FeatureEngineer()
    return _feature_engineer
