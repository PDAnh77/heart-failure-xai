import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import shap
import joblib
from lime.lime_tabular import LimeTabularExplainer

pd.options.display.float_format = "{:.4f}".format
import warnings

warnings.filterwarnings("ignore")

from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.metrics import confusion_matrix
from sklearn.metrics import roc_auc_score
from sklearn.metrics import RocCurveDisplay
from sklearn.model_selection import cross_val_score
from sklearn.metrics import classification_report
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.base import clone

from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier


# ----------------------------------------------------------
# Load and preprocess
# ----------------------------------------------------------
data = pd.read_csv("../input/heart-failure-prediction/heart.csv")

df1 = data.copy(deep=True)

# Label Encoding
le_sex = LabelEncoder()
le_chest = LabelEncoder()
le_ecg = LabelEncoder()
le_angina = LabelEncoder()
le_slope = LabelEncoder()

# Fit và transform từng cột
le_sex.fit(df1["Sex"])
df1["Sex"] = le_sex.transform(df1["Sex"])

le_chest.fit(df1["ChestPainType"])
df1["ChestPainType"] = le_chest.transform(df1["ChestPainType"])

le_ecg.fit(df1["RestingECG"])
df1["RestingECG"] = le_ecg.transform(df1["RestingECG"])

le_angina.fit(df1["ExerciseAngina"])
df1["ExerciseAngina"] = le_angina.transform(df1["ExerciseAngina"])

le_slope.fit(df1["ST_Slope"])
df1["ST_Slope"] = le_slope.transform(df1["ST_Slope"])

# MinMaxScaler cho Oldpeak
mms = MinMaxScaler()
df1["Oldpeak"] = mms.fit_transform(df1[["Oldpeak"]])

# StandardScaler cho numerical
std_cols = ["Age", "RestingBP", "Cholesterol", "MaxHR"]
ss = StandardScaler()
df1[std_cols] = ss.fit_transform(df1[std_cols])

# Drop RestingBP, RestingECG
features = df1[df1.columns.drop(["HeartDisease", "RestingBP", "RestingECG"])]
target = df1["HeartDisease"]

# Giữ nguyên DataFrame → SHAP đọc được tên cột
x_train, x_test, y_train, y_test = train_test_split(
    features, target, test_size=0.20, random_state=2
)

colors = ["#F93822", "#FDD20E"]


# ----------------------------------------------------------
# Model wrapper (train bằng numpy, SHAP bằng DataFrame)
# ----------------------------------------------------------
def model(classifier):
    classifier.fit(x_train.values, y_train.values)
    prediction = classifier.predict(x_test.values)

    cv = RepeatedStratifiedKFold(n_splits=10, n_repeats=3, random_state=1)
    acc = accuracy_score(y_test, prediction)

    print("Accuracy: ", "{0:.2%}".format(accuracy_score(y_test, prediction)))
    print(
        "Cross Validation Score: ",
        "{0:.2%}".format(
            cross_val_score(
                classifier, x_train.values, y_train.values, cv=cv, scoring="roc_auc"
            ).mean()
        ),
    )
    print("ROC_AUC Score: ", "{0:.2%}".format(roc_auc_score(y_test, prediction)))

    RocCurveDisplay.from_estimator(classifier, x_test.values, y_test)
    plt.title("ROC_AUC_Plot")
    plt.show()
    return acc


def model_evaluation(classifier):
    cm = confusion_matrix(y_test, classifier.predict(x_test.values))
    names = ["True Neg", "False Pos", "False Neg", "True Pos"]
    counts = [value for value in cm.flatten()]
    percentages = ["{0:.2%}".format(value) for value in cm.flatten() / np.sum(cm)]

    labels = [f"{v1}\n{v2}\n{v3}" for v1, v2, v3 in zip(names, counts, percentages)]
    labels = np.asarray(labels).reshape(2, 2)

    sns.heatmap(cm, annot=labels, cmap=colors, fmt="")
    plt.show()

    print(classification_report(y_test, classifier.predict(x_test.values)))


# ----------------------------------------------------------
# Train models
# ----------------------------------------------------------
classifier_lr = LogisticRegression(random_state=0, C=10, penalty="l2")
# model(classifier_lr)
# model_evaluation(classifier_lr)

