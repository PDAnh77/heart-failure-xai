import uuid
import re
import copy
from datetime import datetime
from typing import Dict, Any

import pandas as pd
import shap
import matplotlib

matplotlib.use("Agg")  # Use backend non-GUI
import matplotlib.pyplot as plt
from lime import lime_tabular

from fastapi import HTTPException, status
from pydantic import ValidationError
from sklearn.model_selection import train_test_split

from core.model_loader import get_pipeline
from schemas.patient_schema import PatientPredict

from services.plot_service import upload_plot
from services.dataset_service import load_dataset, _sanitize, AVAILABLE_MODELS, DEFAULT_FEATURE_SELECTION_MODEL

IMAGE_BUCKET = "heart-prediction-xai-reports"


def generate_patient_xai_images(model, background_data, lime_train_data, features_list, processed_df, raw_row):
    # Tạo ID chung
    request_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:6]}"
    results = {}

    # --- CHUẨN BỊ SHAP VALUES ---
    try:
        explainer = shap.Explainer(model, background_data.data)
        shap_values = explainer(processed_df)

        if len(shap_values.shape) == 3:
            shap_values = shap_values[:, :, 1]

        shap_values.display_data = raw_row.values
    except Exception as e:
        print(f"Error calculate SHAP values: {e}")
        return results

    # --- BIỂU ĐỒ 1: SHAP WATERFALL ---
    try:
        fig = plt.figure(figsize=(8, 6))
        shap.plots.waterfall(shap_values[0], show=False)
        plt.title("Patient's Risk Factor Breakdown", fontsize=14)
        results["shap_waterfall"] = upload_plot(fig, folder_path=f"shap/{request_id}")
    except Exception:
        pass

    # --- BIỂU ĐỒ 2: SHAP BAR ---
    try:
        fig = plt.figure(figsize=(8, 6))
        shap.plots.bar(shap_values[0], show=False)
        plt.title("Top Factors Influencing This Prediction", fontsize=14)
        results["shap_bar"] = upload_plot(fig, folder_path=f"shap/{request_id}")
    except Exception:
        pass

    # --- BIỂU ĐỒ 3: LIME ---
    try:
        lime_explainer = lime_tabular.LimeTabularExplainer(
            training_data=lime_train_data,
            feature_names=features_list,
            class_names=["Normal", "Heart Disease"],
            mode="classification",
            verbose=False,
        )
        exp = lime_explainer.explain_instance(data_row=processed_df.iloc[0].values, predict_fn=model.predict_proba)
        fig = exp.as_pyplot_figure()
        fig.set_size_inches(8, 6)
        plt.title("Patient's Feature Impact on Probability (LIME Analysis)", fontsize=14)
        results["lime"] = upload_plot(fig, folder_path=f"lime/{request_id}")
    except Exception:
        pass

    return results


def generate_batch_xai_images(model, background_data, processed_batch_df):
    request_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:6]}"
    results = {}

    try:
        explainer = shap.Explainer(model, background_data.data)
        shap_values = explainer(processed_batch_df)

        if len(shap_values.shape) == 3:
            shap_values = shap_values[:, :, 1]
    except Exception as e:
        print(f"Error batch SHAP: {e}")
        return results

    # --- BIỂU ĐỒ 1: SHAP BAR (Global - Trung bình ảnh hưởng của nhóm này) ---
    try:
        fig = plt.figure(figsize=(10, 6))
        shap.plots.bar(shap_values, show=False, max_display=15)
        plt.title("Group Average Feature Importance", fontsize=14)
        results["batch_shap_bar"] = upload_plot(fig, folder_path=f"shap/{request_id}")
    except Exception as e:
        print(f"Batch bar error: {e}")

    # --- BIỂU ĐỒ 2: SHAP BEESWARM (Global) ---
    try:
        fig = plt.figure(figsize=(10, 6))
        shap.plots.beeswarm(shap_values, show=False, max_display=15)
        plt.title("Group Risk Distribution", fontsize=14)
        results["batch_shap_beeswarm"] = upload_plot(fig, folder_path=f"shap/{request_id}")
    except Exception as e:
        print(f"Beeswarm error: {e}")

    return results


def generate_single_xai(patient_raw: Dict[str, Any]):
    from services.prediction_service import build_column_mapping, REQUIRED_COLUMNS, prepare_dataframe

    pipeline = get_pipeline()
    model = pipeline["model"]
    features = pipeline["features"]
    background_data = pipeline["shap_background"]
    lime_data = pipeline["lime_training_data"]

    # Chuyển raw data thành DataFrame để tận dụng hàm build_column_mapping
    raw_df = pd.DataFrame([patient_raw])

    # Map tên cột (hàm này có sẵn trong file của bạn, dùng biến COLUMN_ALIASES)
    try:
        column_mapping = build_column_mapping(raw_df.columns.tolist())
    except HTTPException as e:
        raise e

    mapped_df = raw_df.rename(columns=column_mapping)

    # Lọc lấy đúng các cột cần thiết (REQUIRED_COLUMNS)
    mapped_df = mapped_df[REQUIRED_COLUMNS].copy()
    mapped_df = mapped_df.where(pd.notnull(mapped_df), None)

    # Chuyển lại thành dict để đưa cho Pydantic
    mapped_record = mapped_df.to_dict(orient="records")[0]

    # Validate bằng PatientPredict
    try:
        mapped_record["save_prediction"] = False
        patient_valid = PatientPredict(**mapped_record)
    except ValidationError as e:
        error_details = [f"{err.get('loc')[0]}: {err.get('msg')}" for err in e.errors()]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "Invalid patient data format", "errors": error_details},
        )

    # Bỏ các trường không nằm trong mô hình dự đoán
    clean_dict = patient_valid.model_dump()
    clean_dict.pop("save_prediction", None)

    clean_df = pd.DataFrame([clean_dict])
    x_processed = prepare_dataframe(clean_df, pipeline)

    plots = generate_patient_xai_images(
        model=model,
        background_data=background_data,
        lime_train_data=lime_data,
        features_list=features,
        processed_df=x_processed,
        raw_row=clean_df[features],
    )
    return plots


