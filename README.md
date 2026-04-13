# Royal Shield Risk Prediction Engine - Backend

🛡️ **Predictive risk intelligence platform backend services**

Transform Royal Shield from a reactive security app into a predictive platform that forecasts dangers before they occur using crime data, environmental hazards, OSINT feeds, and ML models.

## 🏗️ Architecture

**Stack:**

- **Framework:** FastAPI 0.104+
- **Database:** PostgreSQL 15 + PostGIS 3.4
- **Caching:** Redis 7
- **ML:** XGBoost, LightGBM, Scikit-learn
- **Geospatial:** H3, Shapely, GeoAlchemy2
- **Vector Search:** Pinecone / Weaviate / Qdrant
- **Task Queue:** Celery + Redis

**Services:**

1. Data Ingestion (FBI, Miami-Dade, NASA FIRMS, NOAA, OSINT)
2. Geo spatial Processing (PostGIS, H3 gridding)
3. ML Engine (hotspot detection, risk prediction)
4. Vector Search (semantic zone queries)
5. Camera Intelligence (RTSP/ONVIF activity detection)
6. REST API (risk maps, predict ions, explanations)

---

## 🚀 Quick Start

### Prerequisites

- **Docker** & **Docker Compose** (recommended)
- OR **Python 3.10+**, **PostgreSQL 15+** with PostGIS

### Option 1: Docker (Recommended)

```bash
# 1. Clone and navigate
cd royal_shield/royal_shield_backend

# 2. Create .env file
cp config/.env.example .env
# Edit .env and add your API credentials

# 3. Start all services
docker-compose up -d

# 4. Check logs
docker-compose logs -f api

# 5. Access API
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
# pgAdmin: http://localhost:5050 (dev profile)
```

**Services Running:**

- PostgreSQL (PostGIS): `localhost:5432`
- Redis: `localhost:6379`
- FastAPI: `localhost:8000`
- Celery Worker: background tasks
- Celery Beat: scheduled jobs

### Option 2: Local Development

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Setup PostgreSQL with PostGIS
# Install PostgreSQL 15+ and PostGIS extension
createdb royal_shield_risk_db
psql royal_shield_risk_db -f services/geospatial/database/schema.sql

# 3. Setup Redis
# Install and start Redis server

# 4. Create .env
cp config/.env.example .env
# Configure database credentials and API keys

# 5. Run FastAPI
uvicorn api.main:app --reload --port 8000

# 6. Run Celery worker (separate terminal)
celery -A services.tasks worker --loglevel=info

# 7. Run Celery beat (separate terminal)
celery -A services.tasks beat --loglevel=info
```

---

## 🔑 API Credentials Setup

Before running, you need API credentials for data sources. See `api_connections_required.md` in the brain folder for details.

**Required Credentials (add to `.env`):**

```bash
# Crime Data
FBI_CRIME_API_KEY=your_key_here
MIAMI_DADE_APP_TOKEN=your_token_here

# Environmental Data
NASA_FIRMS_API_KEY=your_key_here
NOAA_CDO_TOKEN=your_token_here  # optional

# OSINT Feeds
REDDIT_CLIENT_ID=your_id_here
REDDIT_CLIENT_SECRET=your_secret_here
NEWS_API_KEY=your_key_here

# Vector Database (choose one)
PINECONE_API_KEY=your_key_here  # recommended
# OR
# WEAVIATE_URL=your_url_here
# WEAVIATE_API_KEY=your_key_here

# Optional: OpenAI for embeddings/NLP
OPENAI_API_KEY=your_key_here
# OR use free local embeddings (default)
USE_LOCAL_EMBEDDINGS=true
```

**Get API Keys:**

- [FBI Crime API](https://api.data.gov/signup/)
- [Miami-Dade Open Data](https://opendata.miamidade.gov/profile/app_tokens)
- [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/api/area/)
- [Reddit API](https://www.reddit.com/prefs/apps)
- [News API](https://newsapi.org/register)
- [Pinecone](https://app.pinecone.io/)

---

## 📡 API Endpoints

### Core Endpoints

#### Health & Info

```bash
GET /health
GET /api/v1/info
```

#### Risk Maps (TODO)

```bash
GET /api/v1/risk-map?bbox=lat1,lng1,lat2,lng2&resolution=9
GET /api/v1/risk-zones/{h3_index}
GET /api/v1/risk-history?h3_index=xxx&start_date=2026-01-01
```

#### Hotspots (TODO)

```bash
GET /api/v1/hotspots?bbox=...&type=crime
GET /api/v1/hotspots/predict?bbox=...&days_ahead=7
GET /api/v1/hotspots/nearby?lat=25.7617&lng=-80.1918&radius=1000
```

#### Predictions (TODO)

```bash
POST /api/v1/predict/risk
GET /api/v1/predict/explain?h3_index=xxx&date=2026-02-03
GET /api/v1/predict/trends?h3_index=xxx&days=30
```

**Try it:**

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/info
```

---

## 🗄️ Database Schema

The PostGIS database includes:

