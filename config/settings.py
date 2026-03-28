"""
Configuration Management System for Rural Advisory Platform
Supports environment-based configuration with validation and type hints
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from functools import lru_cache
from typing import Optional, Dict, Any
import os
from enum import Enum

class Environment(str, Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"

class DatabaseConfig(BaseSettings):
    """Database Configuration"""
    url: str = Field(default="sqlite:///app.db", env="DATABASE_URL")
    pool_size: int = Field(default=20, env="DB_POOL_SIZE")
    max_overflow: int = Field(default=10, env="DB_MAX_OVERFLOW")
    echo: bool = Field(default=False, env="DB_ECHO")
    
    class Config:
        env_file = ".env"

class MLModelConfig(BaseSettings):
    """ML Model Configuration"""
    # Model paths and versions
    model_dir: str = Field(default="models", env="MODEL_DIR")
    enable_ensemble: bool = Field(default=True, env="ENABLE_ENSEMBLE")
    ensemble_models: list = ["mobilenetv2", "efficientnet", "resnet50"]
    
    # Model confidence thresholds
    confidence_threshold: float = Field(default=0.6, env="CONFIDENCE_THRESHOLD")
    low_confidence_threshold: float = Field(default=0.5, env="LOW_CONFIDENCE_THRESHOLD")
    
    # Model optimization
    quantization_enabled: bool = Field(default=True, env="QUANTIZATION_ENABLED")
    batch_size: int = Field(default=32, env="BATCH_SIZE")
    max_image_size: int = Field(default=512, env="MAX_IMAGE_SIZE")
    
    # GPU/CPU
    use_gpu: bool = Field(default=True, env="USE_GPU")
    gpu_memory_fraction: float = Field(default=0.8, env="GPU_MEMORY_FRACTION")
    
    class Config:
        env_file = ".env"

class WeatherConfig(BaseSettings):
    """Weather API Configuration"""
    api_key: Optional[str] = Field(default=None, env="OPENWEATHER_API_KEY")
    api_url: str = Field(default="https://api.openweathermap.org/data/2.5/weather", env="WEATHER_API_URL")
    cache_ttl: int = Field(default=3600, env="WEATHER_CACHE_TTL")  # 1 hour
    enable_cache: bool = Field(default=True, env="WEATHER_CACHE_ENABLED")
    fallback_on_error: bool = Field(default=True, env="WEATHER_FALLBACK_ON_ERROR")
    
    class Config:
        env_file = ".env"

class AudioConfig(BaseSettings):
    """Audio/Voice Configuration"""
    output_format: str = Field(default="mp3", env="AUDIO_FORMAT")
    language: str = Field(default="ta", env="AUDIO_LANGUAGE")  # Tamil
    alternative_languages: list = Field(default=["en", "hi"], env="AUDIO_ALT_LANGUAGES")
    cache_enabled: bool = Field(default=True, env="AUDIO_CACHE_ENABLED")
    max_cache_size: int = Field(default=1000, env="AUDIO_MAX_CACHE")
    
    class Config:
        env_file = ".env"

class APIConfig(BaseSettings):
    """API Configuration"""
    title: str = Field(default="Rural Advisory API", env="API_TITLE")
    version: str = Field(default="2.0.0", env="API_VERSION")
    description: str = Field(default="AI-Powered Agricultural Advisory System", env="API_DESC")
    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=8000, env="API_PORT")
    
    # Security
    secret_key: str = Field(default="change-me-in-production", env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE")
    
    # CORS
    cors_origins: list = Field(default=["*"], env="CORS_ORIGINS")
    cors_credentials: bool = Field(default=True, env="CORS_CREDENTIALS")
    
    class Config:
        env_file = ".env"

class MonitoringConfig(BaseSettings):
    """Monitoring & Logging Configuration"""
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/app.log", env="LOG_FILE")
    log_format: str = Field(default="json", env="LOG_FORMAT")  # json or text
    
    # Sentry
    sentry_enabled: bool = Field(default=False, env="SENTRY_ENABLED")
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    
    # Prometheus
    prometheus_enabled: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    
    # Performance monitoring
    enable_performance_monitoring: bool = Field(default=True, env="PERF_MONITORING")
    
    class Config:
        env_file = ".env"

class CacheConfig(BaseSettings):
    """Cache Configuration"""
    backend: str = Field(default="redis", env="CACHE_BACKEND")  # redis or in-memory
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    default_ttl: int = Field(default=3600, env="CACHE_DEFAULT_TTL")
    max_size: int = Field(default=1000, env="CACHE_MAX_SIZE")
    
    class Config:
        env_file = ".env"

class Settings(BaseSettings):
    """Main Settings Class"""
    # Environment
    environment: Environment = Field(default=Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # Sub-configurations
    database: DatabaseConfig = DatabaseConfig()
    ml_model: MLModelConfig = MLModelConfig()
    weather: WeatherConfig = WeatherConfig()
    audio: AudioConfig = AudioConfig()
    api: APIConfig = APIConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    cache: CacheConfig = CacheConfig()
    
    # Application settings
    app_name: str = Field(default="Rural Agricultural Advisory System", env="APP_NAME")
    app_version: str = Field(default="2.0.0", env="APP_VERSION")
    
    # Features
    enable_api: bool = Field(default=True, env="ENABLE_API")
    enable_streamlit_ui: bool = Field(default=True, env="ENABLE_UI")
    enable_batch_processing: bool = Field(default=True, env="ENABLE_BATCH")
    enable_analytics: bool = Field(default=True, env="ENABLE_ANALYTICS")
    
    # Disease configuration
    supported_crops: list = Field(default=["tomato", "potato", "rice", "wheat", "cotton"], env="SUPPORTED_CROPS")
    supported_diseases: dict = Field(default={}, env="SUPPORTED_DISEASES")
    
    @validator('environment', pre=True)
    def validate_environment(cls, v):
        if isinstance(v, str):
            return Environment(v)
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == Environment.PRODUCTION
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == Environment.DEVELOPMENT
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get settings instance (cached)
    
    Returns:
        Settings: Configuration object
    """
    return Settings()

# Export settings instance
settings = get_settings()

# Configuration validation on import
if __name__ == "__main__":
    print("Configuration Validation")
    print("=" * 60)
    print(f"Environment: {settings.environment}")
    print(f"Debug Mode: {settings.debug}")
    print(f"Database URL: {settings.database.url}")
    print(f"ML Models Ensemble: {settings.ml_model.enable_ensemble}")
    print(f"Models: {settings.ml_model.ensemble_models}")
    print(f"API Port: {settings.api.port}")
    print("=" * 60)
    print("✅ Configuration loaded successfully!")