def generate_lime_explanation(
    dataset_id: str,
    fs_dataset_id: str,
    target_column: str,
    owner_id: str,
    user: dict,
    model_name: str,
    test_size: float,
    instance_idx: int,
):
    target_user_id = owner_id if (user["role"] == "admin" and owner_id) else user["user_id"]

    # 1. Load data
    df_original = load_dataset(dataset_id, target_user_id)
    df_selected = load_dataset(fs_dataset_id, target_user_id)

    # CLEAN COLUMN NAMES FOR LIGHTGBM
    df_original = df_original.rename(columns=lambda x: re.sub(r'[\[\]{} :",]', "_", str(x)))
    df_selected = df_selected.rename(columns=lambda x: re.sub(r'[\[\]{} :",]', "_", str(x)))

    # Clean target_column name to match the sanitized dataframes
    if target_column:
        target_column = re.sub(r'[\[\]{} :",]', "_", str(target_column))

    if target_column not in df_original.columns:
        raise HTTPException(status_code=400, detail=f"Target column '{target_column}' not found.")

    # 2. Split data (Must keep random_state=42 to match the evaluation API)
    Y_orig = df_original[target_column]
    X_orig = df_original.drop(columns=[target_column])
    Y_sel = df_selected[target_column]
    X_sel = df_selected.drop(columns=[target_column])

    X_train_orig, X_test_orig, Y_train_orig, Y_test_orig = train_test_split(
        X_orig, Y_orig, test_size=test_size, random_state=42
    )
    X_train_sel, X_test_sel, Y_train_sel, Y_test_sel = train_test_split(
        X_sel, Y_sel, test_size=test_size, random_state=42
    )

    # Validate index
    max_idx = len(X_test_orig) - 1
    if instance_idx < 0 or instance_idx > max_idx:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid row index. The test set only contains {len(X_test_orig)} rows.",
        )

    # 3. Model Setup & Fast Retrain
    final_model_name = model_name if model_name else DEFAULT_FEATURE_SELECTION_MODEL
    if final_model_name not in AVAILABLE_MODELS:
        final_model_name = "decision_tree"

    model_before = copy.deepcopy(AVAILABLE_MODELS[final_model_name])
    model_after = copy.deepcopy(AVAILABLE_MODELS[final_model_name])

    model_before.fit(X_train_orig, Y_train_orig)
    model_after.fit(X_train_sel, Y_train_sel)

    # Helpers
    def _to_frame(data, columns):
        return data if isinstance(data, pd.DataFrame) else pd.DataFrame(data, columns=columns)

    def _predict_proba_with_columns(model, columns):
        return lambda data: model.predict_proba(_to_frame(data, columns))

    # 4. Generate LIME
    lime_chart_before_url = None
    lime_chart_after_url = None
    xai_score_before = None
    xai_score_after = None

    try:
        # ==========================================
        # LIME Before Feature Selection
        # ==========================================
        explainer_before = lime_tabular.LimeTabularExplainer(
            training_data=X_train_orig.values,
            feature_names=X_train_orig.columns.tolist(),
            class_names=["Class 0", "Class 1"],
            mode="classification",
            random_state=42,
        )
        exp_before = explainer_before.explain_instance(
            data_row=X_test_orig.iloc[instance_idx].values,
            predict_fn=_predict_proba_with_columns(model_before, X_train_orig.columns),
            num_features=15,
        )

        # Extract XAI Score (R-squared of the local model)
        xai_score_before = exp_before.score

        # Render and save plot
        fig_lime_before = exp_before.as_pyplot_figure()
        plt.title(
            f"LIME Local Explanation - Instance {instance_idx} (Before FS)",
            pad=15,
        )
        plt.tight_layout()
        lime_chart_before_url = upload_plot(
            fig_lime_before, f"{target_user_id}/{dataset_id}/lime_before_idx_{instance_idx}.png"
        )

        # ==========================================
        # LIME After Feature Selection
        # ==========================================
        explainer_after = lime_tabular.LimeTabularExplainer(
            training_data=X_train_sel.values,
            feature_names=X_train_sel.columns.tolist(),
            class_names=["Class 0", "Class 1"],
            mode="classification",
            random_state=42,
        )
        exp_after = explainer_after.explain_instance(
            data_row=X_test_sel.iloc[instance_idx].values,
            predict_fn=_predict_proba_with_columns(model_after, X_train_sel.columns),
            num_features=15,
        )

        # Extract XAI Score (R-squared of the local model)
        xai_score_after = exp_after.score

        # Render and save plot
        fig_lime_after = exp_after.as_pyplot_figure()
        plt.title(
            f"LIME Local Explanation - Instance {instance_idx} (After FS)",
            pad=15,
        )
        plt.tight_layout()
        lime_chart_after_url = upload_plot(
            fig_lime_after, f"{target_user_id}/{dataset_id}/lime_after_idx_{instance_idx}.png"
        )

    except Exception as e:
        print(f"Error generating LIME plots: {e}")
        plt.close("all")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate LIME explanations."
        )

    return _sanitize(
        {
            "instance_idx": instance_idx,
            "lime_chart_before_url": lime_chart_before_url,
            "lime_chart_after_url": lime_chart_after_url,
            "xai_score_before": round(xai_score_before, 4) if xai_score_before is not None else None,
            "xai_score_after": round(xai_score_after, 4) if xai_score_after is not None else None,
        }
    )
