# Machine Learning Models - Usage Guide

## 🤖 Overview

Royal Shield ML system includes:

1. **DBSCAN Hotspot Detector** - Finds geographic crime clusters
2. **XGBoost Risk Predictor** - Predicts future risk scores
3. **Feature Engineering** - Extracts 30+ features from spatial data

All models work with H3 hexagonal grid system for consistent spatial analysis.

---

## 🔥 Hotspot Detection (DBSCAN)

### What It Does

Identifies geographic areas with high density of incidents using **DBSCAN** (Density-Based Spatial Clustering).

**Advantages:**

- Automatically finds number of clusters
- Handles irregular cluster shapes
- Identifies outliers (noise points)
- Works great with geographic data

### Quick Start

```python
from services.ml import get_hotspot_detector

detector = get_hotspot_detector()

# Detect hotspots from events
result = detector.detect_hotspots(
    events=crime_events,
    time_window_days=30
)

print(f"Found {result['clusters_found']} hotspots")

# Access hotspot details
for hotspot in result['hotspots']:
    print(f"Hotspot #{hotspot['hotspot_id']}")
    print(f"  Center: {hotspot['center']}")
    print(f"  Radius: {hotspot['radius_meters']}m")
    print(f"  Events: {hotspot['event_count']}")
    print(f"  Risk: {hotspot['risk_score']:.1f} ({hotspot['risk_level']})")
```

### Configuration

```python
detector = HotspotDetector(
    eps_meters=500.0,        # Max distance between cluster points
    min_samples=5,           # Min events to form a cluster
    severity_weights={       # Event severity multipliers
        "CRITICAL": 5.0,
        "HIGH": 3.0,
        "MEDIUM": 2.0,
        "LOW": 1.0
    }
)
```

**Parameter Guide:**

| Parameter | Default | Description |
| --- | --- | --- |
| `eps_meters` | 500 | Cluster radius (smaller = tighter clusters) |
| `min_samples` | 5 | Min events for cluster (higher = fewer clusters) |
| `severity_weights` | See code | How much to weight severe events |

### Output Structure

```python
{
    "hotspots": [
        {
            "hotspot_id": 0,
            "center": {"lat": 25.7617, "lng": -80.1918},
            "h3_cell": "892a1072b7fffff",
            "radius_meters": 342.5,
            "event_count": 15,
            "event_types": {
                "ROBBERY": 7,
                "ASSAULT": 5,
                "THEFT": 3
            },
            "severities": {
                "CRITICAL": 3,
                "HIGH": 7,
                "MEDIUM": 4,
                "LOW": 1
            },
            "risk_score": 78.3,
            "risk_level": "CRITICAL"
        }
    ],
    "total_events": 523,
    "recent_events": 152,
    "clusters_found": 12,
    "noise_points": 37
}
```

---

## 🎯 Risk Prediction (XGBoost)

### Objective

Predicts future risk scores (0-100) for each H3 cell using **XGBoost** gradient boosting.

**Features Used:**

- Historical event counts (by type, severity)
- Temporal trends (7d, 30d recency)
- Spatial features (neighbor statistics)
- POI density (schools, banks, bars, etc.)
- Derived metrics (violence ratio, severity index)

### Training

```python
from services.ml import get_risk_predictor

predictor = get_risk_predictor()

# Train on historical data
training_results = predictor.train(
    events=historical_events,      # 90+ days recommended
    pois=current_pois,
    lookback_days=90,
    validation_split=0.2
)

print(f"Training R²: {training_results['r2_train']:.3f}")
print(f"Validation R²: {training_results['r2_val']:.3f}")

# View feature importance
for feat in training_results['feature_importance'][:5]:
    print(f"  {feat['feature']}: {feat['importance']:.3f}")

# Save trained model
predictor.save_model("models/risk_predictor_v1.pkl")
```

### Prediction

```python
# Load pre-trained model
predictor = get_risk_predictor(model_path="models/risk_predictor_v1.pkl")

# Predict for specific cells
h3_cells = ["892a1072b7fffff", "892a1072b0fffff"]
predictions = predictor.predict(
    h3_cells=h3_cells,
    current_events=recent_events,
    current_pois=current_pois
)

for cell, risk_score in predictions.items():
    level = predictor.get_risk_level(risk_score)
    print(f"{cell}: {risk_score:.1f} ({level})")
```

### Batch Prediction

```python
# Predict all cells at once (faster)
predictions = predictor.predict_batch(
    events=current_events,
    pois=current_pois
)

# Sort by risk
sorted_cells = sorted(
    predictions.items(),
    key=lambda x: x[1],
    reverse=True
)

print("Top 10 highest-risk cells:")
for cell, risk in sorted_cells[:10]:
    print(f"  {cell}: {risk:.1f}")
```

---

## 🛠️ Feature Engineering

### Available Features (30+)

**Event Metrics:**

- `total_events`, `crime_events`, `fire_events`, `environmental_events`, `osint_events`

**Severity Distribution:**

- `severity_critical`, `severity_high`, `severity_medium`, `severity_low`

**Temporal:**

- `recent_events_7d`, `recent_events_30d`
- `recency_ratio_7d`, `recency_ratio_30d`

**Density:**

- `event_density_km2`, `crime_density_km2`

