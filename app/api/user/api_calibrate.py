from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.repositories.user_repository import get_profile, recalculate_profile_status, update_baseline_bpm

router = APIRouter()


class CalibrateIn(BaseModel):
    baseline_bpm: int


@router.put("/user/profile/calibrate")
def calibrate_profile(body: CalibrateIn, current_user: dict = Depends(get_current_user)):
    if body.baseline_bpm < 30 or body.baseline_bpm > 220:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "INVALID_BPM_RANGE", "message": "baseline_bpm debe estar entre 30 y 220."},
        )
    user_id = current_user["user_id"]
    update_baseline_bpm(user_id=user_id, bpm=body.baseline_bpm)
    recalculate_profile_status(user_id=user_id)
    return get_profile(user_id=user_id)
