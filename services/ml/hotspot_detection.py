"""
DBSCAN Hotspot Detector
Identifies crime/risk hotspots using density-based clustering
"""
from sklearn.cluster import DBSCAN
import numpy as np
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging

from services.geospatial import get_h3_generator

logger = logging.getLogger(__name__)


class HotspotDetector:
    """
    Detects geographic hotspots using DBSCAN clustering algorithm
    
    DBSCAN (Density-Based Spatial Clustering of Applications with Noise)
    - Finds areas with high event density
    - Automatically determines number of clusters
    - Identifies outliers (noise points)
    - Works well with geographic data
    """
    
    def __init__(
        self,
        eps_meters: float = 500.0,
        min_samples: int = 5,
        severity_weights: Dict[str, float] = None
    ):
        """
        Initialize hotspot detector
        
        Args:
            eps_meters: Maximum distance between points in a cluster (meters)
            min_samples: Minimum points needed to form a cluster
            severity_weights: Weight multiplier for event severity
        """
        self.eps_meters = eps_meters
        self.min_samples = min_samples
        
        # Default severity weights (events get duplicated based on severity)
        self.severity_weights = severity_weights or {
            "CRITICAL": 5.0,
            "HIGH": 3.0,
            "MEDIUM": 2.0,
            "LOW": 1.0
        }
        
        # Convert meters to approximate degrees (rough estimate for latitude)
        # 1 degree latitude ≈ 111km
        self.eps_degrees = eps_meters / 111000.0
        
        logger.info(f"Hotspot detector initialized: eps={eps_meters}m, min_samples={min_samples}")
    
    def detect_hotspots(
        self,
        events: List[Dict[str, Any]],
        time_window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Detect hotspots from event data
        
        Args:
            events: List of events with location and metadata
            time_window_days: Only consider events within this window
        
        Returns:
            Dictionary with hotspot clusters and statistics
        """
        # Filter events by time window
        cutoff_date = datetime.utcnow() - timedelta(days=time_window_days)
        recent_events = []
        
        for event in events:
            occurred_at = event.get("occurred_at")
            if occurred_at:
                if isinstance(occurred_at, str):
                    occurred_at = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
                
                if occurred_at >= cutoff_date:
                    recent_events.append(event)
        
        if len(recent_events) < self.min_samples:
            logger.warning(f"Not enough events ({len(recent_events)}) for clustering")
            return {
                "hotspots": [],
                "total_events": len(events),
                "recent_events": len(recent_events),
                "clusters_found": 0,
                "noise_points": 0
            }
        
        # Prepare data for DBSCAN
        coordinates, weights, event_indices = self._prepare_data(recent_events)
        
        # Run DBSCAN
        dbscan = DBSCAN(
            eps=self.eps_degrees,
            min_samples=self.min_samples,
            metric='haversine',  # Great circle distance
            algorithm='ball_tree'
        )
        
        # Convert to radians for haversine
        coords_radians = np.radians(coordinates)
        labels = dbscan.fit_predict(coords_radians, sample_weight=weights)
        
        # Analyze clusters
        hotspots = self._analyze_clusters(
            coordinates,
            labels,
            event_indices,
            recent_events
        )
        
        # Calculate statistics
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)
        
        result = {
            "hotspots": hotspots,
            "total_events": len(events),
            "recent_events": len(recent_events),
            "clusters_found": n_clusters,
            "noise_points": n_noise,
            "eps_meters": self.eps_meters,
            "time_window_days": time_window_days
        }
        
        logger.info(f"Detected {n_clusters} hotspots from {len(recent_events)} events")
        return result
    
    def _prepare_data(
        self,
        events: List[Dict[str, Any]]
    ) -> Tuple[np.ndarray, np.ndarray, List[int]]:
        """
        Prepare event data for DBSCAN
        
        Returns:
            coordinates: (N, 2) array of [lat, lng]
            weights: (N,) array of severity weights
            event_indices: Original event indices
        """
        coordinates = []
        weights = []
        event_indices = []
        
        for idx, event in enumerate(events):
            lat, lng = event.get("location", (None, None))
            if not lat or not lng:
                continue
            
            # Get weight based on severity
            severity = event.get("severity", "LOW").upper()
            weight = self.severity_weights.get(severity, 1.0)
            
            coordinates.append([lat, lng])
            weights.append(weight)
            event_indices.append(idx)
        
        return (
            np.array(coordinates),
            np.array(weights),
            event_indices
        )
    
    def _analyze_clusters(
        self,
        coordinates: np.ndarray,
        labels: np.ndarray,
        event_indices: List[int],
        events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze detected clusters and compute metrics
        
        Returns:
            List of hotspot dictionaries with statistics
        """
        hotspots = []
        h3_gen = get_h3_generator()
        
        # Group by cluster label
        unique_labels = set(labels)
        
        for cluster_id in unique_labels:
            if cluster_id == -1:  # Skip noise points
                continue
            
            # Get events in this cluster
            cluster_mask = labels == cluster_id
            cluster_coords = coordinates[cluster_mask]
            cluster_event_indices = [event_indices[i] for i, mask in enumerate(cluster_mask) if mask]
            cluster_events = [events[i] for i in cluster_event_indices]
            
            # Calculate cluster center (mean of coordinates)
            center_lat = float(np.mean(cluster_coords[:, 0]))
            center_lng = float(np.mean(cluster_coords[:, 1]))
            
            # Calculate cluster radius (max distance from center)
            distances = np.sqrt(
                (cluster_coords[:, 0] - center_lat)**2 +
                (cluster_coords[:, 1] - center_lng)**2
            ) * 111000  # Convert to meters
            radius_meters = float(np.max(distances))
            
            # Analyze event types and severities
            event_types = {}
            severities = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            
            for event in cluster_events:
                event_type = event.get("event_type", "UNKNOWN")
                event_types[event_type] = event_types.get(event_type, 0) + 1
                
                severity = event.get("severity", "LOW").upper()
                if severity in severities:
                    severities[severity] += 1
            
            # Calculate risk score for hotspot
            risk_score = self._calculate_hotspot_risk(
                len(cluster_events),
                severities,
                radius_meters
            )
            
            # Get H3 cell for center
            h3_cell = h3_gen.get_cell_from_point(center_lat, center_lng)
            
            hotspot = {
                "hotspot_id": int(cluster_id),
                "center": {
                    "lat": center_lat,
                    "lng": center_lng
                },
                "h3_cell": h3_cell,
                "radius_meters": radius_meters,
                "event_count": len(cluster_events),
                "event_types": event_types,
                "severities": severities,
                "risk_score": risk_score,
                "risk_level": self._get_risk_level(risk_score)
            }
            
            hotspots.append(hotspot)
        
        # Sort by risk score
        hotspots.sort(key=lambda x: x["risk_score"], reverse=True)
        
        return hotspots
    
    def _calculate_hotspot_risk(
        self,
        event_count: int,
        severities: Dict[str, int],
        radius_meters: float
    ) -> float:
        """
        Calculate risk score for a hotspot
        
        Factors:
        - Event density (events per km²)
        - Severity distribution
        - Cluster compactness
        """
        # Event density
        area_km2 = (np.pi * (radius_meters/1000)**2)
        if area_km2 < 0.01:  # Minimum area to avoid division by zero
            area_km2 = 0.01
        
        density = event_count / area_km2
        
        # Severity score
        severity_score = (
            severities.get("CRITICAL", 0) * 10.0 +
            severities.get("HIGH", 0) * 5.0 +
            severities.get("MEDIUM", 0) * 2.0 +
            severities.get("LOW", 0) * 1.0
        )
        
        # Compactness bonus (smaller radius = more concentrated = higher risk)
        compactness_factor = max(0.5, 1.0 - (radius_meters / 1000))
        
        # Composite risk score
        risk = (density * 2.0 + severity_score) * compactness_factor
        
        # Normalize to 0-100
        return min(risk * 2, 100.0)
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to categorical level"""
        if risk_score >= 75:
            return "CRITICAL"
        elif risk_score >= 50:
            return "HIGH"
        elif risk_score >= 25:
            return "MEDIUM"
        else:
            return "LOW"


# Singleton instance
_hotspot_detector = None

def get_hotspot_detector() -> HotspotDetector:
    """Get singleton hotspot detector instance"""
    global _hotspot_detector
    if _hotspot_detector is None:
        _hotspot_detector = HotspotDetector()
    return _hotspot_detector