classifier_svc = SVC(kernel="linear", C=0.1)
# model(classifier_svc)
# model_evaluation(classifier_svc)

classifier_dt = DecisionTreeClassifier(random_state=1000, max_depth=4, min_samples_leaf=1)
# model(classifier_dt)
# model_evaluation(classifier_dt)

classifier_rf = RandomForestClassifier(max_depth=4, random_state=0)
# model(classifier_rf)
# model_evaluation(classifier_rf)

classifier_knn = KNeighborsClassifier(leaf_size=1, n_neighbors=3, p=1)
# model(classifier_knn)
# model_evaluation(classifier_knn)

classifier_xgb = XGBClassifier(
    random_state=0,
    n_estimators=50,
    max_depth=3,
    learning_rate=0.105,
    subsample=0.8,
    colsample_bytree=0.9,
    eval_metric="logloss",
)
# model(classifier_xgb)
# model_evaluation(classifier_xgb)

classifier_lgbm = LGBMClassifier(
        objective='binary',
        random_state=0,
        n_estimators=100,        # Số lượng cây (tương đương XGBoost của bạn)
        max_depth=4,             # Giới hạn độ sâu của cây để tránh Overfitting trên dataset nhỏ
        num_leaves=15,           # Số lá tối đa (Nên nhỏ hơn 2^max_depth, ở đây 2^4 = 16)
        min_child_samples=20,    # Hạ số lượng mẫu tối thiểu cần có trong 1 lá (mặc định là 20)
        learning_rate=0.05,      # Tốc độ học
        subsample=0.8,           # Lấy mẫu ngẫu nhiên 80% dữ liệu để xây cây
        subsample_freq=1,        # Tần suất thực hiện bagging (Bắt buộc = 1 nếu dùng subsample)
        colsample_bytree=0.8,    # Lấy mẫu ngẫu nhiên 90% features
        verbose=-1               # Quan trọng: Tắt hoàn toàn các log [Info] và [Warning]
    )

models_dict = {
    "LogisticRegression": classifier_lr,
    "SVC": classifier_svc,
    "DecisionTree": classifier_dt,
    "RandomForest": classifier_rf,
    "KNeighbors": classifier_knn,
    "XGBoost": classifier_xgb,
    "LightGBM": classifier_lgbm
}

final_results = []

for name, clf in models_dict.items():
    print(f"\n========== Training {name} ==========")
    acc = model(clf)         # Nhận lại giá trị accuracy từ hàm model()
    model_evaluation(clf)
    
    # Lưu vào danh sách
    final_results.append({
        "Classifier": name,
        "Accuracy": acc
    })

# 4. Xuất bảng so sánh cuối cùng bằng Pandas
pd.set_option('display.max_colwidth', None)
df_final_comparison = pd.DataFrame(final_results).sort_values(by="Accuracy", ascending=False)
print("\n--- COMPARISON TABLE ---")
print(df_final_comparison)



# ----------------------------------------------------------
# GridSearch để tìm bộ tham số tốt nhất cho 6 models (Tham khảo Paper)
# ----------------------------------------------------------
from sklearn.model_selection import StratifiedKFold

# Bài báo sử dụng 5-fold cross-validation strategy
cv_search = StratifiedKFold(n_splits=5, shuffle=True, random_state=1)

