"""
Risk Map API Routes
Endpoints for retrieving risk zone data and heatmaps
"""
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel, Field

from services.geospatial import get_h3_generator, get_spatial_aggregator
from services.ml import get_risk_predictor

router = APIRouter(prefix="/api/v1", tags=["Risk Maps"])


# Response Models
class RiskZone(BaseModel):
    """Individual risk zone data"""
    h3_cell: str
    center: List[float] = Field(..., description="[lat, lng]")
    boundary: List[List[float]] = Field(..., description="Hexagon vertices [[lat, lng], ...]")
    risk_score: float = Field(..., ge=0, le=100)
    risk_level: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL")
    event_count: int = Field(..., ge=0)
    crime_count: int = Field(..., ge=0)
    fire_count: int = Field(..., ge=0)
    recent_events_7d: int = Field(..., ge=0)
    recent_events_30d: int = Field(..., ge=0)


class RiskMapResponse(BaseModel):
    """Risk map heatmap data"""
    type: str = "FeatureCollection"
    features: List[dict]
    metadata: dict


class ZoneDetails(BaseModel):
    """Detailed zone information"""
    h3_cell: str
    center: List[float]
    risk_score: float
    risk_level: str
    statistics: dict
    recent_events: List[dict]
    trends: dict


@router.get("/risk-map", response_model=RiskMapResponse)
async def get_risk_map(
    bbox_min_lat: float = Query(..., description="Minimum latitude"),
    bbox_min_lng: float = Query(..., description="Minimum longitude"),
    bbox_max_lat: float = Query(..., description="Maximum latitude"),
    bbox_max_lng: float = Query(..., description="Maximum longitude"),
    resolution: int = Query(9, ge=7, le=12, description="H3 resolution"),
    date_filter: Optional[date] = Query(None, description="Optional: filter by date")
):
    """
    Get risk heatmap for a bounding box
    
    Returns GeoJSON FeatureCollection with risk zones
    """
    try:
        h3_gen = get_h3_generator()
        aggregator = get_spatial_aggregator()
        
        # TODO: Get events from database
        # For now, return mock data structure
        events = []  # Would fetch from PostGIS
        
        # Aggregate events
        event_metrics = aggregator.aggregate_events_by_cell(events)
        risk_scores = aggregator.calculate_risk_scores(event_metrics)
        
        # Build GeoJSON features
        features = []
        for h3_cell, risk_score in risk_scores.items():
            # Get cell geometry
            center_lat, center_lng = h3_gen.get_cell_center(h3_cell)
            boundary = h3_gen.get_cell_boundary(h3_cell)
            
            # Convert boundary to GeoJSON coordinates (lng, lat)
            coords = [[lng, lat] for lat, lng in boundary]
            coords.append(coords[0])  # Close polygon
            
            # Get metrics
            metrics = event_metrics.get(h3_cell, {})
            
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords]
                },
                "properties": {
                    "h3_cell": h3_cell,
                    "risk_score": risk_score,
                    "risk_level": _get_risk_level(risk_score),
                    "event_count": metrics.get("total_events", 0),
                    "crime_count": metrics.get("crime_events", 0),
                    "fire_count": metrics.get("fire_events", 0),
                    "recent_7d": metrics.get("recent_events_7d", 0),
                    "recent_30d": metrics.get("recent_events_30d", 0)
                }
            }
            features.append(feature)
        
        return RiskMapResponse(
            type="FeatureCollection",
            features=features,
            metadata={
                "bbox": {
                    "min_lat": bbox_min_lat,
                    "min_lng": bbox_min_lng,
                    "max_lat": bbox_max_lat,
                    "max_lng": bbox_max_lng
                },
                "resolution": resolution,
                "zone_count": len(features),
                "generated_at": datetime.utcnow().isoformat()
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating risk map: {str(e)}")


@router.get("/risk-zones/{h3_cell}", response_model=ZoneDetails)
async def get_zone_details(h3_cell: str):
    """
    Get detailed information for a specific risk zone
    
    Args:
        h3_cell: H3 cell ID (e.g., "892a1072b7fffff")
    
    Returns:
        Detailed zone statistics, events, and trends
    """
    try:
        h3_gen = get_h3_generator()
        
        # Validate H3 cell
        try:
            center_lat, center_lng = h3_gen.get_cell_center(h3_cell)
        except:
            raise HTTPException(status_code=404, detail="Invalid H3 cell ID")
        
        # TODO: Fetch from database
        # For now, return mock structure
        
        return ZoneDetails(
            h3_cell=h3_cell,
            center=[center_lat, center_lng],
            risk_score=45.2,
            risk_level="MEDIUM",
            statistics={
                "total_events": 23,
                "crime_events": 18,
                "fire_events": 2,
                "osint_events": 3,
                "recent_7d": 4,
                "recent_30d": 15,
                "severity_critical": 1,
                "severity_high": 6,
                "severity_medium": 11,
                "severity_low": 5
            },
            recent_events=[
                {
                    "type": "ROBBERY",
                    "severity": "HIGH",
                    "occurred_at": "2026-01-27T10:30:00Z",
                    "description": "Armed robbery at convenience store"
                }
            ],
            trends={
                "7d_change": "+12%",
                "30d_change": "-5%",
                "direction": "increasing"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching zone details: {str(e)}")


@router.get("/risk-history")
async def get_risk_history(
    h3_cell: str = Query(..., description="H3 cell ID"),
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date")
):
    """
    Get historical risk data for a zone
    
    Returns time-series of risk scores
    """
    try:
        # TODO: Query database for historical data
        
        return {
            "h3_cell": h3_cell,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "data_points": [
                {"date": "2026-01-01", "risk_score": 42.1},
                {"date": "2026-01-07", "risk_score": 38.5},
                {"date": "2026-01-14", "risk_score": 45.2},
                {"date": "2026-01-21", "risk_score": 51.3},
                {"date": "2026-01-27", "risk_score": 48.7}
            ],
            "statistics": {
                "min": 38.5,
                "max": 51.3,
                "avg": 45.2,
                "trend": "stable"
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")


def _get_risk_level(risk_score: float) -> str:
    """Convert risk score to categorical level"""
    if risk_score >= 75:
        return "CRITICAL"
    elif risk_score >= 50:
        return "HIGH"
    elif risk_score >= 25:
        return "MEDIUM"
    else:
        return "LOW"
