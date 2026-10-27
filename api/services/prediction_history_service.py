import uuid
from fastapi import HTTPException, status
from sqlalchemy import delete, select, literal, union_all
from sqlalchemy.orm import Session

from models.user_model import User
from models.prediction_model import Prediction
from models.batch_prediction_model import BatchPrediction


def check_uuid(id: str):
    """
    Utility function to validate UUID.
    Kept here to ensure this service is self-contained.
    """
    try:
        validated_uuid = str(uuid.UUID(id))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID format")
    return validated_uuid


def get_unified_prediction_history(db: Session, user_id: str, limit: int, offset: int):
    user_uuid = check_uuid(user_id)

    # Query từ bảng Single Prediction
    stmt_single = select(Prediction.id, literal("single").label("type"), Prediction.created_at).where(
        Prediction.user_id == user_uuid
    )

    # Query từ bảng Batch Prediction
    stmt_batch = select(BatchPrediction.id, literal("batch").label("type"), BatchPrediction.created_at).where(
        BatchPrediction.user_id == user_uuid
    )

    # Gộp 2 query lại bằng UNION ALL
    union_stmt = union_all(stmt_single, stmt_batch).subquery()

    # Truy vấn trên bảng ảo vừa gộp, sắp xếp và phân trang
    final_stmt = (
        select(union_stmt.c.id, union_stmt.c.type, union_stmt.c.created_at)
        .order_by(union_stmt.c.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    results = db.execute(final_stmt).mappings().all()
    return results


def get_predictions_by_user(db: Session, user_id: str, limit: int, offset: int):
    user_uuid = check_uuid(user_id)
    result = (
        db.execute(
            select(Prediction)
            .where(Prediction.user_id == user_uuid)
            .order_by(Prediction.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")
    return result


def get_prediction_by_id(db: Session, prediction_id: str, user: dict):
    prediction_uuid = check_uuid(prediction_id)

    if user["role"] == "admin":
        result = db.execute(select(Prediction).where(Prediction.id == prediction_uuid)).scalar_one_or_none()
    else:
        result = db.execute(
            select(Prediction).where(Prediction.id == prediction_uuid).where(Prediction.user_id == user["user_id"])
        ).scalar_one_or_none()

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")
    return result


def get_batch_predictions_by_user(db: Session, user_id: str, limit: int, offset: int):
    user_uuid = check_uuid(user_id)
    result = (
        db.execute(
            select(BatchPrediction)
            .where(BatchPrediction.user_id == user_uuid)
            .order_by(BatchPrediction.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch predictions not found")
    return result


def get_batch_prediction_by_id(db: Session, batch_id: str, user: dict):
    batch_uuid = check_uuid(batch_id)

    if user["role"] == "admin":
        result = db.execute(select(BatchPrediction).where(BatchPrediction.id == batch_uuid)).scalar_one_or_none()
    else:
        result = db.execute(
            select(BatchPrediction)
            .where(BatchPrediction.id == batch_uuid)
            .where(BatchPrediction.user_id == check_uuid(user["user_id"]))
        ).scalar_one_or_none()

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch prediction not found")
    return result


def delete_prediction_by_id(db: Session, prediction_id: str, user: dict):
    prediction_uuid = check_uuid(prediction_id)

    stmt = delete(Prediction).where(Prediction.id == prediction_uuid)

    if user["role"] != "admin":
        stmt = stmt.where(Prediction.user_id == user["user_id"])

    result = db.execute(stmt)
    db.commit()

    if result.rowcount <= 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")

    return {"detail": "Delete user prediction successfully"}


def delete_predictions_by_user(db: Session, user_id: str):
    user_uuid = check_uuid(user_id)

    user = db.execute(select(User.id).where(User.id == user_uuid)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    db.execute(delete(Prediction).where(Prediction.user_id == user_uuid))
    db.commit()
    return {"detail": "User predictions deleted successfully"}


def delete_batch_prediction_by_id(db: Session, batch_id: str, user: dict):
    batch_uuid = check_uuid(batch_id)

    stmt = delete(BatchPrediction).where(BatchPrediction.id == batch_uuid)

    if user["role"] != "admin":
        stmt = stmt.where(BatchPrediction.user_id == user["user_id"])

    result = db.execute(stmt)
    db.commit()

    if result.rowcount <= 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch prediction not found")

    return {"detail": "Delete batch prediction successfully"}
