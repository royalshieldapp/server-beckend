# H3 Spatial Indexing - Usage Guide

## 🎯 Overview

H3 hexagonal grid system for Miami-Dade County provides:

- **Consistent spatial units** for aggregation
- **Fast spatial queries** using cell IDs
- **Hierarchical resolution** (zoom levels)
- **Neighbor finding** for radius queries
- **Density calculations** per cell
- **Risk scoring** based on events + POIs

---

## 🗺️ Grid Configuration

**Resolution:** 9 (default, configurable in `.env`)

| Metric              | Value                  |
| ------------------- | ---------------------- |
| Edge length         | ~174 meters            |
| Cell area           | ~0.10 km² (100,000 m²) |
| Cells in Miami-Dade | ~10,000-15,000         |
| Coverage            | Full county            |

**Why Resolution 9?**

- Perfect for neighborhood-level analysis
- Small enough for precision
- Large enough to avoid over-fragmentation
- Aligns with typical crime reporting zones

---

## 🚀 Quick Start

### 1. Generate Grid

```python
from services.geospatial import get_h3_generator

# Get singleton instance
h3_gen = get_h3_generator()

# Generate all cells for Miami-Dade
cells = h3_gen.generate_grid()
print(f"Generated {len(cells)} H3 cells")

# Get grid statistics
stats = h3_gen.get_grid_stats()
print(stats)
```

**Output:**

```python
{
    "resolution": 9,
    "total_cells": 12543,
    "edge_length_m": 174.38,
    "cell_area_m2": 105332.51,
    "cell_area_km2": 0.105,
    "total_coverage_km2": 1319.2,
    "bounding_box": {...}
}
```

---

### 2. Assign Events to Cells

```python
# Get H3 cell for a crime location
crime_lat, crime_lng = 25.7617, -80.1918  # Downtown Miami
h3_cell = h3_gen.get_cell_from_point(crime_lat, crime_lng)
print(f"Crime occurred in cell: {h3_cell}")
# Output: "892a1072b7fffff"

# Get cell center
center_lat, center_lng = h3_gen.get_cell_center(h3_cell)

# Get cell boundary (hexagon vertices)
boundary = h3_gen.get_cell_boundary(h3_cell)
print(f"Hexagon has {len(boundary)} vertices")
```

---

### 3. Find Neighbors

```python
# Get immediate neighbors (ring 1)
neighbors = h3_gen.get_neighbors(h3_cell, ring=1)
print(f"Cell has {len(neighbors)} neighbors (including itself)")

# Get second ring neighbors
neighbors_ring2 = h3_gen.get_neighbors(h3_cell, ring=2)

# Get distance between cells
other_cell = "892a1072b0fffff"
distance = h3_gen.get_distance(h3_cell, other_cell)
print(f"Cells are {distance} hexagons apart")
```

---

### 4. Radius Queries

```python
# Find all cells within 500m of a point
lat, lng = 25.7617, -80.1918
radius_m = 500

cells_in_radius = h3_gen.cells_in_radius(lat, lng, radius_m)
print(f"Found {len(cells_in_radius)} cells within {radius_m}m")
```

---

## 📊 Spatial Aggregation

### Aggregate Events by Cell

```python
from services.geospatial import get_spatial_aggregator

aggregator = get_spatial_aggregator()

# Example events from collectors
events = [
    {
        "location": (25.7617, -80.1918),
        "event_category": "CRIME",
        "event_type": "ROBBERY",
        "severity": "HIGH",
        "occurred_at": "2026-01-27T10:00:00Z"
    },
    {
        "location": (25.7620, -80.1920),
        "event_category": "FIRE",
        "severity": "CRITICAL",
        "occurred_at": "2026-01-26T15:30:00Z"
    }
    # ... more events
]

# Aggregate into cells
cell_metrics = aggregator.aggregate_events_by_cell(
    events,
    time_window_days=30
)

# Access metrics for a cell
for cell_id, metrics in cell_metrics.items():
    print(f"Cell {cell_id}:")
    print(f"  Total events: {metrics['total_events']}")
    print(f"  Crime events: {metrics['crime_events']}")
    print(f"  Recent (7d): {metrics['recent_events_7d']}")
    print(f"  Severity breakdown:")
    print(f"    Critical: {metrics['severity_critical']}")
    print(f"    High: {metrics['severity_high']}")
```

**Output Structure:**

```python
{
    "892a1072b7fffff": {
        "total_events": 15,
        "crime_events": 10,
        "fire_events": 2,
        "environmental_events": 2,
        "osint_events": 1,
        "severity_critical": 3,
        "severity_high": 7,
        "severity_medium": 4,
        "severity_low": 1,
        "recent_events_7d": 5,
        "recent_events_30d": 15,
        "event_types": {
            "ROBBERY": 4,
            "ASSAULT": 3,
            "FIRE": 2,
            ...
        },
        "latest_event_date": datetime(2026, 1, 27, ...)
    }
}
```

