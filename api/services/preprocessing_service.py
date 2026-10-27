import pandas as pd
from fastapi import HTTPException, status
from sklearn.preprocessing import LabelEncoder, StandardScaler

# Các thư viện cho nội suy dữ liệu (Imputation)
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer, KNNImputer

from core.supabase_client import supabase
from services.dataset_service import load_dataset, DATASET_BUCKET


def preprocess(dataset_id: str, owner_id: str, user: dict, target_column, imputation_method: str = "standard"):
    target_user_id = user["user_id"]

    if user["role"] == "admin" and owner_id:
        target_user_id = owner_id

    # 1. Load dữ liệu
    df = load_dataset(dataset_id, target_user_id)

    if target_column and target_column not in df.columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target column '{target_column}' not found. Available columns: {list(df.columns)}",
        )

    if target_column and target_column in df.columns:
        df = df.dropna(subset=[target_column])

    # 2. Xử lý giá trị trùng lặp (Duplicates)
    rows_before = len(df)
    df = df.drop_duplicates()
    duplicates_removed = rows_before - len(df)

    features_to_process = [col for col in df.columns if col != target_column]

    # Phân loại cột
    categorical_features = []
    numerical_features = []
    unprocessed_columns = []

    for col in features_to_process:
        # Attempt to convert the column to numeric. Invalid parsing will be set as NaN.
        temp_numeric = pd.to_numeric(df[col], errors="coerce")

        # If more than 50% of the data is valid numbers, it is safe to assume it's a numeric column
        if temp_numeric.notna().mean() > 0.5:
            df[col] = temp_numeric
            is_numeric = True
        else:
            is_numeric = pd.api.types.is_numeric_dtype(df[col])

        # Recalculate unique count after potential coercion
        unique_count = df[col].nunique()

        if is_numeric and unique_count > 6:
            numerical_features.append(col)
        elif not is_numeric and unique_count > 15:
            unprocessed_columns.append(col)
        else:
            categorical_features.append(col)

    if unprocessed_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": f"Some columns cannot be preprocessed: {', '.join(unprocessed_columns)}"},
        )

    le = LabelEncoder()  # Khởi tạo LabelEncoder dùng chung cho cả 2 phương pháp

    if imputation_method == "mice":
        # Lấy tỷ lệ thiếu để áp dụng đúng phương pháp cho từng cột
        missing_percentages = df[features_to_process].isnull().mean() * 100
        cols_missing_under_5 = missing_percentages[
            (missing_percentages > 0) & (missing_percentages <= 5)
        ].index.tolist()
        cols_missing_over_5 = missing_percentages[missing_percentages > 5].index.tolist()

        # 3.1 Xử lý các cột thiếu <= 5% (Mean cho Numeric, Mode cho Categorical)
        for col in cols_missing_under_5:
            if col in numerical_features:
                df[col] = df[col].fillna(df[col].mean())
            else:
                df[col] = df[col].fillna(df[col].mode()[0])

        # 3.2 Label Encode cho non-null values để thuật toán MICE có thể chạy được
        for col in categorical_features:
            non_nulls = df[col].dropna()
            if not non_nulls.empty:
                df.loc[df[col].notnull(), col] = le.fit_transform(non_nulls.astype(str))

        # 3.3 Áp dụng MICE cho các biến thiếu > 5%
        if len(cols_missing_over_5) > 0:
            mice_imputer = IterativeImputer(max_iter=10, random_state=0)
            df[features_to_process] = mice_imputer.fit_transform(df[features_to_process])

            # MICE có thể tạo số thập phân cho biến phân loại, nên cần làm tròn
            for col in categorical_features:
                df[col] = df[col].round()

    elif imputation_method == "mean":
        # Áp dụng Average Estimated Method: Dùng trung bình (Mean) cho số, Mode cho phân loại
        for col in features_to_process:
            if df[col].isnull().any():
                if col in numerical_features:
                    df[col] = df[col].fillna(df[col].mean())
                else:
                    df[col] = df[col].fillna(df[col].mode()[0])

        # Label Encoding cho các cột Categorical
        for col in categorical_features:
            df[col] = le.fit_transform(df[col].astype(str))

    elif imputation_method == "knn":
        # Áp dụng K-Nearest Neighbors với k=2 theo như kết quả bài báo

        # Cần Encode tạm các giá trị Non-null sang dạng số để tính toán khoảng cách KNN
        for col in categorical_features:
            non_nulls = df[col].dropna()
            if not non_nulls.empty:
                df.loc[df[col].notnull(), col] = le.fit_transform(non_nulls.astype(str))

        # Thực hiện nội suy bằng KNN với K=2
        knn_imputer = KNNImputer(n_neighbors=2)
        df[features_to_process] = knn_imputer.fit_transform(df[features_to_process])

        # Làm tròn kết quả đối với các biến phân loại sau khi KNN trả về số thập phân
        for col in categorical_features:
            df[col] = df[col].round()

    else:
        # XỬ LÝ MẶC ĐỊNH (STANDARD) BAN ĐẦu
        # 3. Xử lý giá trị thiếu (Missing Values)
        for col in features_to_process:
            if df[col].isnull().any():
                if col in numerical_features:
                    df[col] = df[col].fillna(df[col].median())
                else:
                    df[col] = df[col].fillna(df[col].mode()[0])

        # 4. Label Encoding cho các cột Categorical
        for col in categorical_features:
            df[col] = le.fit_transform(df[col].astype(str))

    # 5. Scaling cho các cột Numerical
    scaler = StandardScaler()
    if numerical_features:
        df[numerical_features] = scaler.fit_transform(df[numerical_features])

    # 7. Nếu Target là dạng chuỗi, chỉ Encode sang số
    if target_column and (df[target_column].dtype == "object" or df[target_column].dtype == "bool"):
        df[target_column] = le.fit_transform(df[target_column].astype(str))

    # 6. Lưu kết quả đã xử lý lên Supabase (vào thư mục 'processed/')
    processed_dataset_id = f"processed_{dataset_id}"
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    path = f"processed/{target_user_id}/{processed_dataset_id}.csv"

    try:
        supabase.storage.from_(DATASET_BUCKET).upload(
            path=path, file=csv_bytes, file_options={"content-type": "text/csv", "upsert": "true"}
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f": {str(e)}")

    return {
        "message": "Preprocessing completed successfully",
        "original_dataset_id": dataset_id,
        "processed_dataset_id": processed_dataset_id,
        "rows": df.shape[0],
        "columns": df.shape[1],
        "duplicates_removed": duplicates_removed,
    }