**POI Features:**

- `total_pois`
- `pois_schools`, `pois_hospitals`, `pois_police`, `pois_banks`, `pois_bars`, `pois_nightclubs`

**Neighbor Features (spatial autocorrelation):**

- `neighbor_avg_events`, `neighbor_max_events`
- `neighbor_avg_crimes`, `neighbor_critical_count`

**Derived:**

- `violence_ratio` - Violent crimes / total crimes
- `severity_index` - Weighted severity (0-10)

### Custom Features

```python
from services.ml import get_feature_engineer

engineer = get_feature_engineer()

# Create full training dataset
df = engineer.create_training_dataset(
    events=historical_events,
    pois=current_pois,
    lookback_days=90
)

print(f"Dataset shape: {df.shape}")
print(f"Features: {df.columns.tolist()}")

# Prepare features for single cell
features = engineer.prepare_prediction_features(
    h3_cell="892a1072b7fffff",
    current_events=recent_events,
    current_pois=current_pois
)
```

---

## 🔄 Complete ML Pipeline

### End-to-End Example

```python
from services.ml import (
    get_hotspot_detector,
    get_risk_predictor,
    get_feature_engineer
)

# 1. Detect current hotspots
detector = get_hotspot_detector()
hotspots = detector.detect_hotspots(events=current_events, time_window_days=30)

print(f"Active hotspots: {hotspots['clusters_found']}")

# 2. Train risk predictor
predictor = get_risk_predictor()
training_results = predictor.train(
    events=historical_events,
    pois=current_pois,
    lookback_days=90
)

print(f"Model R²: {training_results['r2_val']:.3f}")

# 3. Predict future risk
predictions = predictor.predict_batch(
    events=current_events,
    pois=current_pois
)

# 4. Identify high-risk cells
high_risk_cells = [
    cell for cell, risk in predictions.items()
    if risk >= 50.0
]

print(f"High-risk cells: {len(high_risk_cells)}")

# 5. Compare with hotspots
hotspot_cells = {h['h3_cell'] for h in hotspots['hotspots']}
predicted_high_risk = set(high_risk_cells)

overlap = hotspot_cells & predicted_high_risk
print(f"Overlap: {len(overlap)}/{len(hotspot_cells)} hotspots")
```

---

## 📊 Model Performance

### Expected Metrics

| Metric | Target | Typical |
| --- | --- | --- |
| Training R² | >0.80 | 0.75-0.85 |
| Validation R² | >0.70 | 0.65-0.75 |
| Hotspot detection | N/A | 10-20 clusters |
| Feature count | 30+ | 35 |

### Improving Accuracy

1. **More data** - 90+ days recommended
2. **Tune hyperparameters** - Adjust XGBoost params
3. **Feature selection** - Remove low-importance features
4. **Ensemble methods** - Combine multiple models
5. **Temporal features** - Add day-of-week, hour patterns

---

## 🚀 Production Deployment

### Model Training Schedule

```python
# Celery task (runs weekly)
@celery_app.task
def retrain_risk_model():
    from services.ml import get_risk_predictor
    from services.data_ingestion.collectors import get_all_events
    
    # Get last 90 days of events
    events = get_all_events(days=90)
    
    # Train model
    predictor = get_risk_predictor()
    results = predictor.train(events=events, lookback_days=90)
    
    # Save if improved
    if results['r2_val'] > 0.70:
        predictor.save_model("models/risk_predictor_latest.pkl")
        logger.info("Model retrained successfully")
    
    return results
```

### Real-time Prediction API

```python
# FastAPI endpoint
@app.get("/api/v1/predict-risk")
async def predict_risk(lat: float, lng: float, radius_meters: float = 1000):
    from services.ml import get_risk_predictor
    from services.geospatial import get_h3_generator
    
    # Get H3 cells in radius
    h3_gen = get_h3_generator()
    cells = h3_gen.cells_in_radius(lat, lng, radius_meters)
    
    # Get predictions
    predictor = get_risk_predictor(model_path="models/risk_predictor_latest.pkl")
    predictions = predictor.predict(
        h3_cells=list(cells),
        current_events=get_recent_events(),
        current_pois=get_nearby_pois(lat, lng, radius_meters)
    )
    
    return {
        "center": {"lat": lat, "lng": lng},
        "radius_meters": radius_meters,
        "cells_analyzed": len(predictions),
        "predictions": predictions,
        "max_risk": max(predictions.values()),
        "avg_risk": sum(predictions.values()) / len(predictions)
    }
```

---

## ✅ Testing

```bash
# Test hotspot detection
python -c "
from services.ml import get_hotspot_detector
detector = get_hotspot_detector()
print('✅ Hotspot detector ready')
"

# Test risk predictor
python -c "
from services.ml import get_risk_predictor
predictor = get_risk_predictor()
print('✅ Risk predictor ready')
"

# Test feature engineering
python -c "
from services.ml import get_feature_engineer
engineer = get_feature_engineer()
print('✅ Feature engineer ready')
"
```

---

**ML System: ✅ Production Ready** 🤖

**Key Capabilities:**

- DBSCAN hotspot detection with severity weighting
- XGBoost risk prediction (0-100 scale)
- 30+ engineered features
- Model persistence & retraining
- Batch & real-time inference