**Core Tables:**

- `risk_zones` - H3 hexagonal risk grid
- `crime_events` - Crime incidents from all sources
- `environmental_events` - Fires, hurricanes, floods
- `poi_data` - Points of Interest from OSM
- `user_reports` - Community reports

**ML Tables:**

- `hotspots` - DBSCAN/K-means clustering results
- `risk_predictions` - XGBoost future risk forecasts
- `zone_embeddings` - Vector embeddings for semantic search

**Camera Tables:**

- `camera_configs` - User IP cameras
- `camera_activity` - Activity logs (metadata only, no video)

**See:** `services/geospatial/database/schema.sql` for full DDL

---

## 🔄 Data Collection

### Manual Trigger

```python
from services.data_ingestion.collectors.crime_collector import FBICrimeCollector
from datetime import datetime, timedelta

# Collect last 30 days of crime data
collector = FBICrimeCollector()
stats = await collector.run(
    start_date=datetime.now() - timedelta(days=30),
    end_date=datetime.now()
)
print(stats)
```

### Scheduled Collection (Celery)

Data is automatically collected every 6 hours (configurable in `.env`):

```bash
# Check Celery tasks
celery -A services.tasks inspect active

# Run task manually
celery -A services.tasks call services.tasks.collect_all_data
```

---

## 🤖 Machine Learning

### Train Hotspot Detector

```bash
cd services/ml_engine
python -m training.train_hotspot_model
```

### Train Risk Predictor

```bash
python -m training.train_risk_model
```

### Evaluate Models

```bash
python -m training.evaluate_models
```

**Models are versioned and stored in:** `services/ml_engine/models/`

---

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=services --cov-report=html

# Specific module
pytest tests/unit/test_crime_collector.py -v

# Integration tests (requires running services)
pytest tests/integration/ -v
```

---

## 📊 Monitoring

### Logs

```bash
# Docker logs
docker-compose logs -f api
docker-compose logs -f celery_worker

# Local logs
tail -f logs/royal_shield_backend.log
```

### Metrics (TODO: Prometheus)

```bash
# Metrics endpoint (when implemented)
curl http://localhost:8000/metrics
```

---

## 🛠️ Development

### Project Structure

```text
royal_shield_backend/
├── api/                    # FastAPI application
│   ├── main.py
│   ├── routes/            # API endpoints
│   └── schemas/           # Pydantic models
├── services/
│   ├── data_ingestion/    # Data collectors
│   ├── geospatial/        # PostGIS operations
│   ├── ml_engine/         # ML models
│   ├── vector_search/     # Semantic search
│   ├── camera_intelligence/
│   └── intelligence_service/
├── config/                # Configuration
├── tests/                 # Unit & integration tests
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### Code Style

```bash
# Format code
black .

# Lint
flake8 .

# Type check
my py services/
```

### Adding a New Data Source

1. Create collector in `services/data_ingestion/collectors/`
2. Inherit from `BaseCollector`
3. Implement: `collect()`, `validate()`, `transform()`, `store()`
4. Add to Celery tasks
5. Write tests

**Example:** See `collectors/crime_collector.py`

---

## 🚢 Deployment

### Docker Production

```bash
# Build for production
docker build -t royal-shield-backend:latest .

# Run with production .env
docker-compose -f docker-compose.prod.yml up -d
```

### Cloud Deployment (GCP Cloud Run)

```bash
# Build and push
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/royal-shield-backend

# Deploy
gcloud run deploy royal-shield-backend \
  --image gcr.io/YOUR_PROJECT_ID/royal-shield-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

## 🔒 Security

- **API Keys:** Never commit `.env` to version control
- **Database:** Use strong passwords, enable SSL
- **Camera Passwords:** Encrypted at application level
- **No PII:** All data is anonymized
- **No Facial Recognition:** Person detection only (bounding boxes)

---

## 📝 TODO (Implementation Roadmap)

- [x] Phase 1: Project structure & configuration
- [x] Phase 1: Database schema
- [x] Phase 1: Base data collector framework
- [ ] Phase 1: Complete all data collectors (OSM, NASA, NOAA, OSINT)
- [ ] Phase 2: PostGIS integration & H3 grid seeding
- [ ] Phase 3: Risk calculation engine
- [ ] Phase 4: ML models (DBSCAN, XGBoost)
- [ ] Phase 5: Vector embeddings & semantic search
- [ ] Phase 6: Camera integration
- [ ] Phase 7: Intelligence service (NLP + explainability)
- [ ] Phase 8: Complete REST API endpoints
- [ ] Phase 9: Android SDK integration
- [ ] Phase 10: UI/UX for explanations
- [ ] Phase 11: Privacy audit & compliance

**See:** `task.md` in brain folder for detailed checklist

---

## 📞 Support

**Issues:** Report bugs or request features via GitHub Issues

**Documentation:** Full API docs at `/docs` (development mode)

**Contact:** Royal Shield Development Team

---

**Royal Shield - Predicting Dangers Before They Occur** 🛡️
