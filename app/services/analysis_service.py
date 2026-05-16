from app.config import settings
from app.models_ai import inference_engine
from app.repositories import biometric_repository, session_repository
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Importación lazy de audit_repository (se crea en Fase 5D)
_audit_available = False
try:
    from app.repositories import audit_repository
    _audit_available = True
except ImportError:
    pass


def _determine_traffic_light(stress_level: str, bpm_mean: float, baseline_bpm: int) -> tuple[str, str]:
    """
    El traffic_light lo determina exclusivamente el clúster fisiológico.
    baseline_bpm se usa post-inferencia para ajustar si el bpm_mean está muy por debajo del basal.
    """
    if stress_level == "High":
        return "Red", "Unfit"
    if stress_level == "Moderate":
        # Ajuste post-inferencia: si el BPM está muy por debajo del basal, bajar a Green
        if baseline_bpm and bpm_mean < baseline_bpm * 0.85:
            return "Green", "Fit"
        return "Yellow", "Fit"
    return "Green", "Fit"


def process(
    user_id: str,
    series: list[dict],
    baseline_bpm: int | None = None,
    lat: float | None = None,
    lon: float | None = None,
) -> dict:
    """
    Orquesta: inferencia → traffic_light → persistencia → audit log.
    No usa BackgroundTasks. Procesamiento síncrono.
    """
    bpms = [row["bpm"] for row in series]
    bpm_mean = sum(bpms) / len(bpms)
    effective_baseline = baseline_bpm or settings.DEFAULT_BASELINE_BPM

    try:
        inference_result = inference_engine.run_inference(series)
    except Exception as exc:
        _log_event(user_id, "upload", "Error", str(type(exc).__name__))
        raise

    stress_level = inference_result["stress_level"]
    confidence_score = inference_result["confidence_score"]
    traffic_light, verdict = _determine_traffic_light(stress_level, bpm_mean, effective_baseline)

    # weather_impact se integra en Fase 4A; por ahora es null
    weather_impact = None
    weather_snapshot: dict = {}

    risk_score = round(confidence_score * 100, 1) if stress_level == "High" else round(confidence_score * 50, 1)

    result = {
        "verdict": verdict,
        "stress_level": stress_level,
        "traffic_light": traffic_light,
        "confidence_score": confidence_score,
        "confidence_score_pct": int(round(confidence_score * 100)),  # valor expuesto en API (0–100)
        "risk_score": risk_score,
        "weather_snapshot": weather_snapshot,
        "weather_impact": weather_impact,
        "tags": [],
        "rejected_rows": [],  # se sobreescribe desde el endpoint con el valor del ETL
    }

    session_id = session_repository.create_session(user_id, result)
    biometric_repository.save_biometric_series(session_id, series)

    _log_event(user_id, "upload", "Success")
    logger.info("Analysis complete session_id=%s stress=%s", session_id, stress_level)

    result["session_id"] = session_id
    return result


def _log_event(user_id: str, event_type: str, model_status: str, error_message: str | None = None) -> None:
    if not _audit_available:
        return
    try:
        audit_repository.log_event(
            user_id=user_id,
            event_type=event_type,
            model_status=model_status,
            error_message=error_message,
        )
    except Exception:
        pass
