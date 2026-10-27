import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import shap
import joblib
import lightgbm as lgb
from lime.lime_tabular import LimeTabularExplainer

pd.options.display.float_format = "{:.2f}".format
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

from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from xgboost import XGBClassifier

from sklearn.impute import SimpleImputer, KNNImputer



# ----------------------------------------------------------
# Load and preprocess
# ----------------------------------------------------------
data = pd.read_csv("../input/heart-failure-prediction/heart.csv")

df1 = data.copy(deep=True)

# ----------------------------------------------------------
# 1. GIẢ LẬP BƠM DỮ LIỆU TRỐNG (Simulating Missing Data)
# ----------------------------------------------------------
# Đặt tỷ lệ muốn làm rỗng là 10%
missing_rate = 0.10
np.random.seed(42) # Set seed để cố định random
n_rows = len(df1)

# Random index cho Cholesterol và Oldpeak
missing_chol = np.random.choice(n_rows, size=int(n_rows * missing_rate), replace=False)
missing_oldpeak = np.random.choice(n_rows, size=int(n_rows * missing_rate), replace=False)

# Gán giá trị NaN
df1.loc[missing_chol, 'Cholesterol'] = np.nan
df1.loc[missing_oldpeak, 'Oldpeak'] = np.nan

print("--- KIỂM TRA DỮ LIỆU TRỐNG (TRƯỚC IMPUTATION) ---")
print(df1[['Cholesterol', 'Oldpeak']].isnull().sum())
print("-" * 50)

# ----------------------------------------------------------
# 2. XỬ LÝ ĐIỀN KHUYẾT THEO BÀI BÁO (Imputation)
# ----------------------------------------------------------
# Chọn phương pháp chạy: 'mean' hoặc 'knn'
IMPUTE_METHOD = 'mean'  

if IMPUTE_METHOD == 'mean':
    # Phương pháp 1: Average estimated method (Mean Imputation)
    print(">> Đang áp dụng phương pháp: Average estimated (Mean) Imputation")
    mean_imputer = SimpleImputer(strategy='mean')
    df1[['Cholesterol', 'Oldpeak']] = mean_imputer.fit_transform(df1[['Cholesterol', 'Oldpeak']])
    
elif IMPUTE_METHOD == 'knn':
    # Phương pháp 2: k-NN Imputation (Bài báo chỉ định k=2 đem lại kết quả tốt nhất)
    print(">> Đang áp dụng phương pháp: k-NN Imputation (với k=2)")
    knn_imputer = KNNImputer(n_neighbors=2)
    # LƯU Ý: Nếu dùng KNNImputer, nó sẽ xét khoảng cách (distance) dựa trên các cột số. 
    # Ở đây ta chỉ điền tạm dựa trên 2 cột chính nó, 
    # hoặc bạn có thể pass toàn bộ DataFrame sau khi Label Encode (được khuyến khích hơn để tăng độ chính xác)
    df1[['Cholesterol', 'Oldpeak']] = knn_imputer.fit_transform(df1[['Cholesterol', 'Oldpeak']])

print("\n--- KIỂM TRA DỮ LIỆU TRỐNG (SAU IMPUTATION) ---")
print(df1[['Cholesterol', 'Oldpeak']].isnull().sum())
print("-" * 50)

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

categorical_features = ['Sex', 'ChestPainType', 'ExerciseAngina', 'ST_Slope']
#Ép kiểu dữ liệu sang 'category' để kích hoạt thuật toán Categorical của LightGBM
for col in categorical_features:
    # Giả sử biến dữ liệu huấn luyện của bạn tên là x_train và x_test
    x_train[col] = x_train[col].astype('category')
    x_test[col] = x_test[col].astype('category')


colors = ["#F93822", "#FDD20E"]


# ----------------------------------------------------------
# Model wrapper (train bằng numpy, SHAP bằng DataFrame)
# ----------------------------------------------------------
def model(classifier):
    if classifier.__class__.__name__ == 'LGBMClassifier':
        classifier.fit(x_train, y_train)
        prediction = classifier.predict(x_test)
    else:
        classifier.fit(x_train.values, y_train.values)
        prediction = classifier.predict(x_test.values)

    cv = RepeatedStratifiedKFold(n_splits=10, n_repeats=3, random_state=1)

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
model(classifier_lr)
model_evaluation(classifier_lr)

classifier_svc = SVC(kernel="linear", C=0.1)
model(classifier_svc)
model_evaluation(classifier_svc)

classifier_dt = DecisionTreeClassifier(random_state=1000, max_depth=4, min_samples_leaf=1)
model(classifier_dt)
model_evaluation(classifier_dt)

classifier_rf = RandomForestClassifier(max_depth=4, random_state=0)
model(classifier_rf)
model_evaluation(classifier_rf)

classifier_knn = KNeighborsClassifier(leaf_size=1, n_neighbors=3, p=1)
model(classifier_knn)
model_evaluation(classifier_knn)

classifier_xgb = XGBClassifier(
    random_state=0,
    n_estimators=50,
    max_depth=3,
    learning_rate=0.105,
    subsample=0.8,
    colsample_bytree=0.9,
    eval_metric="logloss",
)
model(classifier_xgb)
model_evaluation(classifier_xgb)

lgbm_basic = lgb.LGBMClassifier(
    learning_rate=0.05,
    n_estimators=200,
    num_leaves=31,
    min_child_samples=20,
    random_state=42,
    verbose=-1
)
model(lgbm_basic)
model_evaluation(lgbm_basic)

# ----------------------------------------------------------
# Local
# ----------------------------------------------------------
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

# joblib.dump(
#     {
#         "model": classifier_xgb,
#         "label_encoders": {
#             "Sex": le_sex,         # LabelEncoder cho từng cột phân loại
#             "ChestPainType": le_chest,
#             "RestingECG": le_ecg,
#             "ExerciseAngina": le_angina,
#             "ST_Slope": le_slope
#         },
#         "scalers": {
#             "MinMax_Oldpeak": mms,
#             "Standard_Numeric": ss
#         },
#         "features": features.columns,
#         "target": "HeartDisease",
#         "shap_background": background_summary,  # Lưu bản tóm tắt
#         "lime_training_data": lime_training_data
#     },
#     "../models/model_predict.pkl"
# )
