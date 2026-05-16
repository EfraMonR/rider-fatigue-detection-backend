import base64
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    DATABASE_URL: str = "sqlite:///./data/segvial.db"

    # JWT
    JWT_SECRET_KEY: str
    JWT_ACCESS_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_EXPIRE_DAYS: int = 7

    # Model
    MODEL_PATH: str = "app/models_ai/modelo.pkl"
    KMEANS_SCALER_MEAN: float = 78.5
    KMEANS_SCALER_STD: float = 12.3
    DEFAULT_BASELINE_BPM: int = 72

    # Stress thresholds (post-inference)
    STRESS_THRESHOLD_MODERATE: float = 0.4
    STRESS_THRESHOLD_HIGH: float = 0.7

    # Weather
    WEATHER_API_URL: str = "https://api.open-meteo.com/v1/forecast"
    WEATHER_CACHE_TTL_MINUTES: int = 15

    # Alerts
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "alertas@segvial.app"

    # Biometric encryption
    BIOMETRIC_KEY: str

    # Uploads
    MAX_UPLOAD_SIZE_MB: int = 2

    def model_post_init(self, __context: object) -> None:
        if len(self.JWT_SECRET_KEY) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")

        try:
            key_bytes = base64.b64decode(self.BIOMETRIC_KEY)
        except Exception:
            raise ValueError("BIOMETRIC_KEY must be a valid base64 string")

        if len(key_bytes) != 32:
            raise ValueError("BIOMETRIC_KEY must decode to exactly 32 bytes")


settings = Settings()
