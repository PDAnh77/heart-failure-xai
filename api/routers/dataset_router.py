from typing import Literal
from fastapi import BackgroundTasks, APIRouter, Depends, Query, UploadFile
from services.auth_service import require_roles

from services import dataset_service, preprocessing_service, eda_service, feature_selection_service, xai_service

router = APIRouter()


@router.post("/upload")
def upload_dataset(file: UploadFile, user=Depends(require_roles(["admin", "user"]))):
    return dataset_service.upload_raw_dataset(file, user["user_id"])


@router.get("/{dataset_id}/summary")
def get_dataset_summary(
    dataset_id: str,
    target_column: str = Query(None),
    owner_id: str = Query(None),
    user=Depends(require_roles(["admin", "user"])),
):
    return dataset_service.get_summary(dataset_id, owner_id, user, target_column)


@router.get("/{dataset_id}/rows")
def get_dataset_rows(
    dataset_id: str,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    owner_id: str = Query(None),
    user=Depends(require_roles(["admin", "user"])),
):
    return dataset_service.get_rows(dataset_id, owner_id, user, limit, offset)


@router.post("/{dataset_id}/preprocess")
def preprocess_dataset(
    dataset_id: str,
    target_column: str,
    imputation_method: Literal["default", "mice", "mean", "knn"] = Query(
        "default",
        description="Choose 'default' (Median/Mode), 'mice' (Mean/Mode for <=5% missing values and MICE for >5%), 'mean' (Average Mean), or 'knn' (K-Nearest Neighbors)",
    ),
    owner_id: str = Query(None),
    user=Depends(require_roles(["admin", "user"])),
):
    return preprocessing_service.preprocess(dataset_id, owner_id, user, target_column, imputation_method)


@router.get("/{dataset_id}/download")
def download_dataset(
    dataset_id: str,
    owner_id: str = Query(None),
    file_type: str = Query(None),
    user=Depends(require_roles(["admin", "user"])),
):
    return dataset_service.download(dataset_id, owner_id, user, file_type)


@router.get("/{dataset_id}/eda", dependencies=[Depends(require_roles(["admin", "user"]))])
def get_dataset_eda(
    dataset_id: str,
    target_column: str,
    owner_id: str = Query(None),
    user=Depends(require_roles(["admin", "user"])),
):
    return eda_service.get_eda(dataset_id, target_column, owner_id, user)


@router.get("/feature-selection/status/{task_id}")
def check_feature_selection_status(task_id: str):
    """
    API dùng để Frontend gọi liên tục (mỗi 3-5s) để lấy kết quả thuật toán
    """
    # Hàm này sẽ trả về {"status": "COMPLETED", "result": {...}} khi chạy xong
    return feature_selection_service.get_task_status(task_id)


@router.post("/{dataset_id}/feature-selection")
def dataset_feature_selection(
    dataset_id: str,
    target_column: str = Query(...),
    background_tasks: BackgroundTasks = None,
    size: int = Query(80, ge=10, le=200),
    n_gen: int = Query(10, ge=1, le=50),
    mutation_rate: float = Query(0.2, ge=0.01, le=0.5),
    n_parents: int = Query(None),
    owner_id: str = Query(None),
    user=Depends(require_roles(["admin", "user"])),
    model_name: str = Query(None),
    test_size: float = Query(0.3, ge=0.1, le=0.5),
    balancing_method: Literal["none", "smote", "adasyn"] = Query(
        "none",
        description="Choose a data balancing method: 'none' (no balancing applied), 'smote' (SMOTE oversampling), or 'adasyn' (ADASYN oversampling)",
    ),
):
    # Khởi tạo một Task ID mới và lưu trạng thái vào RAM/DB
    task_id = feature_selection_service.create_task()

    # Đưa hàm wrapper chạy ngầm vào hàng đợi của FastAPI
    background_tasks.add_task(
        feature_selection_service.background_genetic_selection,
        task_id=task_id,
        dataset_id=dataset_id,
        target_column=target_column,
        owner_id=owner_id,
        user=user,
        size=size,
        n_gen=n_gen,
        mutation_rate=mutation_rate,
        n_parents=n_parents,
        model_name=model_name,
        test_size=test_size,
        balancing_method=balancing_method,
    )

    # Trả kết quả cho Frontend mà không cần đợi thuật toán thực thi
    return {"message": "Feature selection started in the background", "task_id": task_id, "status": "PROCESSING"}


@router.post("/{dataset_id}/feature-selection-evaluation")
def dataset_feature_selection_evaluation(
    dataset_id: str,
    background_tasks: BackgroundTasks,
    fs_dataset_id: str = Query(...),
    target_column: str = Query(...),
    owner_id: str = Query(None),
    user=Depends(require_roles(["admin", "user"])),
    model_name: str = Query(None),
    test_size: float = Query(0.3, ge=0.1, le=0.5),
    balancing_method: Literal["none", "smote", "adasyn"] = Query("none"),
):
    # Tạo Task ID mới
    task_id = feature_selection_service.create_task()

    # Đưa tác vụ nặng vào chạy ngầm
    background_tasks.add_task(
        feature_selection_service.background_evaluate_feature_selection,
        task_id=task_id,
        dataset_id=dataset_id,
        fs_dataset_id=fs_dataset_id,
        target_column=target_column,
        owner_id=owner_id,
        user=user,
        model_name=model_name,
        test_size=test_size,
        balancing_method=balancing_method,
    )

    # Trả về ngay lập tức
    return {"message": "Evaluation started in the background", "task_id": task_id, "status": "PROCESSING"}


@router.get("/{dataset_id}/feature-selection-evaluation/lime")
def get_standalone_lime_explanation(
    dataset_id: str,
    fs_dataset_id: str,
    target_column: str,
    instance_idx: int = Query(..., ge=0, description="Exact index of the row to explain"),
    model_name: str = Query(None),
    test_size: float = Query(0.3, ge=0.1, le=0.5),
    owner_id: str = Query(None),
    user=Depends(require_roles(["admin", "user"])),
):
    return xai_service.generate_lime_explanation(
        dataset_id=dataset_id,
        fs_dataset_id=fs_dataset_id,
        target_column=target_column,
        owner_id=owner_id,
        user=user,
        model_name=model_name,
        test_size=test_size,
        instance_idx=instance_idx,
    )