---

### Aggregate POIs by Cell

```python
# Example POIs
pois = [
    {
        "location": (25.7617, -80.1918),
        "poi_type": "school",
        "name": "Downtown Elementary"
    },
    {
        "location": (25.7620, -80.1920),
        "poi_type": "bank",
        "name": "Chase Bank"
    }
    # ... more POIs
]

poi_metrics = aggregator.aggregate_pois_by_cell(pois)

for cell_id, metrics in poi_metrics.items():
    print(f"Cell {cell_id}:")
    print(f"  Total POIs: {metrics['total_pois']}")
    print(f"  POI types: {metrics['poi_types']}")
```

---

### Calculate Density Metrics

```python
# Add density metrics (events/km²)
density_metrics = aggregator.calculate_density_metrics(cell_metrics)

for cell_id, metrics in density_metrics.items():
    print(f"Cell {cell_id}:")
    print(f"  Event density: {metrics['event_density_per_km2']:.2f} events/km²")
    print(f"  Crime density: {metrics['crime_density_per_km2']:.2f} crimes/km²")
```

---

### Calculate Risk Scores

```python
# Calculate composite risk score (0-100)
risk_scores = aggregator.calculate_risk_scores(
    event_aggregations=cell_metrics,
    poi_aggregations=poi_metrics  # Optional
)

# Sort cells by risk
sorted_cells = sorted(
    risk_scores.items(),
    key=lambda x: x[1],
    reverse=True
)

print("Top 10 highest-risk cells:")
for cell_id, risk_score in sorted_cells[:10]:
    center = h3_gen.get_cell_center(cell_id)
    print(f"  {cell_id}: Risk={risk_score:.1f}, Center={center}")
```

**Risk Score Formula:**

```text
risk_score = (

    critical_events × 10.0 +
    high_events × 5.0 +
    medium_events × 2.0 +
    low_events × 1.0 +
    recent_7d_events × 3.0 +
    recent_30d_events × 1.5 +
    violent_crime_events × 5.0 +
    poi_count × 0.1
)
capped at 100
```

---

## 🎨 Visualization

### Export for Mapping

```python
import json

# Convert to GeoJSON for visualization
geojson_features = []

for cell_id, risk_score in risk_scores.items():
    boundary = h3_gen.get_cell_boundary(cell_id)
    
    # H3 returns (lat, lng), GeoJSON needs [lng, lat]
    coordinates = [[lng, lat] for lat, lng in boundary]
    coordinates.append(coordinates[0])  # Close polygon
    
    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [coordinates]
        },
        "properties": {
            "h3_cell": cell_id,
            "risk_score": risk_score,
            "risk_level": (
                "CRITICAL" if risk_score >= 75 else
                "HIGH" if risk_score >= 50 else
                "MEDIUM" if risk_score >= 25 else
                "LOW"
            )
        }
    }
    geojson_features.append(feature)

geojson = {
    "type": "FeatureCollection",
    "features": geojson_features
}

# Save to file
with open("miami_risk_map.geojson", "w") as f:
    json.dump(geojson, f)
```

**Use in:**

- Google Maps (via Data Layer)
- Mapbox
- Leaflet.js
- QGIS

---

## 🔥 Production Usage

### Database Integration

```python
from services.geospatial.database.connection import get_db_context
from sqlalchemy import text

# Store risk zones in database
with get_db_context() as db:
    for cell_id, risk_score in risk_scores.items():
        center_lat, center_lng = h3_gen.get_cell_center(cell_id)
        
        query = text("""
            INSERT INTO risk_zones (h3_cell_id, location, risk_score)
            VALUES (:h3_cell, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), :score)
            ON CONFLICT (h3_cell_id)
            DO UPDATE SET risk_score = :score, updated_at = NOW()
        """)
        
        db.execute(query, {
            "h3_cell": cell_id,
            "lat": center_lat,
            "lng": center_lng,
            "score": risk_score
        })
```

---

## 📈 Performance

| Operation                         | Time (approx) |
| --------------------------------- | ------------- |
| Generate full grid                | ~100ms        |
| Point to cell                     | <1ms          |
| Get neighbors (ring 1)            | <1ms          |
| Aggregate 1000 events             | ~50ms         |
| Calculate risk scores (10k cells) | ~200ms        |

**Optimizations:**

- H3 operations are O(1) for most queries
- Grid is pre-generated and cached
- Singleton pattern avoids re-initialization

---

## ✅ Testing

```bash
# Test H3 grid generation
python -c "
from services.geospatial import get_h3_generator
h3 = get_h3_generator()
grid = h3.generate_grid()
print(f'✅ Generated {len(grid)} cells')
print(h3.get_grid_stats())
"

# Test aggregation
python -c "
from services.geospatial import get_spatial_aggregator
agg = get_spatial_aggregator()
print('✅ Spatial aggregator ready')
"
```

---

**H3 Spatial Indexing System: ✅ Ready for Production** 🗺️
