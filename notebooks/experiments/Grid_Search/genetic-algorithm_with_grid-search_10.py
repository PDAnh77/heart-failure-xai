# 21/04 - chỉnh sửa hàm fitness_score thành fitness_score_cv để đánh giá bằng Cross-Validation trên tập TRAIN, không dùng tập TEST trong quá trình GA. Điều này giúp tránh rò rỉ thông tin từ TEST vào quá trình chọn đặc trưng.


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from random import randint
import warnings
import shap
from lime.lime_tabular import LimeTabularExplainer

from sklearn.calibration import LabelEncoder
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold, cross_val_score
from sklearn.metrics import accuracy_score
from sklearn.base import clone

warnings.filterwarnings("ignore")
pd.options.display.float_format = "{:.4f}".format

from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

# =====================================================================
# 1. PREPROCESSING & SPLIT DATA
# =====================================================================
def split(features, target):
    X_train, X_test, Y_train, Y_test = train_test_split(features, target, test_size=0.2, random_state=42)
    return X_train, X_test, Y_train, Y_test

data = pd.read_csv("../input/heart-failure-prediction/heart.csv")
df1 = data.copy(deep=True)

le_sex = LabelEncoder()
le_chest = LabelEncoder()
le_ecg = LabelEncoder()
le_angina = LabelEncoder()
le_slope = LabelEncoder()

df1["Sex"] = le_sex.fit_transform(df1["Sex"])
df1["ChestPainType"] = le_chest.fit_transform(df1["ChestPainType"])
df1["RestingECG"] = le_ecg.fit_transform(df1["RestingECG"])
df1["ExerciseAngina"] = le_angina.fit_transform(df1["ExerciseAngina"])
df1["ST_Slope"] = le_slope.fit_transform(df1["ST_Slope"])

mms = MinMaxScaler()
df1["Oldpeak"] = mms.fit_transform(df1[["Oldpeak"]])

std_cols = ["Age", "RestingBP", "Cholesterol", "MaxHR"]
ss = StandardScaler()
df1[std_cols] = ss.fit_transform(df1[std_cols])

target = df1["HeartDisease"]
# Loại bỏ RestingBP và RestingECG theo logic của bạn
features = df1[df1.columns.drop(["HeartDisease", "RestingBP", "RestingECG"])] 

X_train, X_test, Y_train, Y_test = split(features, target)

# =====================================================================
# 2. KHAI BÁO MODELS VÀ PARAM GRIDS
# =====================================================================
classifiers = [
    "SVC", "LogisticRegression", "RandomForest", "DecisionTree", 
    "KNeighbors", "XGBoost", "LightGBM"
]

models = [
    SVC(kernel="linear", C=0.1),
    LogisticRegression(random_state=0, C=10, penalty="l2"),
    RandomForestClassifier(max_depth=4, random_state=0),
    DecisionTreeClassifier(random_state=1000, max_depth=4, min_samples_leaf=1),
    KNeighborsClassifier(leaf_size=1, n_neighbors=3, p=1),
    XGBClassifier(random_state=0, n_estimators=50, max_depth=3, learning_rate=0.105, subsample=0.8, colsample_bytree=0.9, eval_metric="logloss"),
    LGBMClassifier(objective='binary', random_state=0, n_estimators=100, max_depth=4, num_leaves=15, min_child_samples=20, learning_rate=0.05, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, verbose=-1)
]