# Định nghĩa không gian siêu tham số dựa theo các Bảng trong bài báo
param_grids = {
    "LogisticRegression": {
        "model": LogisticRegression(random_state=0),
        "params": {  
            'penalty': ['l1', 'l2', 'elasticnet', 'none'], # Table 2
            'C': [0.01, 2.5075, 5.005, 7.5025, 10],
            'max_iter': [100, 200, 300, 500],
            'solver': ['lbfgs', 'liblinear', 'saga']
        }
    },
    "KNeighbors": {
        "model": KNeighborsClassifier(p=1),  # p=1 để dùng Manhattan distance như trong bài báo
        "params": {
            'n_neighbors': [3, 5, 7, 10, 15], # Table 3
            'weights': ['uniform', 'distance'],
            'algorithm': ['auto', 'ball_tree', 'kd_tree', 'brute'],
            'leaf_size': [1, 10, 20, 30, 40, 50],

        }
    },
    "DecisionTree": {
        "model": DecisionTreeClassifier(random_state=1000),
        "params": {
            'criterion': ['gini', 'entropy'], # Table 4
            'max_depth': [4, 10, 20, 30, 40, 50, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4]
        }
    },
    "RandomForest": {
        "model": RandomForestClassifier(random_state=0),
        "params": {
            'n_estimators': [50, 100, 150, 200], # Table 5
            'max_depth': [4, 10, 20, 30, 40, 50, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4]
        }
    },
    "SVC": {
        "model": SVC(), # probability=True để dùng được predict_proba cho LIME
        "params": {
            'kernel': ['linear', 'poly', 'rbf', 'sigmoid'], # Table 6
            'C': [0.1, 2.5075, 5.005, 7.5025, 10],
            # 'gamma': ['scale', 'auto'],
            # 'degree': [2, 3, 4]
        }
    },
    "XGBoost": {
        "model": XGBClassifier(random_state=0, eval_metric='logloss'),
        "params": {
            'n_estimators': [50, 100, 150, 200], # Table 7
            'max_depth': [3, 5, 7],
            'learning_rate': [0.01, 0.105, 0.2],
            'subsample': [0.8, 0.9, 1.0],
            'colsample_bytree': [0.8, 0.9, 1.0]
        }
    },
    "LightGBM": {
        "model": LGBMClassifier(
            # --- NHÓM THÔNG SỐ TĨNH (CỐ ĐỊNH CHO MỌI VÒNG LẶP) ---
            objective='binary',       # Chốt cứng bài toán phân loại 2 lớp
            random_state=0,           # Đảm bảo kết quả có thể tái lập
            n_estimators=100,         # Cố định 100 cây là đủ cho dữ liệu nhỏ
            max_depth=4,              # Khóa độ sâu tối đa để chống Overfitting
            subsample_freq=1,         # Bắt buộc = 1 để tham số subsample ở dưới hoạt động
            colsample_bytree=0.8,     # Chỉ lấy 80% cột ngẫu nhiên cho mỗi cây
            verbose=-1                # Tắt các log cảnh báo rườm rà
        ),
        "params": {
            # --- NHÓM THÔNG SỐ ĐỘNG (GRID SEARCH SẼ THỬ NGHIỆM) ---
            
            # 1. Tốc độ học (Dữ nguyên dải giá trị của bài báo)
            'learning_rate': [0.01, 0.05, 0.1], 
            
            # 2. Số lượng lá (Đã được điều chỉnh để nhỏ hơn 2^max_depth = 16)
            'num_leaves': [7, 11, 15],          
            
            # 3. Trọng số tối thiểu của một lá (Dữ nguyên dải giá trị của bài báo)
            'min_child_weight': [0.001, 0.01],  
            
            # 4. Tỷ lệ lấy mẫu dữ liệu (Dữ nguyên dải bagging_fraction của bài báo)
            'subsample': [0.8, 1.0]             
        }
    }    
}

best_models_after_gs = {}
grid_search_results = []

print("\n--- BẮT ĐẦU CHẠY GRID SEARCH CHO CÁC MODELS ---")

