import os
from datetime import datetime


def validate_bpm(value: object) -> bool:
    try:
        bpm = float(value)
    except (TypeError, ValueError):
        return False
    return 30.0 <= bpm <= 220.0


def validate_timestamp(value: object) -> bool:
    if value is None:
        return False
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
    ):
        try:
            datetime.strptime(str(value).strip(), fmt)
            return True
        except ValueError:
            continue
    return False


def validate_csv_filename(name: str) -> bool:
    return (
        bool(name)
        and os.sep not in name
        and "/" not in name
        and "\\" not in name
        and name == os.path.basename(name)
    )
