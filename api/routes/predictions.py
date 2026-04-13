"""
Prediction API Routes
Endpoints for risk predictions and explainability
"""
from fastapi import APIRouter, Query, HTTPException, Body
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import date, datetime

from services.ml import get_risk_predictor, get_feature_engineer
from services.geospatial import get_h3_generator

router = APIRouter(prefix="/api/v1", tags=["Predictions"])


# Request/Response Models
class LocationInput(BaseModel):
    """Single location for prediction"""
    lat: float
    lng: float


class PredictRiskRequest(BaseModel):
    """Batch prediction request"""
    locations: List[LocationInput]
    prediction_date: Optional[date] = None


class RiskPrediction(BaseModel):
    """Risk prediction for a location"""
    location: dict
    h3_cell: str
    predicted_risk_score: float = Field(..., ge=0, le=100)
    predicted_risk_level: str
    confidence: float = Field(..., ge=0, le=1)
    prediction_date: str


class PredictionExplanation(BaseModel):
    """Explainable prediction"""
    h3_cell: str
    risk_score: float
    risk_level: str
    top_factors: List[dict]
    natural_language: str
    confidence: float


@router.post("/predict/risk")
async def predict_risk(request: PredictRiskRequest = Body(...)):
    """
    Predict risk scores for multiple locations
    
    Args:
        request: Locations and optional prediction date
    
    Returns:
        Risk predictions for each location
    """
    try:
        h3_gen = get_h3_generator()
        predictor = get_risk_predictor(model_path="models/risk_predictor_latest.pkl")
        
        predictions = []
        
        for location in request.locations:
            # Get H3 cell
            h3_cell = h3_gen.get_cell_from_point(location.lat, location.lng)
            
            # TODO: Get current events/POIs from database for prediction
            current_events = []
            current_pois = []
            
            # Predict
            try:
                risk_scores = predictor.predict(
                    h3_cells=[h3_cell],
                    current_events=current_events,
                    current_pois=current_pois
                )
                
                risk_score = risk_scores.get(h3_cell, 0.0)
                risk_level = predictor.get_risk_level(risk_score)
                
                predictions.append(RiskPrediction(
                    location={"lat": location.lat, "lng": location.lng},
                    h3_cell=h3_cell,
                    predicted_risk_score=risk_score,
                    predicted_risk_level=risk_level,
                    confidence=0.75,  # TODO: Calculate actual confidence
                    prediction_date=(request.prediction_date or date.today()).isoformat()
                ))
            
            except Exception as e:
                # Skip failed predictions
                continue
        
        return {
            "predictions": predictions,
            "total_requested": len(request.locations),
            "total_predicted": len(predictions),
            "prediction_date": (request.prediction_date or date.today()).isoformat(),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error predicting risk: {str(e)}")


@router.get("/predict/explain", response_model=PredictionExplanation)
async def explain_prediction(
    h3_cell: str = Query(..., description="H3 cell ID"),
    prediction_date: Optional[date] = Query(None, description="Prediction date")
):
    """
    Get explainable prediction for a zone
    
    Returns SHAP-based feature importance and natural language explanation
    """
    try:
        h3_gen = get_h3_generator()
        predictor = get_risk_predictor(model_path="models/risk_predictor_latest.pkl")
        engineer = get_feature_engineer()
        
        # Validate H3 cell
        try:
            center_lat, center_lng = h3_gen.get_cell_center(h3_cell)
        except:
            raise HTTPException(status_code=404, detail="Invalid H3 cell ID")
        
        # TODO: Fetch current data from database
        current_events = []
        current_pois = []
        
        # Get prediction
        risk_scores = predictor.predict(
            h3_cells=[h3_cell],
            current_events=current_events,
            current_pois=current_pois
        )
        
        risk_score = risk_scores.get(h3_cell, 0.0)
        risk_level = predictor.get_risk_level(risk_score)
        
        # TODO: Implement SHAP explainer for actual feature importance
        # For now, mock top factors
        top_factors = [
            {
                "feature": "recent_events_7d",
                "value": 5,
                "contribution": +12.3,
                "direction": "increases"
            },
            {
                "feature": "crime_density_km2",
                "value": 45.2,
                "contribution": +8.7,
                "direction": "increases"
            },
            {
                "feature": "pois_bars",
                "value": 3,
                "contribution": +4.1,
                "direction": "increases"
            },
            {
                "feature": "pois_police",
                "value": 1,
                "contribution": -3.5,
                "direction": "decreases"
            }
        ]
        
        # Generate natural language explanation
        nl_explanation = _generate_explanation(risk_level, top_factors)
        
        return PredictionExplanation(
            h3_cell=h3_cell,
            risk_score=risk_score,
            risk_level=risk_level,
            top_factors=top_factors,
            natural_language=nl_explanation,
            confidence=0.75
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error explaining prediction: {str(e)}")


@router.get("/predict/trends")
async def get_trend_forecast(
    h3_cell: str = Query(..., description="H3 cell ID"),
    days: int = Query(30, ge=7, le=90, description="Forecast duration in days")
):
    """
    Get trend forecast for a zone
    
    Returns:
        Daily risk forecast for next N days
    """
    try:
        # TODO: Implement time-series forecasting
        # Would use historical patterns + seasonality
        
        return {
            "h3_cell": h3_cell,
            "forecast_days": days,
            "forecast": [
                {"date": "2026-01-28", "predicted_risk": 48.2, "confidence": 0.85},
                {"date": "2026-01-29", "predicted_risk": 49.1, "confidence": 0.83},
                {"date": "2026-01-30", "predicted_risk": 51.3, "confidence": 0.80},
                # ... more days
            ],
            "trend": "increasing",
            "trend_strength": "moderate",
            "message": "Time-series forecasting coming soon"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error forecasting trends: {str(e)}")


def _generate_explanation(risk_level: str, factors: List[dict]) -> str:
    """Generate natural language explanation from factors"""
    
    if risk_level == "CRITICAL":
        intro = "This area has CRITICAL risk"
    elif risk_level == "HIGH":
        intro = "This area has HIGH risk"
    elif risk_level == "MEDIUM":
        intro = "This area has MODERATE risk"
    else:
        intro = "This area has LOW risk"
    
    # Extract top positive and negative factors
    positive_factors = [f for f in factors if f["contribution"] > 0][:2]
    negative_factors = [f for f in factors if f["contribution"] < 0][:2]
    
    explanation_parts = [intro]
    
    if positive_factors:
        reasons = ", ".join([f["feature"].replace("_", " ") for f in positive_factors])
        explanation_parts.append(f"mainly due to {reasons}")
    
    if negative_factors:
        mitigating = ", ".join([f["feature"].replace("_", " ") for f in negative_factors])
        explanation_parts.append(f"However, {mitigating} help reduce the risk")
    
    return ". ".join(explanation_parts) + "."
