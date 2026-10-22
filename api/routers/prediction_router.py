from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query
from schemas.prediction_schema import PredictionBase, PredictionGet, UnifiedHistoryItem
from schemas.batch_prediction_schema import BatchPredictionList, BatchPredictionDetail
from services.auth_service import require_roles
from dependencies import get_db
from sqlalchemy.orm import Session
from schemas.patient_schema import PatientBase, PatientPredict

from services.prediction_service import predict_dataframe, predict_single, predict_batch
from services.prediction_history_service import (
    get_predictions_by_user,
    get_prediction_by_id,
    get_batch_predictions_by_user,
    get_batch_prediction_by_id,
    get_unified_prediction_history,
    delete_prediction_by_id,
    delete_predictions_by_user,
    delete_batch_prediction_by_id,
)
from services.xai_service import generate_single_xai

router = APIRouter()


@router.get("/history/me", response_model=List[UnifiedHistoryItem])
def get_user_mixed_history(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user=Depends(require_roles(["admin", "user"])),
    db: Session = Depends(get_db),
):
    return get_unified_prediction_history(db, user["user_id"], limit, offset)


@router.get("/me", response_model=List[PredictionBase])
def get_user_predictions_me(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user: str = Depends(require_roles(["admin", "user"])),
    db: Session = Depends(get_db),
):
    return get_predictions_by_user(db, user["user_id"], limit, offset)


@router.get("/batch/me", response_model=List[BatchPredictionList])
def get_user_batch_predictions_me(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user=Depends(require_roles(["admin", "user"])),
    db: Session = Depends(get_db),
):
    return get_batch_predictions_by_user(db, user["user_id"], limit, offset)


@router.get("/users/{user_id}", dependencies=[Depends(require_roles(["admin"]))])
def get_user_predictions_admin(
    user_id: str, limit: int = Query(10, ge=1, le=50), offset: int = Query(0, ge=0), db: Session = Depends(get_db)
):
    return get_predictions_by_user(db, user_id, limit, offset)


@router.get("/batch/{batch_id}", response_model=BatchPredictionDetail)
def get_batch_prediction(batch_id: str, user=Depends(require_roles(["admin", "user"])), db: Session = Depends(get_db)):
    return get_batch_prediction_by_id(db, batch_id, user)


@router.get("/{prediction_id}", response_model=PredictionGet)
def get_prediction(prediction_id: str, user=Depends(require_roles(["admin", "user"])), db: Session = Depends(get_db)):
    return get_prediction_by_id(db, prediction_id, user)


@router.post("")
def create_prediction(
    patient: PatientPredict, user=Depends(require_roles(["admin", "user"])), db: Session = Depends(get_db)
):
    return predict_single(db, patient, user["user_id"])


@router.post("/batch", dependencies=[Depends(require_roles(["admin"]))])
def create_batch_prediction(patients: List[PatientBase]):
    return predict_batch(patients)


@router.post("/upload/{dataset_id}")
def create_prediction_from_file(
    dataset_id: str,
    user=Depends(require_roles(["admin", "user"])),
    db: Session = Depends(get_db),
):
    return predict_dataframe(db, dataset_id, user["user_id"])


@router.post("/xai/on-demand", dependencies=[Depends(require_roles(["admin", "user"]))])
def create_xai_on_demand(patient_raw: Dict[str, Any]):
    return generate_single_xai(patient_raw)


@router.delete("/me")
def delete_user_predictions_me(user=Depends(require_roles(["admin", "user"])), db: Session = Depends(get_db)):
    return delete_predictions_by_user(db, user["user_id"])


@router.delete("/users/{user_id}", dependencies=[Depends(require_roles(["admin"]))])
def delete_user_predictions_admin(user_id: str, db: Session = Depends(get_db)):
    return delete_predictions_by_user(db, user_id)


@router.delete("/batch/{batch_id}")
def delete_batch_prediction(
    batch_id: str, user=Depends(require_roles(["admin", "user"])), db: Session = Depends(get_db)
):
    return delete_batch_prediction_by_id(db, batch_id, user)


@router.delete("/{prediction_id}")
def delete_prediction(
    prediction_id: str, user=Depends(require_roles(["admin", "user"])), db: Session = Depends(get_db)
):
    return delete_prediction_by_id(db, prediction_id, user)
