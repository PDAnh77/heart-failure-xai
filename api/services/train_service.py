import io
import uuid
import pickle
import numpy as np
import pandas as pd
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from services.dataset_service import AVAILABLE_MODELS, load_dataset
from core.supabase_client import supabase
from datetime import datetime

MODEL_BUCKET = "heart-prediction-models"


def train_model_service(dataset_id: str, model_name: str, target_column: str, user: dict):
    user_id = user["user_id"]

    try:
        df = load_dataset(dataset_id, user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to load dataset: {str(e)}")

    if df.empty:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dataset is empty")

    if target_column not in df.columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Target column '{target_column}' not found in the dataset."
        )

    # Check for missing values
    if df.isnull().values.any():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dataset contains missing values. Please handle missing values before training.",
        )

    # Check if all features are numeric
    features = df.drop(columns=[target_column])
    if not all(pd.api.types.is_numeric_dtype(df[col]) for col in features.columns):
        non_numeric_cols = [col for col in features.columns if not pd.api.types.is_numeric_dtype(df[col])]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dataset contains non-numeric columns: {', '.join(non_numeric_cols)}. Please encode categorical variables.",
        )

    # Check if target column has at least two classes
    if df[target_column].nunique() < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target column must have at least 2 distinct classes for classification.",
        )

    if model_name not in AVAILABLE_MODELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{model_name}' is not supported. Available models: {list(AVAILABLE_MODELS.keys())}",
        )

    X = features
    y = df[target_column]

    # Check if enough samples
    if len(df) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Dataset must have at least 10 rows for training."
        )

    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        model = AVAILABLE_MODELS[model_name]

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        # Calculate metrics
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, average="weighted", zero_division=0)
        rec = recall_score(y_test, y_pred, average="weighted", zero_division=0)
        f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)

        # Cross validation score
        cv_scores = cross_val_score(model, X, y, cv=5)
        mean_cv_score = cv_scores.mean()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error during model training: {str(e)}"
        )

    # Create model id and upload to storage
    model_id = f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:6]}"
    model_bytes = pickle.dumps(model)
    path = f"{user_id}/{model_id}.pkl"

    try:
        supabase.storage.from_(MODEL_BUCKET).upload(
            path=path, file=model_bytes, file_options={"content-type": "application/octet-stream"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Upload trained model failed: {str(e)}"
        )

    return {
        "model_id": model_id,
        "model": model_name,
        "target_column": target_column,
        "accuracy": float(acc),
        "precision": float(prec),
        "recall": float(rec),
        "f1_score": float(f1),
        "cross_validation_score": float(mean_cv_score),
    }


def download_model_service(model_id: str, user: dict):
    user_id = user["user_id"]
    path = f"{user_id}/{model_id}.pkl"

    try:
        response = supabase.storage.from_(MODEL_BUCKET).download(path)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Model not found: {str(e)}")

    stream = io.BytesIO(response)
    resp = StreamingResponse(iter([stream.getvalue()]), media_type="application/octet-stream")
    resp.headers["Content-Disposition"] = f"attachment; filename={model_id}.pkl"
    return resp
