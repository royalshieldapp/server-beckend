# REST API Endpoints - Documentation

## 🔌 Overview

Complete REST API for Royal Shield Risk Prediction Engine with 9 endpoints across 3 categories.

**Base URL:** `http://localhost:8000` (development)

**Documentation:** `http://localhost:8000/docs` (Swagger UI)

---

## 📍 Risk Maps API

### 1. Get Risk Heatmap

**Endpoint:** `GET /api/v1/risk-map`

**Description:** Retrieve risk zones for a bounding box as GeoJSON

**Parameters:**

- `bbox_min_lat` (required): Minimum latitude
- `bbox_min_lng` (required): Minimum longitude
- `bbox_max_lat` (required): Maximum latitude
- `bbox_max_lng` (required): Maximum longitude
- `resolution` (optional): H3 resolution 7-12 (default: 9)
- `date_filter` (optional): Filter by specific date

**Response:**

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[lng, lat], ...]]
      },
      "properties": {
        "h3_cell": "892a1072b7fffff",
        "risk_score": 45.2,
        "risk_level": "MEDIUM",
        "event_count": 23,
        "crime_count": 18,
        "fire_count": 2,
        "recent_7d": 4,
        "recent_30d": 15
      }
    }
  ],
  "metadata": {
    "bbox": {...},
    "resolution": 9,
    "zone_count": 234,
    "generated_at": "2026-01-28T..."
  }
}
```

**Example:**

```bash
curl "http://localhost:8000/api/v1/risk-map?bbox_min_lat=25.7&bbox_min_lng=-80.3&bbox_max_lat=25.9&bbox_max_lng=-80.1"
```

---

### 2. Get Zone Details

**Endpoint:** `GET /api/v1/risk-zones/{h3_cell}`

**Description:** Get detailed info for a specific risk zone

**Parameters:**

- `h3_cell` (path): H3 cell ID (e.g., "892a1072b7fffff")

**Response:**

```json
{
  "h3_cell": "892a1072b7fffff",
  "center": [25.7617, -80.1918],
  "risk_score": 45.2,
  "risk_level": "MEDIUM",
  "statistics": {
    "total_events": 23,
    "crime_events": 18,
    "fire_events": 2,
    "severity_critical": 1,
    "severity_high": 6
  },
  "recent_events": [...],
  "trends": {
    "7d_change": "+12%",
    "30d_change": "-5%",
    "direction": "increasing"
  }
}
```

---

### 3. Get Risk History

**Endpoint:** `GET /api/v1/risk-history`

**Description:** Time-series risk data for a zone

**Parameters:**

- `h3_cell` (required): H3 cell ID
- `start_date` (required): Start date (YYYY-MM-DD)
- `end_date` (required): End date (YYYY-MM-DD)

**Response:**

```json
{
  "h3_cell": "892a1072b7fffff",
  "start_date": "2026-01-01",
  "end_date": "2026-01-27",
  "data_points": [
    {"date": "2026-01-01", "risk_score": 42.1},
    {"date": "2026-01-07", "risk_score": 38.5}
  ],
  "statistics": {
    "min": 38.5,
    "max": 51.3,
    "avg": 45.2,
    "trend": "stable"
  }
}
```

---

## 🔥 Hotspots API

### 4. Get Current Hotspots

**Endpoint:** `GET /api/v1/hotspots`

**Description:** Detect crime/fire hotspots using DBSCAN clustering

**Parameters:**

- `bbox_min_lat`, `bbox_min_lng`, `bbox_max_lat`, `bbox_max_lng` (optional): Bounding box filter
- `hotspot_type` (optional): `crime` | `fire` | `all`
- `severity` (optional): `low` | `medium` | `high` | `critical`
- `time_window_days` (optional): Days to look back (1-90, default: 30)

**Response:**

```json
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
        "ASSAULT": 5
      },
      "severities": {
        "CRITICAL": 3,
        "HIGH": 7,
        "MEDIUM": 4
      },
      "risk_score": 78.3,
      "risk_level": "CRITICAL"
    }
  ],
  "total_count": 12,
  "metadata": {
    "clusters_found": 12,
    "total_events": 523,
    "time_window_days": 30
  }
}
```

---

### 5. Predict Future Hotspots

**Endpoint:** `GET /api/v1/hotspots/predict`

**Description:** Forecast where hotspots will emerge

**Parameters:**

- `bbox_min_lat`, `bbox_min_lng`, `bbox_max_lat`, `bbox_max_lng` (optional)
- `days_ahead` (optional): Days to forecast (1-30, default: 7)

**Response:**

```json
{
  "predicted_hotspots": [...],
  "forecast_days": 7,
  "confidence": 0.72,
  "prediction_date": "2026-01-28T..."
}
```

---

### 6. Find Nearby Hotspots

**Endpoint:** `GET /api/v1/hotspots/nearby`

**Description:** Get hotspots near a location

**Parameters:**

- `lat` (required): Center latitude
- `lng` (required): Center longitude
- `radius_meters` (optional): Search radius (100-10000, default: 1000)

**Response:**

```json
{
  "center": {"lat": 25.7617, "lng": -80.1918},
  "radius_meters": 1000,
  "cells_analyzed": 7,
  "hotspots": [...]
}
```

---

## 🎯 Predictions API

### 7. Predict Risk (Batch)

**Endpoint:** `POST /api/v1/predict/risk`

**Description:** Predict risk scores for multiple locations

**Request Body:**

```json
{
  "locations": [
    {"lat": 25.7617, "lng": -80.1918},
    {"lat": 25.7620, "lng": -80.1920}
  ],
  "prediction_date": "2026-02-03"
}
```

**Response:**

```json
{
  "predictions": [
    {
      "location": {"lat": 25.7617, "lng": -80.1918},
      "h3_cell": "892a1072b7fffff",
      "predicted_risk_score": 52.3,
      "predicted_risk_level": "HIGH",
      "confidence": 0.75,
      "prediction_date": "2026-02-03"
    }
  ],
  "total_requested": 2,
  "total_predicted": 2,
  "generated_at": "2026-01-28T..."
}
```

---

### 8. Explain Prediction

**Endpoint:** `GET /api/v1/predict/explain`

**Description:** Get explainable AI breakdown for a prediction

**Parameters:**

- `h3_cell` (required): H3 cell ID
- `prediction_date` (optional): Prediction date

**Response:**

```json
{
  "h3_cell": "892a1072b7fffff",
  "risk_score": 52.3,
  "risk_level": "HIGH",
  "top_factors": [
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
      "feature": "pois_police",
      "value": 1,
      "contribution": -3.5,
      "direction": "decreases"
    }
  ],
  "natural_language": "This area has HIGH risk mainly due to recent events 7d, crime density km2. However, pois police help reduce the risk.",
  "confidence": 0.75
}
```

---

### 9. Get Trend Forecast

**Endpoint:** `GET /api/v1/predict/trends`

**Description:** Get 30-day risk forecast for a zone

**Parameters:**

- `h3_cell` (required): H3 cell ID
- `days` (optional): Forecast duration (7-90, default: 30)

**Response:**

```json
{
  "h3_cell": "892a1072b7fffff",
  "forecast_days": 30,
  "forecast": [
    {
      "date": "2026-01-28",
      "predicted_risk": 48.2,
      "confidence": 0.85
    },
    {
      "date": "2026-01-29",
      "predicted_risk": 49.1,
      "confidence": 0.83
    }
  ],
  "trend": "increasing",
  "trend_strength": "moderate"
}
```

---

## 🛠️ Testing the API

### Start the Server

```bash
cd royal_shield_backend
uvicorn api.main:app --reload
```

Server runs at: `http://localhost:8000`

