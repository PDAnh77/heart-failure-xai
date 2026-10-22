import io
import uuid
from datetime import datetime

import pandas as pd
from fastapi import HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from core.supabase_client import supabase
from core.config import settings

from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

DATASET_BUCKET = "heart-failure-datasets"
DEFAULT_FEATURE_SELECTION_MODEL = "decision_tree"

AVAILABLE_MODELS = {
    "svc": SVC(kernel="linear", C=0.1, probability=True),
    "logistic_regression": LogisticRegression(random_state=0, C=10, penalty="l2"),
    "random_forest": RandomForestClassifier(max_depth=4, random_state=0),
    "decision_tree": DecisionTreeClassifier(random_state=1000, max_depth=4, min_samples_leaf=1),
    "knn": KNeighborsClassifier(leaf_size=1, n_neighbors=3, p=1),
    "xgboost": XGBClassifier(
        random_state=0,
        n_estimators=50,
        max_depth=3,
        learning_rate=0.105,
        subsample=0.8,
        colsample_bytree=0.9,
        eval_metric="logloss",
    ),
    "lightgbm": LGBMClassifier(
        objective="binary",
        random_state=0,
        n_estimators=100,
        max_depth=4,
        num_leaves=15,
        min_child_samples=20,
        learning_rate=0.05,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.8,
        verbose=-1,
    ),
}


def _sanitize(obj):
    """
    Recursively replace nan/inf float values with None for JSON safety.
    """
    if isinstance(obj, float) and (obj != obj or obj == float("inf") or obj == float("-inf")):
        return None
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


def load_dataset(dataset_id: str, user_id: str) -> pd.DataFrame:
    if dataset_id.startswith("pred_"):
        path = f"batch-prediction/{user_id}/{dataset_id}.csv"
    elif dataset_id.startswith("fs_"):
        path = f"feature-selection/{user_id}/{dataset_id}.csv"
    elif dataset_id.startswith("processed_"):
        path = f"processed/{user_id}/{dataset_id}.csv"
    else:
        path = f"raw/{user_id}/{dataset_id}.csv"

    try:
        # 1. Download file from storage
        response = supabase.storage.from_(DATASET_BUCKET).download(path)
    except Exception:
        # File not found / storage error
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Dataset '{dataset_id}' not found or cannot be accessed"
        )

    try:
        # 2. Convert bytes → file-like object → DataFrame
        df = pd.read_csv(io.BytesIO(response))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to parse CSV file")

    # 3. Check empty dataset
    if df.empty:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dataset is empty")
    return df


def upload_raw_dataset(file: UploadFile, user_id: str):
    valid_extensions = (".csv", ".xlsx", ".xls")

    filename_lower = file.filename.lower()

    if not filename_lower.endswith(valid_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV and Excel files (.xlsx, .xls) are allowed"
        )

    original_file_type = "csv"
    if filename_lower.endswith(".xlsx"):
        original_file_type = "xlsx"
    elif filename_lower.endswith(".xls"):
        original_file_type = "xls"

    # Check file size
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    if size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    # Read file
    try:
        if file.filename.lower().endswith(".csv"):
            df = pd.read_csv(file.file)
        else:
            # Đọc file Excel
            df = pd.read_excel(file.file)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid file format or corrupted file: {str(e)}"
        )

    df = df.dropna(axis=1, how="all")

    cols_to_drop = []
    for col in df.columns:
        col_name_str = str(col).strip().lower()
        if "unnamed" in col_name_str:
            # Nếu cột unnamed trống hơn 90% => xóa
            if df[col].isna().mean() > 0.9:
                cols_to_drop.append(col)
                continue

        if (
            col_name_str in ["id", "name"]
            or col_name_str.endswith(" id")
            or col_name_str.endswith(" no")
            or col_name_str.endswith(" no.")
        ):
            cols_to_drop.append(col)

    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)

    # Dataset validation
    if df.empty:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dataset is empty")

    if df.shape[0] > 100000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Dataset too large (max 100000 rows allowed)"
        )

    if df.shape[1] > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Too many columns (max 100 allowed)")

    # Extract columns
    columns = df.columns.tolist()

    # Create dataset id
    dataset_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:6]}"

    # Chuẩn hóa tất cả dữ liệu thành CSV trước khi lưu lên Supabase
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    path = f"raw/{user_id}/{dataset_id}.csv"

    # Upload
    try:
        supabase.storage.from_(DATASET_BUCKET).upload(
            path=path, file=csv_bytes, file_options={"content-type": "text/csv"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Upload processed dataset failed: {str(e)}"
        )

    return {"dataset_id": dataset_id, "columns": columns, "original_file_type": original_file_type}


def get_summary(dataset_id: str, owner_id: str, user: dict, target_column: str = None):
    target_user_id = user["user_id"]

    if user["role"] == "admin" and owner_id:
        target_user_id = owner_id

    df = load_dataset(dataset_id, target_user_id)

    if target_column and target_column not in df.columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target column '{target_column}' not found. Available columns: {list(df.columns)}",
        )

    rows, cols = df.shape

    features_to_process = [col for col in df.columns if col != target_column]
    categorical_features = []
    numerical_features = []

    for column in features_to_process:
        if df[column].nunique() > 6:
            numerical_features.append(column)
        else:
            categorical_features.append(column)

    # ===== KIỂU DỮ LIỆU =====
    column_types = df.dtypes.astype(str).to_dict()

    # ===== GIÁ TRỊ THIẾU =====
    missing_values = df.isnull().sum().to_dict()

    return _sanitize(
        {
            "rows": rows,
            "columns": cols,
            "target_column": target_column,
            "categorical_features": categorical_features,
            "numerical_features": numerical_features,
            "column_types": column_types,
            "missing_values": missing_values,
        }
    )


def get_rows(dataset_id: str, owner_id: str, user: dict, limit: int, offset: int):
    target_user_id = user["user_id"]

    if user["role"] == "admin" and owner_id:
        target_user_id = owner_id

    df = load_dataset(dataset_id, target_user_id)

    total_rows = len(df)

    # 2. Thực hiện cắt dữ liệu (Slicing) theo limit và offset
    # Công thức: [vị trí bắt đầu : vị trí kết thúc]
    df_slice = df.iloc[offset : offset + limit]

    # 3. Xử lý giá trị NaN
    df_slice = df_slice.astype(object).where(pd.notnull(df_slice), None)

    # 4. Chuyển đổi sang list các dictionary
    data = df_slice.to_dict(orient="records")

    return {"total_rows": total_rows, "limit": limit, "offset": offset, "data": data}


def download(dataset_id: str, owner_id: str, user: dict, file_type: str):
    target_user_id = user["user_id"]

    if user["role"] == "admin" and owner_id:
        target_user_id = owner_id

    # Default to csv
    if not file_type:
        file_type = "csv"

    df = load_dataset(dataset_id, target_user_id)

    # Convert format
    if file_type.lower() in ["xlsx", "xls"]:
        stream = io.BytesIO()
        df.to_excel(stream, index=False, engine="openpyxl")
        stream.seek(0)

        response = StreamingResponse(
            iter([stream.getvalue()]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response.headers["Content-Disposition"] = f"attachment; filename={dataset_id}.xlsx"
    else:
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        stream.seek(0)

        response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = f"attachment; filename={dataset_id}.csv"

    return response