param_grids = {
    "LogisticRegression": {
        "model": LogisticRegression(random_state=0),
        "params": {  
            'penalty': ['l1', 'l2', 'elasticnet', 'none'],
            'C': [0.01, 2.5075, 5.005, 7.5025, 10],
            'max_iter': [100, 200, 300, 500],
            'solver': ['lbfgs', 'liblinear', 'saga']
        }
    },
    "KNeighbors": {
        "model": KNeighborsClassifier(p=1),
        "params": {
            'n_neighbors': [3, 5, 7, 10, 15],
            'weights': ['uniform', 'distance'],
            'algorithm': ['auto', 'ball_tree', 'kd_tree', 'brute'],
            'leaf_size': [1, 10, 20, 30, 40, 50],
        }
    },
    "DecisionTree": {
        "model": DecisionTreeClassifier(random_state=1000),
        "params": {
            'criterion': ['gini', 'entropy'],
            'max_depth': [4, 10, 20, 30, 40, 50, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4]
        }
    },
    "RandomForest": {
        "model": RandomForestClassifier(random_state=0),
        "params": {
            'n_estimators': [50, 100, 150, 200],
            'max_depth': [4, 10, 20, 30, 40, 50, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4]
        }
    },
    "SVC": {
        "model": SVC(probability=True), # Thêm probability=True cho LIME ở bước sau
        "params": {
            'kernel': ['linear', 'poly', 'rbf', 'sigmoid'],
            'C': [0.1, 2.5075, 5.005, 7.5025, 10],
        }
    },
    "XGBoost": {
        "model": XGBClassifier(random_state=0, eval_metric='logloss'),
        "params": {
            'n_estimators': [50, 100, 150, 200],
            'max_depth': [3, 5, 7],
            'learning_rate': [0.01, 0.105, 0.2],
            'subsample': [0.8, 0.9, 1.0],
            'colsample_bytree': [0.8, 0.9, 1.0]
        }
    },
    "LightGBM": {
        "model": LGBMClassifier(objective='binary', random_state=0, n_estimators=100, max_depth=4, subsample_freq=1, colsample_bytree=0.8, verbose=-1),
        "params": {
            'learning_rate': [0.01, 0.05, 0.1], 
            'num_leaves': [7, 11, 15],          
            'min_child_weight': [0.001, 0.01],  
            'subsample': [0.8, 1.0]             
        }
    }    
}

# =====================================================================
# 3. GENETIC ALGORITHM FUNCTIONS
# =====================================================================
def plot(score, x, y, c="b"):
    gen = list(range(1, len(score) + 1))
    plt.figure(figsize=(6, 4))
    plt.plot(gen, score, marker="o", color=c)
    plt.xlabel("Generation")
    plt.ylabel("Accuracy")
    plt.ylim(x, y)
    plt.grid(True)

def initilization_of_population(size, n_feat):
    population = []
    for i in range(size):
        chromosome = np.ones(n_feat, dtype=np.bool_) # Fix cảnh báo np.bool
        chromosome[: int(0.3 * n_feat)] = False
        np.random.shuffle(chromosome)
        population.append(chromosome)
    return population

def fitness_score_cv(population, model, X_train, Y_train):
    scores = []
    for chromosome in population:
        # Nếu gen toàn False (không chọn đặc trưng nào), gán điểm 0
        if not any(chromosome): 
            scores.append(0.0)
            continue
            
        X_train_selected = X_train.iloc[:, chromosome]
        
        # Đánh giá bằng Cross-Validation 3-Fold trên tập TRAIN
        cv_scores = cross_val_score(model, X_train_selected, Y_train, cv=3, scoring='accuracy', n_jobs=-1)
        scores.append(cv_scores.mean())

    scores, population = np.array(scores), np.array(population)
    inds = np.argsort(scores)
    return list(scores[inds][::-1]), list(population[inds, :][::-1])

def selection(pop_after_fit, n_parents):
    population_nextgen = []
    for i in range(n_parents):
        population_nextgen.append(pop_after_fit[i])
    return population_nextgen

