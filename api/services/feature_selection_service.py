import re
import copy
from random import randint
import numpy as np
import pandas as pd
import shap
import uuid
from typing import Dict, Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from fastapi import HTTPException, status
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, roc_curve, auc
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import ADASYN, SMOTE

from core.supabase_client import supabase

from services.plot_service import upload_plot
from services.dataset_service import load_dataset, _sanitize, DATASET_BUCKET, AVAILABLE_MODELS, DEFAULT_FEATURE_SELECTION_MODEL

task_store: Dict[str, Dict[str, Any]] = {}


def create_task() -> str:
    task_id = str(uuid.uuid4())
    task_store[task_id] = {"status": "PROCESSING", "result": None, "error": None}
    return task_id


def get_task_status(task_id: str) -> Dict[str, Any]:
    if task_id not in task_store:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Task not found")
    return task_store[task_id]


def initialization_of_population(size, n_feat):
    population = []
    for i in range(size):
        chromosome = np.ones(n_feat, dtype=bool)
        chromosome[: int(0.3 * n_feat)] = False
        np.random.shuffle(chromosome)
        population.append(chromosome)
    return population


def fitness_score(population, model, X_train, X_test, Y_train, Y_test):
    scores = []
    for chromosome in population:
        if not np.any(chromosome):
            scores.append(0.0)
            continue

        X_train_selected = X_train.iloc[:, chromosome]
        X_test_selected = X_test.iloc[:, chromosome]
        model.fit(X_train_selected, Y_train)
        predictions = model.predict(X_test_selected)
        scores.append(accuracy_score(Y_test, predictions))

    scores, population = np.array(scores), np.array(population)
    inds = np.argsort(scores)
    return list(scores[inds][::-1]), list(population[inds, :][::-1])


def selection(pop_after_fit, n_parents):
    return list(pop_after_fit[:n_parents])


