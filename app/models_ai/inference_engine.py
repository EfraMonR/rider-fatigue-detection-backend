import numpy as np

from app.config import settings
from app.models_ai.model_loader import ModelNotAvailableError, get_model
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _compute_features(series: list[dict]) -> np.ndarray:
    bpms = np.array([row["bpm"] for row in series], dtype=float)
    # Pipeline(StandardScaler + KMeans) trained on 1D — pass raw [[bpm_mean]]
    return np.array([[bpms.mean()]])


_STRESS_LEVELS = ["Low", "Moderate", "High"]


def _build_cluster_stress_map(model) -> dict[int, int]:
    """
    Devuelve {cluster_label: stress_index} ordenando clústeres por centroide ascendente.
    KMeans no garantiza orden de etiquetas; este mapeo lo corrige en tiempo de inferencia.
    """
    kmeans = model[-1]
    centers = kmeans.cluster_centers_  # shape (n_clusters, 1) en espacio escalado
    sorted_labels = sorted(range(len(centers)), key=lambda i: centers[i][0])
    return {label: stress_idx for stress_idx, label in enumerate(sorted_labels)}


def _cluster_to_stress(stress_index: int, n_clusters: int) -> tuple[str, float]:
    """Mapea stress_index ordenado → stress_level y confidence_score."""
    ratio = stress_index / max(n_clusters - 1, 1)
    level = _STRESS_LEVELS[min(stress_index, len(_STRESS_LEVELS) - 1)]
    if ratio < settings.STRESS_THRESHOLD_MODERATE:
        return level, round(1.0 - ratio, 2)
    if ratio < settings.STRESS_THRESHOLD_HIGH:
        return level, round(0.5 + (ratio - settings.STRESS_THRESHOLD_MODERATE) * 0.5, 2)
    return level, round(ratio, 2)


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
        n_clusters = int(model[-1].n_clusters)  # Pipeline: last step is KMeans
        cluster_map = _build_cluster_stress_map(model)
        stress_index = cluster_map[cluster_label]
    except Exception as exc:
        logger.error("Inference failed: %s", type(exc).__name__)
        raise ModelNotAvailableError("Inference error") from exc

    stress_level, confidence_score = _cluster_to_stress(stress_index, n_clusters)
    logger.info("Inference complete stress_level=%s cluster=%d→stress_idx=%d", stress_level, cluster_label, stress_index)

    return {"stress_level": stress_level, "confidence_score": confidence_score}