def crossover(pop_after_sel):
    pop_nextgen = pop_after_sel
    for i in range(0, len(pop_after_sel), 2):
        new_par = []
        child_1, child_2 = pop_nextgen[i], pop_nextgen[i + 1]
        new_par = np.concatenate((child_1[: len(child_1) // 2], child_2[len(child_1) // 2 :]))
        pop_nextgen.append(new_par)
    return pop_nextgen

def mutation(pop_after_cross, mutation_rate, n_feat):
    mutation_range = int(mutation_rate * n_feat)
    pop_next_gen = []
    for n in range(0, len(pop_after_cross)):
        chromo = pop_after_cross[n]
        rand_posi = []
        for i in range(0, mutation_range):
            pos = randint(0, n_feat - 1)
            rand_posi.append(pos)
        for j in rand_posi:
            chromo[j] = not chromo[j]
        pop_next_gen.append(chromo)
    return pop_next_gen

def generations(model, df, label, size, n_feat, n_parents, mutation_rate, n_gen, X_train, Y_train):
    best_chromo = []
    best_score = []
    population_nextgen = initilization_of_population(size, n_feat)

    for i in range(n_gen):
        # Dùng fitness_score_cv và không truyền X_test, Y_test
        scores, pop_after_fit = fitness_score_cv(population_nextgen, model, X_train, Y_train)
        print("   -> Best CV score in generation", i + 1, ":", scores[:1])
        
        pop_after_sel = selection(pop_after_fit, n_parents)
        pop_after_cross = crossover(pop_after_sel)
        population_nextgen = mutation(pop_after_cross, mutation_rate, n_feat)

        best_chromo.append(pop_after_fit[0])
        best_score.append(scores[0])

    return best_chromo, best_score

# =====================================================================
# 4. PIPELINE: GA -> GRID SEARCH (TOP 10 LOGIC)
# =====================================================================
final_results_ga = []
grid_search_results = []
best_models_after_gs = {}
best_features_dict = {} # "Sổ tay" lưu features cho từng model

print("\n" + "="*60)
print("PHASE 1: FEATURE SELECTION BẰNG GENETIC ALGORITHM")
print("="*60)

for name, model_obj in zip(classifiers, models):
    print(f"\n[GA] Running Feature Selection for {name}...")

    best_chromo_list, best_score_list = generations(
        model=model_obj, df=features, label=target,
        size=80, n_feat=features.shape[1], n_parents=64,
        mutation_rate=0.20, n_gen=10,
        X_train=X_train, Y_train=Y_train
    )

    # Lấy features tốt nhất
    best_gen_index = np.argmax(best_score_list)
    overall_best_score = best_score_list[best_gen_index]
    overall_best_features = features.columns[best_chromo_list[best_gen_index]].tolist()
    
    # Lưu vào "Sổ tay"
    best_features_dict[name] = overall_best_features

    final_results_ga.append({
        "Classifier": name,
        "Best_GA_Accuracy": overall_best_score,
        "Selected_Features": overall_best_features,
        "Feature_Count": len(overall_best_features)
    })
    
    plot(best_score_list, 0.8, 1.0, c="orange")
    plt.title(f"GA Optimization Progress: {name}")
    plt.show()

# In bảng điểm sau Phase 1
df_ga = pd.DataFrame(final_results_ga).sort_values(by="Best_GA_Accuracy", ascending=False)
print("\n--- BẢNG KẾT QUẢ SAU KHI CHẠY GA ---")
print(df_ga[['Classifier', 'Best_GA_Accuracy', 'Feature_Count']])


print("\n" + "="*60)
print("PHASE 2: GRID SEARCH (VỚI TOP 10 CANDIDATES LOGIC)")
print("="*60)

for model_name, config in param_grids.items():
    print(f"\n[GS] Đang tối ưu siêu tham số cho {model_name}...")
    
    # 1. Trích xuất bộ gen (features) được chỉ định riêng cho model này
    if model_name not in best_features_dict:
        continue
    selected_features = best_features_dict[model_name]
    
    # 2. Cắt gọt tập Train/Test theo bộ gen đó
    X_train_ga = X_train[selected_features]
    X_test_ga = X_test[selected_features]
    
    grid_search = GridSearchCV(
        estimator=config["model"],
        param_grid=config["params"],
        scoring='accuracy',
        cv=5, # 5-Fold
        n_jobs=-1,
        verbose=0
    )
    
    try:
        # Huấn luyện GS bằng dữ liệu ĐÃ LỌC
        grid_search.fit(X_train_ga, Y_train)
        
        # --- LOGIC LỌC TOP 10 CANDIDATES CỦA BẠN GIỮ NGUYÊN ---
        cv_results_df = pd.DataFrame(grid_search.cv_results_)
        top_10_candidates = cv_results_df.sort_values(by='rank_test_score').head(10)
        
        best_test_acc_for_model = 0
        ultimate_best_model = None
        ultimate_best_params = None
        best_cv_of_ultimate = 0
        
        for index, row in top_10_candidates.iterrows():
            candidate_params = row['params']
            candidate_cv_score = row['mean_test_score']
            
            candidate_model = clone(config["model"])
            candidate_model.set_params(**candidate_params)
            
            # Train trên dữ liệu đã lọc
            candidate_model.fit(X_train_ga, Y_train)
            
            # Predict trên test đã lọc
            y_pred = candidate_model.predict(X_test_ga)
            test_acc = accuracy_score(Y_test, y_pred)
            
            if test_acc > best_test_acc_for_model:
                best_test_acc_for_model = test_acc
                ultimate_best_model = candidate_model
                ultimate_best_params = candidate_params
                best_cv_of_ultimate = candidate_cv_score
                
        # Lưu lại Nhà Vô Địch cuối cùng
        best_models_after_gs[model_name] = ultimate_best_model
        
        grid_search_results.append({
            "Classifier": model_name,
            "Base_GA_Acc": df_ga[df_ga['Classifier']==model_name]['Best_GA_Accuracy'].values[0],
            "Best_CV_Accuracy": best_cv_of_ultimate,
            "Test_Accuracy": best_test_acc_for_model,
            "Best_Params": str(ultimate_best_params)
        })
        
        print(f"🌟 CHỌN {model_name} | CV: {best_cv_of_ultimate:.4f} | Test: {best_test_acc_for_model:.4f}")
        
    except Exception as e:
        print(f"❌ Bỏ qua {model_name} do lỗi cấu hình tham số: {e}")

# In bảng so sánh cuối cùng
df_grid_results = pd.DataFrame(grid_search_results).sort_values(by="Test_Accuracy", ascending=False)
print("\n--- BẢNG SO SÁNH TỔNG HỢP: GA + GRID SEARCH ---")
print(df_grid_results[['Classifier', 'Base_GA_Acc', 'Best_CV_Accuracy', 'Test_Accuracy']])


# =====================================================================
# 5. GIẢI THÍCH MÔ HÌNH (SHAP & LIME) CHO TÂN VƯƠNG XGBOOST
# =====================================================================
if "XGBoost" in best_models_after_gs:
    print("\n" + "="*60)
    print("PHASE 3: SHAP & LIME EXPLANATION")
    print("="*60)
    
    classifier_xgb = best_models_after_gs["XGBoost"]
    
    # QUAN TRỌNG: SHAP/LIME phải dùng đúng tập dữ liệu đã bị GA cắt gọn
    xgb_features = best_features_dict["XGBoost"]
    X_train_xgb = X_train[xgb_features]
    X_test_xgb = X_test[xgb_features]
    
    i = 0  # Bệnh nhân mẫu số 0
    
    # ---------------- Plot SHAP ----------------
    shap_explainer = shap.Explainer(classifier_xgb, X_train_xgb)
    shap_values = shap_explainer(X_test_xgb)

    print(f"Explanation for patient {i} (SHAP):")
    shap.plots.waterfall(shap_values[i], show=False)
    plt.title(f"Individual Prediction Explanation", fontsize=16)
    plt.show()

    shap.plots.bar(shap_values[i], show=False)
    plt.title("Local Feature Importance Ranking", fontsize=16)
    plt.show()

    # ---------------- Plot LIME ----------------
    explainer = LimeTabularExplainer(
        training_data=X_train_xgb.values,       # Dùng .values cho LIME
        feature_names=X_train_xgb.columns,
        class_names=["Normal", "Heart Disease"],
        mode="classification",
    )

    exp = explainer.explain_instance(
        data_row=X_test_xgb.iloc[i].values, 
        predict_fn=classifier_xgb.predict_proba
    )

    print(f"Explanation for patient {i} (LIME):")
    fig = exp.as_pyplot_figure()
    plt.show()

    # ---------------- Global SHAP ----------------
    shap.plots.bar(shap_values, show=False)
    plt.title("Global Feature Importance Ranking", fontsize=16)
    plt.show()

    shap.plots.beeswarm(shap_values, show=False)
    plt.title("Global Feature Impact Distribution", fontsize=16)
    plt.show()