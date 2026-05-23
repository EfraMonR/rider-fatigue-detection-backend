import io

import pandas as pd

from app.utils.validators import validate_bpm, validate_timestamp

# Columnas que identifican formato Apple Health
APPLE_HEALTH_COLUMNS = {"timestamp", "type", "value", "unit", "sourceName", "sourceVersion"}
APPLE_HEALTH_HR_TYPE = "HKQuantityTypeIdentifierHeartRate"

# Candidatos para columna de BPM en formato simple
HR_COLUMN_CANDIDATES = ["bpm", "heart_rate", "heartrate", "hr", "ritmo",
                        "frecuencia_cardiaca", "FC", "HeartRate", "value"]

# Candidatos para columna de timestamp en formato simple
TS_COLUMN_CANDIDATES = ["timestamp", "time", "fecha", "date", "datetime"]

_MAX_NROWS = 1_000_000


class ETLError(Exception):
    """Error estructurado del pipeline ETL."""
    def __init__(self, error_code: str, message: str, extra: dict | None = None):
        self.error_code = error_code
        self.message = message
        self.extra = extra or {}
        super().__init__(error_code)


def _detect_format(df: pd.DataFrame) -> str:
    cols = set(df.columns)
    if APPLE_HEALTH_COLUMNS.issubset(cols):
        return "apple_health"

    hr_matches = [c for c in HR_COLUMN_CANDIDATES if c in cols]
    if len(hr_matches) == 1:
        return "simple"
    if len(hr_matches) > 1:
        raise ETLError(
            "COLUMN_SELECTION_REQUIRED",
            "No se pudo identificar la columna de ritmo cardíaco. Seleccioná la columna correcta.",
            {"columns": hr_matches},
        )
    raise ETLError(
        "COLUMN_SELECTION_REQUIRED",
        "No se pudo identificar la columna de ritmo cardíaco. Seleccioná la columna correcta.",
        {"columns": list(df.columns)},
    )


def _extract_series(df: pd.DataFrame, fmt: str, hr_column: str | None = None) -> list[tuple]:
    if fmt == "apple_health":
        df = df[df["type"] == APPLE_HEALTH_HR_TYPE][["timestamp", "value"]].copy()
        df.columns = ["_ts", "_bpm"]
    else:
        cols = set(df.columns)
        hr_col = hr_column or next(c for c in HR_COLUMN_CANDIDATES if c in cols)
        ts_col = next((c for c in TS_COLUMN_CANDIDATES if c in cols), None)
        if ts_col is None:
            raise ETLError("NO_TIMESTAMP_COLUMN", "El archivo no contiene una columna de timestamp reconocible.")
        df = df[[ts_col, hr_col]].copy()
        df.columns = ["_ts", "_bpm"]

    return list(zip(df["_ts"].astype(str), df["_bpm"]))


def _filter_series(raw: list[tuple]) -> dict:
    series: list[dict] = []
    rejected: list[dict] = []

    for i, (ts, bpm) in enumerate(raw):
        row_num = i + 2  # fila 1 = encabezado

        if not validate_timestamp(ts):
            rejected.append({"row": row_num, "reason": "INVALID_TIMESTAMP", "value": str(ts)})
            continue

        if not validate_bpm(bpm):
            try:
                val = float(bpm)
                reason = "BPM_OUT_OF_RANGE"
            except (TypeError, ValueError):
                val = bpm
                reason = "INVALID_BPM"
            rejected.append({"row": row_num, "reason": reason, "value": val})
            continue

        series.append({"timestamp": str(ts).strip(), "bpm": float(bpm)})

    series.sort(key=lambda x: x["timestamp"])
    return {"series": series, "rejected_rows": rejected}


def run_etl(file_bytes: bytes, filename: str, hr_column: str | None = None) -> dict:
    """
    Devuelve {"series": [...], "rejected_rows": [...]}.
    Lanza ETLError si el archivo es inválido o no hay filas válidas.
    """
    try:
        df = pd.read_csv(io.BytesIO(file_bytes), nrows=_MAX_NROWS)
    except Exception as exc:
        raise ETLError("PARSE_ERROR", f"No se pudo parsear el archivo: {exc}") from exc

    if df.empty:
        raise ETLError("NO_VALID_ROWS", "El archivo no contiene datos de ritmo cardíaco válidos tras el filtrado.")

    if hr_column:
        if hr_column not in df.columns:
            raise ETLError("COLUMN_NOT_FOUND", f"La columna '{hr_column}' no existe en el archivo.")
        fmt = "simple"
    else:
        fmt = _detect_format(df)

    raw = _extract_series(df, fmt, hr_column=hr_column)
    result = _filter_series(raw)

    if not result["series"]:
        raise ETLError("NO_VALID_ROWS", "El archivo no contiene datos de ritmo cardíaco válidos tras el filtrado.")

    return result
