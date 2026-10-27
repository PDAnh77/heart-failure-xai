from fastapi import APIRouter, Depends, Query, HTTPException, status
from services.auth_service import require_roles
from services import train_service

router = APIRouter()


@router.post("")
def train_model(
    dataset_id: str = Query(..., description="ID of the dataset to train on"),
    model_name: str = Query(..., description="Name of the model to train (e.g., svc, random_forest)"),
    target_column: str = Query(..., description="Target column name for prediction"),
    user=Depends(require_roles(["admin", "user"])),
):
    """
    Train a model using an existing dataset.
    Returns evaluation metrics: accuracy, precision, recall, f1-score, and cross-validation score.
    """
    return train_service.train_model_service(dataset_id, model_name, target_column, user)


@router.get("/{model_id}/download")
def download_model(model_id: str, user=Depends(require_roles(["admin", "user"]))):
    """
    Download a trained model as a .pkl file.
    """
    return train_service.download_model_service(model_id, user)
