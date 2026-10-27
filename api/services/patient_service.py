import random
import uuid
from pathlib import Path
import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import select, insert, update, delete, func
from models.patient_model import Patient
from schemas.patient_schema import PatientCreate, PatientUpdate
from sqlalchemy.orm import Session

DEFAULT_SAMPLE_PATIENTS = [
    {
        "age": 40,
        "sex": "M",
        "chest_pain_type": "ATA",
        "resting_bp": 140,
        "cholesterol": 289,
        "fasting_bs": 0,
        "resting_ecg": "Normal",
        "max_hr": 172,
        "exercise_angina": "N",
        "oldpeak": 0.0,
        "st_slope": "Up",
        "heart_disease": 0,
    },
    {
        "age": 49,
        "sex": "F",
        "chest_pain_type": "NAP",
        "resting_bp": 160,
        "cholesterol": 180,
        "fasting_bs": 0,
        "resting_ecg": "Normal",
        "max_hr": 156,
        "exercise_angina": "N",
        "oldpeak": 1.0,
        "st_slope": "Flat",
        "heart_disease": 1,
    },
    {
        "age": 54,
        "sex": "M",
        "chest_pain_type": "ASY",
        "resting_bp": 140,
        "cholesterol": 239,
        "fasting_bs": 0,
        "resting_ecg": "Normal",
        "max_hr": 160,
        "exercise_angina": "N",
        "oldpeak": 1.2,
        "st_slope": "Up",
        "heart_disease": 0,
    },
    {
        "age": 63,
        "sex": "M",
        "chest_pain_type": "ASY",
        "resting_bp": 150,
        "cholesterol": 220,
        "fasting_bs": 1,
        "resting_ecg": "ST",
        "max_hr": 144,
        "exercise_angina": "Y",
        "oldpeak": 2.5,
        "st_slope": "Flat",
        "heart_disease": 1,
    },
]


def check_uuid(id: str):
    try:
        validated_uuid = str(uuid.UUID(id))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID format")
    return validated_uuid


def get_patients(db: Session, limit: int, offset: int):
    result = db.execute(select(Patient).offset(offset).limit(limit)).scalars().all()
    return {"data": result, "count": len(result)}


def get_random_patient(db: Session):
    # Lấy từ bảng patients trong database
    result = db.execute(select(Patient).order_by(func.random()).limit(1)).scalars().first()
    if result:
        return result

    # Fallback vào danh sách mẫu mặc định
    chosen = random.choice(DEFAULT_SAMPLE_PATIENTS)
    return {
        "id": uuid.uuid4(),
        **chosen,
    }


def get_patient_by_id(db: Session, patient_id: str, user: dict):
    patient_uuid = check_uuid(patient_id)

    stmt = select(Patient).where(Patient.id == patient_uuid)

    if user["role"] != "admin":
        stmt = stmt.where(Patient.user_id == user["user_id"])

    patient = db.execute(stmt).scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


def get_patients_by_user(db: Session, user_id: str, limit: int, offset: int):
    user_uuid = check_uuid(user_id)
    patients = (
        db.execute(select(Patient).where(Patient.user_id == user_uuid).offset(offset).limit(limit)).scalars().all()
    )
    return patients


def create_patient_service(db: Session, new_patient: PatientCreate, user_id: str):
    patient_data = new_patient.model_dump()
    patient_data["user_id"] = user_id

    result = db.execute(insert(Patient).values(patient_data).returning(Patient))
    patient_obj = result.scalar_one()
    db.commit()
    db.refresh(patient_obj)
    return patient_obj


def update_patient(db: Session, patient_id: str, patient: PatientUpdate, user: dict):
    patient_uuid = check_uuid(patient_id)
    update_data = patient.model_dump(exclude_unset=True)

    stmt = update(Patient).where(Patient.id == patient_uuid)
    if user["role"] != "admin":
        stmt = stmt.where(Patient.user_id == user["user_id"])

    result = db.execute(stmt.values(update_data).returning(Patient))
    patient_obj = result.scalar_one_or_none()

    if not patient_obj:
        raise HTTPException(status_code=404, detail="Patient not found")

    db.commit()
    return patient_obj


def delete_patient(db: Session, patient_id: str, user: dict):
    patient_uuid = check_uuid(patient_id)

    stmt = delete(Patient).where(Patient.id == patient_uuid)
    if user["role"] != "admin":
        stmt = stmt.where(Patient.user_id == user["user_id"])

    result = db.execute(stmt)

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Patient not found")

    db.commit()
    return {"detail": "Delete patient successfully"}


def delete_patients_by_user(db: Session, user_id: str):
    user_uuid = check_uuid(user_id)

    db.execute(delete(Patient).where(Patient.user_id == user_uuid))
    db.commit()
    return {"detail": "Delete patients successfully"}
