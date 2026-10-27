import matplotlib

matplotlib.use("Agg")  # Use backend non-GUI
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from fastapi import HTTPException, status
from sklearn.feature_selection import SelectKBest, chi2, f_classif
from sklearn.preprocessing import OrdinalEncoder

from services.plot_service import upload_plot
from services.dataset_service import load_dataset, _sanitize

EDA_BUCKET = "eda-artifacts"


def get_eda(dataset_id: str, target_column: str, owner_id: str, user: dict):
    target_user_id = owner_id if (user["role"] == "admin" and owner_id) else user["user_id"]
    df = load_dataset(dataset_id, target_user_id)

    if target_column and target_column not in df.columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target column '{target_column}' not found. Available columns: {list(df.columns)}",
        )

    # Phân loại features
    features_only = [col for col in df.columns if col != target_column]
    numeric_df = df.select_dtypes(include=["number"])
    numerical_features = [col for col in features_only if col in numeric_df.columns and df[col].nunique() > 6]
    categorical_features = [col for col in features_only if col not in numerical_features]

    stats = df.describe().to_dict()
    charts = {}

    # --- 1. FULL CORRELATION HEATMAP (Tương quan giữa các cặp biến) ---
    plt.figure(figsize=(10, 8))
    sns.heatmap(numeric_df.corr(), annot=True, cmap="coolwarm", fmt=".2f")
    plt.title("Full Correlation Heatmap")
    fig_full_corr = plt.gcf()
    charts["full_correlation"] = upload_plot(
        fig_full_corr, f"{target_user_id}/{dataset_id}/full_corr.png", bucket_name=EDA_BUCKET
    )

    if target_column and target_column in df.columns:
        valid_mask = df[target_column].notna()
        clean_df = df[valid_mask]
        target = clean_df[target_column]

        # --- 2. TARGET DISTRIBUTION (Tỷ lệ và số lượng nhãn) ---
        counts = target.value_counts()
        if not counts.empty:
            palette = sns.color_palette("coolwarm", n_colors=len(counts))
            fig, ax = plt.subplots(1, 2, figsize=(15, 6))
            ax[0].pie(
                counts,
                labels=counts.index,
                autopct="%1.1f%%",
                startangle=90,
                colors=palette,
                wedgeprops={"edgecolor": "black"},
            )
            ax[0].set_title(f"{target_column} %")
            sns.barplot(
                x=counts.index,
                y=counts.values,
                hue=counts.index,
                ax=ax[1],
                palette=palette,
                edgecolor="black",
                legend=False,
            )
            ax[1].set_title(f"Cases of {target_column}")
            ax[1].set_xlabel(target_column)
            ax[1].set_ylabel("count")
            fig_dist = plt.gcf()
            charts["target_distribution"] = upload_plot(
                fig_dist, f"{target_user_id}/{dataset_id}/dist.png", bucket_name=EDA_BUCKET
            )

        # --- 3. TARGET CORRELATION (Pearson - Tương quan tuyến tính với nhãn) ---
        if target_column in numeric_df.columns:
            try:
                target_corr = clean_df[numeric_df.columns].corrwith(target).sort_values(ascending=False).to_frame()
                target_corr.columns = ["Correlation"]
                plt.figure(figsize=(6, 10))
                sns.heatmap(target_corr, annot=True, cmap="coolwarm", fmt=".2f", linewidths=0.5)
                plt.title(f"Correlation w.r.t {target_column}")
                fig_target_corr = plt.gcf()
                charts["target_correlation"] = upload_plot(
                    fig_target_corr, f"{target_user_id}/{dataset_id}/target_corr.png", bucket_name=EDA_BUCKET
                )
            except Exception as e:
                print(f"Target correlation error: {str(e)}")

        # --- 4. CHI-SQUARE SCORE (Ý nghĩa của biến phân loại) ---
        if categorical_features and not clean_df.empty:
            try:
                encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
                encoded_cat = encoder.fit_transform(clean_df[categorical_features].astype(str))
                X_cat = pd.DataFrame(encoded_cat, columns=categorical_features, index=clean_df.index)
                X_cat = X_cat.where(X_cat >= 0, 0)
                fit_cat = SelectKBest(score_func=chi2, k="all").fit(X_cat, target)
                cat_scores = (
                    pd.DataFrame(data=fit_cat.scores_, index=categorical_features, columns=["Score"])
                    .sort_values(by="Score", ascending=False)
                    .head(20)
                )
                plt.figure(figsize=(6, 8))
                sns.heatmap(cat_scores, annot=True, cmap="YlGnBu", fmt=".2f")
                plt.title("Categorical Importance (Chi-Square)")
                fig_chi2 = plt.gcf()
                charts["chi_square_score"] = upload_plot(
                    fig_chi2, f"{target_user_id}/{dataset_id}/chi2.png", bucket_name=EDA_BUCKET
                )
            except Exception as e:
                print(f"Chi-square calculation error: {str(e)}")

        # --- 5. ANOVA SCORE (Ý nghĩa của biến số) ---
        if numerical_features and not clean_df.empty:
            try:
                X_num = clean_df[numerical_features].fillna(clean_df[numerical_features].median()).fillna(0)
                fit_num = SelectKBest(score_func=f_classif, k="all").fit(X_num, target)
                num_scores = (
                    pd.DataFrame(data=fit_num.scores_, index=numerical_features, columns=["Score"])
                    .sort_values(by="Score", ascending=False)
                    .head(20)
                )
                plt.figure(figsize=(6, 8))
                sns.heatmap(num_scores, annot=True, cmap="YlOrRd", fmt=".2f")
                plt.title("Numerical Importance (ANOVA)")
                fig_anova = plt.gcf()
                charts["anova_score"] = upload_plot(
                    fig_anova, f"{target_user_id}/{dataset_id}/anova.png", bucket_name=EDA_BUCKET
                )
            except Exception as e:
                print(f"ANOVA calculation error: {str(e)}")

    return _sanitize({"statistics": stats, "charts": charts})
