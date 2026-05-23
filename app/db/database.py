from sqlalchemy import create_engine
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
)


def get_connection():
    return engine.connect()
