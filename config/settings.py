"""
Configuration management for Royal Shield Backend
Loads environment variables and provides typed access to settings
"""
import os
from typing import Optional
from pydantic import BaseSettings, Field, validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # =============================================================================
    # DATABASE
    # =============================================================================
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(default="royal_shield_risk_db", env="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", env="POSTGRES_USER")
    postgres_password: str = Field(default="", env="POSTGRES_PASSWORD")
    
    @property
    def database_url(self) -> str:
        """PostgreSQL connection URL"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    # =============================================================================
    # CRIME DATA APIS
    # =============================================================================
    fbi_crime_api_key: Optional[str] = Field(default=None, env="FBI_CRIME_API_KEY")
    miami_dade_app_token: Optional[str] = Field(default=None, env="MIAMI_DADE_APP_TOKEN")
    
    # =============================================================================
    # ENVIRONMENTAL DATA APIS
    # =============================================================================
    nasa_firms_api_key: Optional[str] = Field(default=None, env="NASA_FIRMS_API_KEY")
    noaa_cdo_token: Optional[str] = Field(default=None, env="NOAA_CDO_TOKEN")
    
    # =============================================================================
    # OSINT FEEDS
    # =============================================================================
    reddit_client_id: Optional[str] = Field(default=None, env="REDDIT_CLIENT_ID")
    reddit_client_secret: Optional[str] = Field(default=None, env="REDDIT_CLIENT_SECRET")
    reddit_user_agent: str = Field(default="RoyalShield/1.0", env="REDDIT_USER_AGENT")
    
    news_api_key: Optional[str] = Field(default=None, env="NEWS_API_KEY")
    
    twitter_bearer_token: Optional[str] = Field(default=None, env="TWITTER_BEARER_TOKEN")
    twitter_api_key: Optional[str] = Field(default=None, env="TWITTER_API_KEY")
    twitter_api_secret: Optional[str] = Field(default=None, env="TWITTER_API_SECRET")
    
    # =============================================================================
    # VECTOR DATABASE
    # =============================================================================
    pinecone_api_key: Optional[str] = Field(default=None, env="PINECONE_API_KEY")
    pinecone_environment: str = Field(default="us-west1-gcp", env="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field(default="royal-shield-zones", env="PINECONE_INDEX_NAME")
    
    # =============================================================================
    # AI/ML SERVICES
    # =============================================================================
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    use_local_embeddings: bool = Field(default=True, env="USE_LOCAL_EMBEDDINGS")
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        env="EMBEDDING_MODEL"
    )
    
    # =============================================================================
    # API SECURITY
    # =============================================================================
    jwt_secret: str = Field(
        default="CHANGE_THIS_SECRET_KEY_IN_PRODUCTION",
        env="JWT_SECRET"
    )
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=60, env="JWT_EXPIRE_MINUTES")
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    
    # =============================================================================
    # APPLICATION
    # =============================================================================
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/royal_shield_backend.log", env="LOG_FILE")
    
    data_collection_interval_hours: int = Field(default=6, env="DATA_COLLECTION_INTERVAL_HOURS")
    model_retrain_interval_days: int = Field(default=7, env="MODEL_RETRAIN_INTERVAL_DAYS")
    
    # Cache
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    
    # =============================================================================
    # MIAMI-DADE CONFIGURATION
    # =============================================================================
    bbox_min_lat: float = Field(default=25.1398, env="BBOX_MIN_LAT")
    bbox_min_lng: float = Field(default=-80.8738, env="BBOX_MIN_LNG")
    bbox_max_lat: float = Field(default=25.9740, env="BBOX_MAX_LAT")
    bbox_max_lng: float = Field(default=-80.1194, env="BBOX_MAX_LNG")
    
    default_h3_resolution: int = Field(default=9, env="DEFAULT_H3_RESOLUTION")
    
    # =============================================================================
    # FEATURE FLAGS
    # =============================================================================
    enable_crime_collection: bool = Field(default=True, env="ENABLE_CRIME_COLLECTION")
    enable_environmental_collection: bool = Field(default=True, env="ENABLE_ENVIRONMENTAL_COLLECTION")
    enable_osint_collection: bool = Field(default=True, env="ENABLE_OSINT_COLLECTION")
    enable_camera_integration: bool = Field(default=False, env="ENABLE_CAMERA_INTEGRATION")
    enable_ml_predictions: bool = Field(default=True, env="ENABLE_ML_PREDICTIONS")
    enable_vector_search: bool = Field(default=True, env="ENABLE_VECTOR_SEARCH")
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value"""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == "development"
    
    @property
    def miami_dade_bbox(self) -> tuple:
        """Get Miami-Dade bounding box as tuple"""
        return (
            self.bbox_min_lat,
            self.bbox_min_lng,
            self.bbox_max_lat,
            self.bbox_max_lng
        )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    Call this function to access settings throughout the application
    """
    return Settings()


# Convenience exports
settings = get_settings()
