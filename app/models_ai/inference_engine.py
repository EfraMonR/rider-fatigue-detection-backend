import numpy as np

from app.config import settings
from app.models_ai.model_loader import ModelNotAvailableError, get_model
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _compute_features(series: list[dict]) -> np.ndarray:
    bpms = np.array([row["bpm"] for row in series], dtype=float)
    features = np.array([
        bpms.mean(),
        bpms.std(),
        np.percentile(bpms, 25),
        np.percentile(bpms, 75),
        bpms.max(),
    ])
    # Estandarizar con parámetros del scaler de entrenamiento
    scaled = (features - settings.KMEANS_SCALER_MEAN) / settings.KMEANS_SCALER_STD
    return scaled.reshape(1, -1)


def _cluster_to_stress(cluster_label: int, n_clusters: int) -> tuple[str, float]:
    """
    Mapea cluster → stress_level y confidence_score.
    Asume que el modelo devuelve etiquetas 0..n-1 ordenadas por BPM medio ascendente.
    """
    ratio = cluster_label / max(n_clusters - 1, 1)
    if ratio < settings.STRESS_THRESHOLD_MODERATE:
        return "Low", round(1.0 - ratio, 2)
    if ratio < settings.STRESS_THRESHOLD_HIGH:
        return "Moderate", round(0.5 + (ratio - settings.STRESS_THRESHOLD_MODERATE) * 0.5, 2)
    return "High", round(ratio, 2)


def run_inference(series: list[dict]) -> dict:
    """
    Input: series limpia de dicts {"timestamp": str, "bpm": float}.
    Output: {"stress_level": "Low|Moderate|High", "confidence_score": 0.0–1.0}
    Lanza ModelNotAvailableError si el modelo no está disponible.
    """
    model = get_model()
    features = _compute_features(series)

    try:
        cluster_label = int(model.predict(features)[0])
        n_clusters = int(model.n_clusters)
    except Exception as exc:
        logger.error("Inference failed: %s", type(exc).__name__)
        raise ModelNotAvailableError("Inference error") from exc

    stress_level, confidence_score = _cluster_to_stress(cluster_label, n_clusters)
    logger.info("Inference complete stress_level=%s", stress_level)

    return {"stress_level": stress_level, "confidence_score": confidence_score}