def crossover(pop_after_sel):
    pop_nextgen = list(pop_after_sel)
    for i in range(0, len(pop_after_sel) - 1, 2):
        child_1, child_2 = pop_nextgen[i], pop_nextgen[i + 1]
        new_par = np.concatenate((child_1[: len(child_1) // 2], child_2[len(child_1) // 2 :]))
        pop_nextgen.append(new_par)
    return pop_nextgen


def mutation(pop_after_cross, mutation_rate, n_feat):
    mutation_range = int(mutation_rate * n_feat)
    pop_next_gen = []
    for chromo in pop_after_cross:
        new_chromo = chromo.copy()
        for _ in range(mutation_range):
            pos = randint(0, n_feat - 1)
            new_chromo[pos] = not new_chromo[pos]
        pop_next_gen.append(new_chromo)
    return pop_next_gen


def generations(model, size, n_feat, n_parents, mutation_rate, n_gen, X_train, X_test, Y_train, Y_test):
    best_chromo = []
    best_score = []
    population_nextgen = initialization_of_population(size, n_feat)

    for i in range(n_gen):
        scores, pop_after_fit = fitness_score(population_nextgen, model, X_train, X_test, Y_train, Y_test)
        pop_after_sel = selection(pop_after_fit, n_parents)
        pop_after_cross = crossover(pop_after_sel)
        population_nextgen = mutation(pop_after_cross, mutation_rate, n_feat)

        best_chromo.append(pop_after_fit[0])
        best_score.append(scores[0])

    return best_chromo, best_score


def genetic_selection(
    dataset_id: str,
    target_column: str,
    owner_id: str,
    user: dict,
    size: int,
    n_gen: int,
    mutation_rate: float,
    n_parents: int,
    model_name: str,
    test_size: float,
    balancing_method: str = "none",
):
    if n_parents is None or n_parents >= size:
        n_parents = int(size * 0.8)

    target_user_id = owner_id if (user["role"] == "admin" and owner_id) else user["user_id"]
    processed_df = load_dataset(dataset_id, target_user_id)

    processed_df = processed_df.rename(columns=lambda x: re.sub(r'[\[\]{} :",]', "_", str(x)))
    if target_column:
        target_column = re.sub(r'[\[\]{} :",]', "_", str(target_column))

    if target_column and target_column not in processed_df.columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target column '{target_column}' not found. Available columns: {list(processed_df.columns)}",
        )

    target = processed_df[target_column]
    features = processed_df.drop(columns=[target_column])

    X_train, X_test, Y_train, Y_test = train_test_split(features, target, test_size=test_size, random_state=42)

    # --- DATA BALANCING ---
    balancing_info = None
    if balancing_method == "smote":
        class_counts = Y_train.value_counts()
        if len(class_counts) >= 2 and class_counts.min() / class_counts.max() < 0.9:
            try:
                before_counts = Y_train.value_counts().to_dict()
                smote = SMOTE(random_state=42)
                X_resampled, Y_resampled = smote.fit_resample(X_train, Y_train)

                X_resampled = pd.DataFrame(X_resampled, columns=X_train.columns)
                categorical_cols = [col for col in X_train.columns if X_train[col].nunique() <= 6]
                for col in categorical_cols:
                    X_resampled[col] = X_resampled[col].round()

                X_train = X_resampled
                Y_train = pd.Series(Y_resampled, name=Y_train.name)
                after_counts = Y_train.value_counts().to_dict()
                balancing_info = {"method": "smote", "before": before_counts, "after": after_counts}
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"SMOTE failed: {str(e)}",
                )
        else:
            balancing_info = {
                "method": "smote",
                "skipped": "Dataset is already balanced (ratio >= 0.9), SMOTE was not applied.",
            }
    elif balancing_method == "adasyn":
        class_counts = Y_train.value_counts()
        if len(class_counts) >= 2 and class_counts.min() / class_counts.max() < 0.9:
            try:
                before_counts = Y_train.value_counts().to_dict()
                adasyn = ADASYN(random_state=42)
                X_resampled, Y_resampled = adasyn.fit_resample(X_train, Y_train)

                categorical_cols = [col for col in X_train.columns if X_train[col].nunique() <= 6]
                X_resampled = pd.DataFrame(X_resampled, columns=X_train.columns)
                for col in categorical_cols:
                    X_resampled[col] = X_resampled[col].round()

                X_train = X_resampled
                Y_train = pd.Series(Y_resampled, name=Y_train.name)
                after_counts = Y_train.value_counts().to_dict()
                balancing_info = {"method": "adasyn", "before": before_counts, "after": after_counts}
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"ADASYN failed: {str(e)}",
                )
        else:
            balancing_info = {
                "method": "adasyn",
                "skipped": "Dataset is already balanced (ratio >= 0.9), ADASYN was not applied.",
            }

    # --- CHỌN MÔ HÌNH ---
    default_model = DEFAULT_FEATURE_SELECTION_MODEL

    if default_model and default_model not in AVAILABLE_MODELS:
        print(f"Model '{default_model}' is not supported. Available models: {list(AVAILABLE_MODELS.keys())}")
        default_model = "decision_tree"

    final_model = default_model

    if model_name:
        if model_name in AVAILABLE_MODELS:
            final_model = model_name
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{model_name}' is not supported. Available models: {list(AVAILABLE_MODELS.keys())}",
            )

    print(f"Using model {final_model} for feature selection")

    # Khởi tạo Model
    model = AVAILABLE_MODELS[final_model]

    # --- ĐÁNH GIÁ MÔ HÌNH BAN ĐẦU (BASELINE) ---
    model.fit(X_train, Y_train)
    baseline_predictions = model.predict(X_test)
    baseline_accuracy = accuracy_score(Y_test, baseline_predictions)
    original_feature_count = features.shape[1]
    # ------------------------------------------

    # Genetic Algorithm
    best_chromo_list, best_score_list = generations(
        model=model,
        size=size,
        n_feat=features.shape[1],
        n_parents=n_parents,
        mutation_rate=mutation_rate,
        n_gen=n_gen,
        X_train=X_train,
        X_test=X_test,
        Y_train=Y_train,
        Y_test=Y_test,
    )

    # Tìm index của giá trị accuracy cao nhất trong các thế hệ
    best_gen_index = np.argmax(best_score_list)

    # Trích xuất score và chromosome tại thế hệ đó
    absolute_best_score = float(best_score_list[best_gen_index])
    absolute_best_chromo = best_chromo_list[best_gen_index]

    # Lấy danh sách feature
    selected_features = features.columns[absolute_best_chromo].tolist()

    columns_to_keep = selected_features.copy()
    if target_column and target_column not in columns_to_keep:
        columns_to_keep.append(target_column)

    df_selected = processed_df[columns_to_keep]

    fs_dataset_id = f"fs_{dataset_id}"
    csv_bytes = df_selected.to_csv(index=False).encode("utf-8")

    path = f"feature-selection/{target_user_id}/{fs_dataset_id}.csv"

    try:
        supabase.storage.from_(DATASET_BUCKET).upload(
            path=path, file=csv_bytes, file_options={"content-type": "text/csv", "upsert": "true"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload feature selection dataset failed: {str(e)}",
        )

    return {
        "fs_dataset_id": fs_dataset_id,
        "baseline_accuracy": round(baseline_accuracy, 4),
        "original_feature_count": original_feature_count,
        "best_ga_accuracy": round(absolute_best_score, 4),
        "selected_features": selected_features,
        "feature_count": len(selected_features),
        "found_at_generation": int(best_gen_index + 1),
        "balancing": balancing_info,
    }


def evaluate_feature_selection(
    dataset_id: str,
    fs_dataset_id: str,
    target_column: str,
    owner_id: str,
    user: dict,
    model_name: str,
    test_size: float,
    balancing_method: str = "none",
):
    target_user_id = owner_id if (user["role"] == "admin" and owner_id) else user["user_id"]

    # 2 tập dữ liệu từ Supabase Storage
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

    # Tách Features và Target
    Y_orig = df_original[target_column]
    X_orig = df_original.drop(columns=[target_column])

    selected_features = df_selected.drop(columns=[target_column]).columns.tolist()

    # Chia tập Train/Test
    X_train_orig, X_test_orig, Y_train_orig, Y_test_orig = train_test_split(
        X_orig, Y_orig, test_size=test_size, random_state=42
    )

    # =================================================================
    # ĐỒNG BỘ DATA BALANCING (SMOTE / ADASYN)
    # =================================================================
    def apply_balancing(X_tr, Y_tr, method):
        if method == "none":
            return X_tr, Y_tr

        class_counts = Y_tr.value_counts()
        if len(class_counts) < 2 or class_counts.min() / class_counts.max() >= 0.9:
            return X_tr, Y_tr

        try:
            if method == "smote":
                from imblearn.over_sampling import SMOTE

                sampler = SMOTE(random_state=42)
            elif method == "adasyn":
                from imblearn.over_sampling import ADASYN

                sampler = ADASYN(random_state=42)
            else:
                return X_tr, Y_tr

            X_res, Y_res = sampler.fit_resample(X_tr, Y_tr)
            X_res = pd.DataFrame(X_res, columns=X_tr.columns)

            cat_cols = [col for col in X_tr.columns if X_tr[col].nunique() <= 6]
            for col in cat_cols:
                X_res[col] = X_res[col].round()

            return X_res, pd.Series(Y_res, name=Y_tr.name)
        except Exception as e:
            print(f"Balancing failed in evaluation: {e}")
            return X_tr, Y_tr

    # Áp dụng cân bằng cho cả mô hình Before và After
    X_train_orig, Y_train_orig = apply_balancing(X_train_orig, Y_train_orig, balancing_method)

    X_train_sel = X_train_orig[selected_features].copy()
    X_test_sel = X_test_orig[selected_features].copy()
    Y_train_sel = Y_train_orig.copy()
    Y_test_sel = Y_test_orig.copy()

    # Xác định mô hình sử dụng
    final_model_name = model_name if model_name else DEFAULT_FEATURE_SELECTION_MODEL
    if final_model_name not in AVAILABLE_MODELS:
        final_model_name = "decision_tree"

    # LUÔN GIỮ COPY ĐỂ BẢO VỆ SERVER
    model_before = copy.deepcopy(AVAILABLE_MODELS[final_model_name])
    model_after = copy.deepcopy(AVAILABLE_MODELS[final_model_name])

    def _to_frame(data, columns):
        if isinstance(data, pd.DataFrame):
            return data
        return pd.DataFrame(data, columns=columns)

    def _predict_with_columns(model, columns):
        def _predict(data):
            return model.predict(_to_frame(data, columns))

        return _predict

    # =================================================================
    # ĐÁNH GIÁ MÔ HÌNH TRƯỚC (BASELINE)
    # =================================================================
    model_before.fit(X_train_orig, Y_train_orig)
    preds_before = model_before.predict(X_test_orig)

    metrics_before = {
        "accuracy": round(accuracy_score(Y_test_orig, preds_before), 4),
        "precision": round(precision_score(Y_test_orig, preds_before, average="binary", zero_division=0), 4),
        "recall": round(recall_score(Y_test_orig, preds_before, average="binary", zero_division=0), 4),
        "f1_score": round(f1_score(Y_test_orig, preds_before, average="binary", zero_division=0), 4),
    }
    cm_before = confusion_matrix(Y_test_orig, preds_before)

    # =================================================================
    # ĐÁNH GIÁ MÔ HÌNH SAU GA (OPTIMIZED)
    # =================================================================
    model_after.fit(X_train_sel, Y_train_sel)
    preds_after = model_after.predict(X_test_sel)

    metrics_after = {
        "accuracy": round(accuracy_score(Y_test_sel, preds_after), 4),
        "precision": round(precision_score(Y_test_sel, preds_after, average="binary", zero_division=0), 4),
        "recall": round(recall_score(Y_test_sel, preds_after, average="binary", zero_division=0), 4),
        "f1_score": round(f1_score(Y_test_sel, preds_after, average="binary", zero_division=0), 4),
    }
    cm_after = confusion_matrix(Y_test_sel, preds_after)

    # =================================================================
    # VẼ ĐỒ THỊ CONFUSION MATRIX
    # =================================================================
    fig_cm, axes_cm = plt.subplots(1, 2, figsize=(11, 4.5))

    sns.heatmap(
        cm_before,
        annot=True,
        fmt="d",
        cmap="Blues",
        ax=axes_cm[0],
        cbar=False,
        annot_kws={"size": 14, "weight": "bold"},
    )
    axes_cm[0].set_title("Confusion Matrix (Before Selection)", fontsize=12, pad=10)
    axes_cm[0].set_xlabel("Predicted Label")
    axes_cm[0].set_ylabel("Actual Label")

    sns.heatmap(
        cm_after,
        annot=True,
        fmt="d",
        cmap="Greens",
        ax=axes_cm[1],
        cbar=False,
        annot_kws={"size": 14, "weight": "bold"},
    )
    axes_cm[1].set_title("Confusion Matrix (After Selection)", fontsize=12, pad=10)
    axes_cm[1].set_xlabel("Predicted Label")
    axes_cm[1].set_ylabel("Actual Label")

    plt.tight_layout()
    chart_url = upload_plot(
        fig_cm, f"{target_user_id}/{dataset_id}/confusion_matrix_comparison.png", bucket_name="eda-artifacts"
    )

    # =================================================================
    # VẼ BIỂU ĐỒ ROC CURVE SO SÁNH
    # =================================================================
    roc_chart_url = None
    try:
        # Lấy xác suất dự đoán (class 1)
        probs_before = model_before.predict_proba(X_test_orig)[:, 1]
        probs_after = model_after.predict_proba(X_test_sel)[:, 1]

        # Tính ROC curve
        fpr_before, tpr_before, _ = roc_curve(Y_test_orig, probs_before)
        roc_auc_before = auc(fpr_before, tpr_before)

        fpr_after, tpr_after, _ = roc_curve(Y_test_sel, probs_after)
        roc_auc_after = auc(fpr_after, tpr_after)

        # Vẽ đồ thị
        fig_roc, ax_roc = plt.subplots(figsize=(7, 6))
        ax_roc.plot(
            fpr_before,
            tpr_before,
            color="darkorange",
            lw=2,
            linestyle="--",
            label=f"Before Selection (AUC = {roc_auc_before:.3f})",
        )
        ax_roc.plot(fpr_after, tpr_after, color="green", lw=2.5, label=f"After Selection (AUC = {roc_auc_after:.3f})")
        ax_roc.plot([0, 1], [0, 1], color="gray", lw=1, linestyle="--")

        ax_roc.set_xlim([0.0, 1.0])
        ax_roc.set_ylim([0.0, 1.05])
        ax_roc.set_xlabel("False Positive Rate (1 - Specificity)", fontsize=11)
        ax_roc.set_ylabel("True Positive Rate (Sensitivity)", fontsize=11)
        ax_roc.set_title("Receiver Operating Characteristic (ROC) Comparison", fontsize=13, pad=15)
        ax_roc.legend(loc="lower right", frameon=True, shadow=True)

        plt.tight_layout()
        roc_chart_url = upload_plot(
            fig_roc, f"{target_user_id}/{dataset_id}/roc_comparison.png", bucket_name="eda-artifacts"
        )
    except Exception as e:
        print(f"Error gen ROC plot: {e}")

    # =================================================================
    # VẼ BIỂU ĐỒ SHAP (BAR & BEESWARM) TRƯỚC VÀ SAU
    # =================================================================
    shap_chart_before_url = None
    shap_chart_after_url = None
    shap_beeswarm_before_url = None
    shap_beeswarm_after_url = None

    try:
        limit = 100
        X_sample_orig = shap.utils.sample(X_test_orig, limit) if len(X_test_orig) > limit else X_test_orig
        X_sample_sel = shap.utils.sample(X_test_sel, limit) if len(X_test_sel) > limit else X_test_sel

        tree_models = ["xgboost", "lightgbm", "random_forest", "decision_tree"]

        def _compute_shap_values(model, X_sample, X_train_full):
            if final_model_name in tree_models:
                explainer = shap.TreeExplainer(model)
                sv = explainer.shap_values(X_sample)
            elif final_model_name == "logistic_regression":
                explainer = shap.LinearExplainer(model, X_train_full)
                sv = explainer.shap_values(X_sample)
            else:
                background = shap.kmeans(X_train_full, 10)
                explainer = shap.KernelExplainer(
                    _predict_with_columns(model, X_train_full.columns),
                    background,
                )
                sv = explainer.shap_values(X_sample, silent=True)

            if isinstance(sv, list):
                sv = sv[1]
            elif len(sv.shape) == 3:
                sv = sv[:, :, 1]
            return sv

        # --- SHAP BEFORE ---
        shap_values_before = _compute_shap_values(model_before, X_sample_orig, X_train_orig)

        # Bar Chart Before
        plt.figure(figsize=(8, 5))
        shap.summary_plot(shap_values_before, X_sample_orig, plot_type="bar", show=False, max_display=15)
        plt.title("SHAP Global Feature Importance (Before Feature Selection)", pad=15, fontsize=12)
        plt.tight_layout()
        fig_shap_bar_before = plt.gcf()
        shap_chart_before_url = upload_plot(
            fig_shap_bar_before, f"{target_user_id}/{dataset_id}/shap_before.png", bucket_name="eda-artifacts"
        )

        # Beeswarm Chart Before (Tận dụng luôn shap_values_before đã tính)
        plt.figure(figsize=(8, 5))
        shap.summary_plot(shap_values_before, X_sample_orig, show=False, max_display=15)
        plt.title("SHAP Beeswarm Distribution (Before Feature Selection)", pad=15, fontsize=12)
        plt.tight_layout()
        fig_shap_beeswarm_before = plt.gcf()
        shap_beeswarm_before_url = upload_plot(
            fig_shap_beeswarm_before,
            f"{target_user_id}/{dataset_id}/shap_beeswarm_before.png",
            bucket_name="eda-artifacts",
        )

        # --- SHAP AFTER ---
        shap_values_after = _compute_shap_values(model_after, X_sample_sel, X_train_sel)

        # Bar Chart After
        plt.figure(figsize=(8, 5))
        shap.summary_plot(shap_values_after, X_sample_sel, plot_type="bar", show=False, max_display=15)
        plt.title("SHAP Global Feature Importance (After Feature Selection)", pad=15, fontsize=12)
        plt.tight_layout()
        fig_shap_bar_after = plt.gcf()
        shap_chart_after_url = upload_plot(
            fig_shap_bar_after, f"{target_user_id}/{dataset_id}/shap_after.png", bucket_name="eda-artifacts"
        )

        # Beeswarm Chart After
        plt.figure(figsize=(8, 5))
        shap.summary_plot(shap_values_after, X_sample_sel, show=False, max_display=15)
        plt.title("SHAP Beeswarm Distribution (After Feature Selection)", pad=15, fontsize=12)
        plt.tight_layout()
        fig_shap_beeswarm_after = plt.gcf()
        shap_beeswarm_after_url = upload_plot(
            fig_shap_beeswarm_after,
            f"{target_user_id}/{dataset_id}/shap_beeswarm_after.png",
            bucket_name="eda-artifacts",
        )

    except Exception as e:
        print(f"Error generating SHAP plots: {e}")
        plt.close("all")

    return _sanitize(
        {
            "model_evaluated": final_model_name,
            "metrics_before": metrics_before,
            "metrics_after": metrics_after,
            "confusion_matrix_chart_url": chart_url,
            "roc_chart_url": roc_chart_url,
            "shap_chart_before_url": shap_chart_before_url,
            "shap_chart_after_url": shap_chart_after_url,
            "shap_beeswarm_before_url": shap_beeswarm_before_url,
            "shap_beeswarm_after_url": shap_beeswarm_after_url,
        }
    )


def background_genetic_selection(
    task_id: str,
    dataset_id: str,
    target_column: str,
    owner_id: str,
    user: dict,
    size: int,
    n_gen: int,
    mutation_rate: float,
    n_parents: int,
    model_name: str,
    test_size: float,
    balancing_method: str = "none",
):
    """
    This wrapper function runs in the background.
    It executes the heavy GA process and updates the task_store upon completion.
    """
    try:
        # Call your original heavy function
        result = genetic_selection(
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

        # Update status to COMPLETED and store the result
        task_store[task_id]["status"] = "COMPLETED"
        task_store[task_id]["result"] = result
    except Exception as e:
        # Update status to FAILED and store the error message
        print(f"Background task {task_id} failed: {e}")
        task_store[task_id]["status"] = "FAILED"
        task_store[task_id]["error"] = str(e)


def background_evaluate_feature_selection(
    task_id: str,
    dataset_id: str,
    fs_dataset_id: str,
    target_column: str,
    owner_id: str,
    user: dict,
    model_name: str,
    test_size: float,
    balancing_method: str = "none",
):
    try:
        # Gọi hàm đánh giá (vẽ SHAP, tính accuracy, upload hình...)
        result = evaluate_feature_selection(
            dataset_id=dataset_id,
            fs_dataset_id=fs_dataset_id,
            target_column=target_column,
            owner_id=owner_id,
            user=user,
            model_name=model_name,
            test_size=test_size,
            balancing_method=balancing_method,
        )

        # Cập nhật trạng thái thành công
        task_store[task_id]["status"] = "COMPLETED"
        task_store[task_id]["result"] = result

    except Exception as e:
        print(f"Background evaluation {task_id} failed: {e}")
        task_store[task_id]["status"] = "FAILED"
        task_store[task_id]["error"] = str(e)
