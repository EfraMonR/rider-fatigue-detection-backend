import pickle
from pathlib import Path

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ModelNotAvailableError(Exception):
    pass


_model = None


def load_model() -> object:
    global _model
    if _model is not None:
        return _model

    model_path = Path(settings.MODEL_PATH)
    if not model_path.exists():
        logger.error("Model file not found at path configured in MODEL_PATH")
        raise ModelNotAvailableError("Model file not found")

    try:
        with open(model_path, "rb") as f:
            _model = pickle.load(f)
        logger.info("Model loaded successfully from MODEL_PATH")
    except Exception as exc:
        logger.error("Failed to load model: %s", type(exc).__name__)
        raise ModelNotAvailableError("Model could not be loaded") from exc

    return _model


def get_model() -> object:
    return load_model()
