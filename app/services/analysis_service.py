from app.config import settings
from app.models_ai import inference_engine
from app.repositories import audit_repository, biometric_repository, session_repository, user_repository
from app.services import weather_service
from app.utils.logging import get_logger

logger = get_logger(__name__)
_audit_available = True

# Banda de risk_score por nivel de estrés — Low < Moderate < High siempre
_RISK_BANDS: dict[str, tuple[int, int]] = {
    "Low":      (0,  33),
    "Moderate": (34, 66),
    "High":     (67, 100),
}


def _compute_risk_score(stress_level: str, confidence_score: float) -> float:
    base, top = _RISK_BANDS[stress_level]
    return round(base + confidence_score * (top - base), 1)


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


async def process(
    user_id: str,
    series: list[dict],
    baseline_bpm: int | None = None,
    lat: float | None = None,
    lon: float | None = None,
    tags: list[str] | None = None,
) -> dict:
    """
    Orquesta: inferencia → traffic_light → weather_impact → persistencia → audit log.
    No usa BackgroundTasks. Procesamiento síncrono (async solo por weather HTTP call).
    """
    bpms = [row["bpm"] for row in series]
    bpm_mean = sum(bpms) / len(bpms)
    effective_baseline = baseline_bpm or settings.DEFAULT_BASELINE_BPM

    try:
        inference_result = inference_engine.run_inference(series)
    except Exception as exc:
        # model_failure: evento específico requerido por RF-008
        _log_event(user_id, "model_failure", "Error", str(type(exc).__name__))
        raise

    stress_level = inference_result["stress_level"]
    confidence_score = inference_result["confidence_score"]
    traffic_light, verdict = _determine_traffic_light(stress_level, bpm_mean, effective_baseline)

    # Weather enrichment — no modifica el semáforo, solo contextualiza
    weather_snapshot: dict = {}
    weather_impact = None
    if lat is not None and lon is not None:
        try:
            weather_data = await weather_service.get_weather(lat, lon)
            # M-5: marcar explícitamente cuando solo hay datos de fallback
            if weather_data.get("warning"):
                weather_data["source"] = "fallback"
            weather_snapshot = weather_data
            weather_impact = weather_service.generate_weather_impact(weather_data)
        except Exception as exc:
            logger.error("Weather enrichment failed: %s", type(exc).__name__)

    risk_score = _compute_risk_score(stress_level, confidence_score)

    result = {
        "verdict": verdict,
        "stress_level": stress_level,
        "traffic_light": traffic_light,
        "confidence_score": int(round(confidence_score * 100)),  # H-3: siempre int 0–100
        "bpm_mean": round(bpm_mean, 2),
        "risk_score": risk_score,
        "weather_snapshot": weather_snapshot,
        "weather_impact": weather_impact,
        "tags": tags or [],
        "rejected_rows": [],  # se sobreescribe desde el endpoint con el valor del ETL
    }

    session_id = session_repository.create_session(user_id, result)
    biometric_repository.save_biometric_series(session_id, series)
    user_repository.recalculate_profile_status(user_id)  # H-2: actualizar estado tras cada sesión

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