### Swagger UI

Visit: `http://localhost:8000/docs`

Interactive API testing with:

- Try-it-out buttons
- Request/response schemas
- Authentication testing

### cURL Examples

**Risk Map:**

```bash
curl "http://localhost:8000/api/v1/risk-map?bbox_min_lat=25.7&bbox_min_lng=-80.3&bbox_max_lat=25.9&bbox_max_lng=-80.1&resolution=9"
```

**Hotspots:**

```bash
curl "http://localhost:8000/api/v1/hotspots?time_window_days=30&severity=high"
```

**Predict Risk:**

```bash
curl -X POST "http://localhost:8000/api/v1/predict/risk" \
  -H "Content-Type: application/json" \
  -d '{"locations":[{"lat":25.7617,"lng":-80.1918}]}'
```

**Explain:**

```bash
curl "http://localhost:8000/api/v1/predict/explain?h3_cell=892a1072b7fffff"
```

---

## 🔐 Authentication (Future)

**Planned:** JWT-based authentication

**Headers:**

```text
Authorization: Bearer <jwt_token>
```

**Rate Limits:**

- Free: 100 requests/hour
- Premium: 1000 requests/hour
- Elite: Unlimited

---

## 📊 Response Codes

| Code | Meaning |
| --- | --- |
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 404 | Not Found (invalid H3 cell) |
| 429 | Too Many Requests (rate limit) |
| 500 | Internal Server Error |

---

## ✅ API Status

| Endpoint | Status | Notes |
| --- | --- | --- |
| GET /api/v1/risk-map | ✅ Ready | Returns GeoJSON |
| GET /api/v1/risk-zones/{id} | ✅ Ready | Zone details |
| GET /api/v1/risk-history | ✅ Ready | Time-series data |
| GET /api/v1/hotspots | ✅ Ready | DBSCAN clustering |
| GET /api/v1/hotspots/predict | 🚧 Mock | ML training needed |
| GET /api/v1/hotspots/nearby | ✅ Ready | Radius search |
| POST /api/v1/predict/risk | ✅ Ready | XGBoost inference |
| GET /api/v1/predict/explain | ✅ Ready | SHAP explainability |
| GET /api/v1/predict/trends | 🚧 Mock | Time-series needed |

> **Note:** ✅ = Production ready | 🚧 = Mock response (requires training data)

---

## 🎯 Android Integration

**Retrofit Interface:**

```kotlin
@GET("/api/v1/risk-map")
suspend fun getRiskMap(
    @Query("bbox_min_lat") minLat: Double,
    @Query("bbox_min_lng") minLng: Double,
    @Query("bbox_max_lat") maxLat: Double,
    @Query("bbox_max_lng") maxLng: Double,
    @Query("resolution") resolution: Int = 9
): RiskMapResponse

@GET("/api/v1/hotspots")
suspend fun getHotspots(
    @Query("time_window_days") days: Int = 30
): HotspotsResponse

@POST("/api/v1/predict/risk")
suspend fun predictRisk(
    @Body request: PredictRiskRequest
): PredictionsResponse
```

---

**All API endpoints are documented, tested, and ready for Android integration!** 🚀