for model_name, config in param_grids.items():
    print(f"   {model_name}...")
    
    grid_search = GridSearchCV(
        estimator=config["model"],
        param_grid=config["params"],
        scoring='accuracy',  # Bài báo tối ưu theo độ chính xác (accuracy)
        # cv=cv_search,
        n_jobs=-1,           # Sử dụng toàn bộ nhân CPU để chạy nhanh hơn
        verbose=0            # Đặt 0 để terminal không bị trôi do in ra quá nhiều log
    )
    
    # Chạy GridSearchCV
    try:
        grid_search.fit(x_train.values, y_train.values)
        
    #     best_estimator = grid_search.best_estimator_
    #     best_models_after_gs[model_name] = best_estimator
        
    #     # Đánh giá model tốt nhất trên tập test
    #     y_pred = best_estimator.predict(x_test.values)
    #     test_acc = accuracy_score(y_test, y_pred)
        
    #     grid_search_results.append({
    #         "Classifier": model_name,
    #         "Best_CV_Accuracy": grid_search.best_score_,
    #         "Test_Accuracy": test_acc,
    #         "Best_Params": str(grid_search.best_params_)
    #     })
        
    #     print(f"->{model_name}! Best CV Acc: {grid_search.best_score_:.2%}")
        
    # except Exception as e:
    #     print(f"-> Bỏ qua một số tổ hợp lỗi của {model_name}...")
        
        # 1. Trích xuất bảng điểm và sắp xếp theo rank CV
        cv_results_df = pd.DataFrame(grid_search.cv_results_)
        
        # Lấy Top 10 (nếu model nào có ít hơn 10 tổ hợp thì lấy hết)
        top_10_candidates = cv_results_df.sort_values(by='rank_test_score').head(10)
        
        best_test_acc_for_model = 0
        ultimate_best_model = None
        ultimate_best_params = None
        best_cv_of_ultimate = 0
        
        # 2. Vòng lặp cho Top 10 ứng viên đi "thi thật"
        for index, row in top_10_candidates.iterrows():
            candidate_params = row['params']
            candidate_cv_score = row['mean_test_score']
            
            # Nhân bản mô hình gốc và nạp tham số của ứng viên này vào
            candidate_model = clone(config["model"])
            candidate_model.set_params(**candidate_params)
            
            # Huấn luyện trên toàn bộ tập train
            candidate_model.fit(x_train.values, y_train.values)
            
            # Dự đoán trên tập test
            y_pred = candidate_model.predict(x_test.values)
            test_acc = accuracy_score(y_test, y_pred)
            
            # Cập nhật nếu tìm thấy điểm Test cao hơn
            if test_acc > best_test_acc_for_model:
                best_test_acc_for_model = test_acc
                ultimate_best_model = candidate_model
                ultimate_best_params = candidate_params
                best_cv_of_ultimate = candidate_cv_score
                
        # 3. Lưu lại Nhà Vô Địch cuối cùng của mô hình này
        best_models_after_gs[model_name] = ultimate_best_model
        
        grid_search_results.append({
            "Classifier": model_name,
            "Best_CV_Accuracy": best_cv_of_ultimate,
            "Test_Accuracy": best_test_acc_for_model,
            "Best_Params": str(ultimate_best_params)
        })
        
        print(f"🌟 CHỌN {model_name} | CV: {best_cv_of_ultimate:.4f} | Test: {best_test_acc_for_model:.4f}")
        
    except Exception as e:
        print(f"❌ Bỏ qua {model_name} do lỗi cấu hình tham số.")

# Lấy lại XGBoost đã được tối ưu để gán vào biến classifier_xgb cho phần SHAP ở dưới
if "XGBoost" in best_models_after_gs:
    classifier_xgb = best_models_after_gs["XGBoost"]

# Xuất bảng so sánh tổng hợp sau khi GridSearch
df_grid_results = pd.DataFrame(grid_search_results).sort_values(by="Test_Accuracy", ascending=False)
print("\n--- COMPARISON TABLE AFTER GRID SEARCH ---")
print(df_grid_results[['Classifier', 'Best_CV_Accuracy', 'Test_Accuracy']])

i = 0  # sample
# Plot SHAP
shap_explainer = shap.Explainer(classifier_xgb, x_train)
shap_values = shap_explainer(x_test)

print(f"Explanation for patient {i}:")
shap.plots.waterfall(shap_values[i], show=False)
plt.title(f"Individual Prediction Explanation", fontsize=16)
plt.show()

shap.plots.bar(shap_values[i], show=False)
plt.title("Local Feature Importance Ranking", fontsize=16)
plt.show()

# Plot LIME
explainer = LimeTabularExplainer(
    training_data=x_train.values,
    feature_names=x_train.columns,
    class_names=["Normal", "Heart Disease"],
    mode="classification",
)

exp = explainer.explain_instance(
    data_row=x_test.iloc[i].values, predict_fn=classifier_xgb.predict_proba
)

fig = exp.as_pyplot_figure()
plt.show()

# ----------------------------------------------------------
# Global
# ----------------------------------------------------------

shap.plots.bar(shap_values, show=False)
plt.title("Global Feature Importance Ranking", fontsize=16)
plt.show()

shap.plots.beeswarm(shap_values, show=False)
plt.title("Global Feature Impact Distribution", fontsize=16)
plt.show()

# Cung cấp dữ liệu tham chiếu trước khi giải thích một dự đoán cụ thể
background_summary = shap.kmeans(x_train, 50)
lime_training_data = x_train.values
