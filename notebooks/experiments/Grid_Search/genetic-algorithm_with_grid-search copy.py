import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from random import randint
import warnings

from sklearn.calibration import LabelEncoder
from sklearn.discriminant_analysis import StandardScaler
from sklearn.preprocessing import MinMaxScaler

warnings.filterwarnings("ignore")

from sklearn.model_selection import train_test_split, GridSearchCV

def split(features, target):
    X_train, X_test, Y_train, Y_test = train_test_split(features, target, test_size=0.2, random_state=42)
    return X_train, X_test, Y_train, Y_test


from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

from sklearn.metrics import accuracy_score

classifiers = [
    "SVC",
    "LogisticRegression",
    "RandomForest",
    "DecisionTree",
    "KNeighbors",
    "XGBoost",
    "LightGBM",
]

models = [
    SVC(kernel="linear", C=0.1),
    LogisticRegression(random_state=0, C=10, penalty="l2"),
    RandomForestClassifier(max_depth=4, random_state=0),
    DecisionTreeClassifier(random_state=1000, max_depth=4, min_samples_leaf=1),
    KNeighborsClassifier(leaf_size=1, n_neighbors=3, p=1),
    XGBClassifier(
        random_state=0,
        n_estimators=50,
        max_depth=3,
        learning_rate=0.105,
        subsample=0.8,
        colsample_bytree=0.9,
        eval_metric="logloss",
    ),
    LGBMClassifier(
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
        verbose=-1 )
]


def acc_score(df, label):
    Score = pd.DataFrame({"Classifier": classifiers})
    j = 0
    acc = []
    X_train, X_test, Y_train, Y_test = split(df, label)
    for i in models:
        model = i
        model.fit(X_train, Y_train)
        predictions = model.predict(X_test)
        acc.append(accuracy_score(Y_test, predictions))
        j = j + 1
    Score["Accuracy"] = acc
    Score.sort_values(by="Accuracy", ascending=False, inplace=True)
    Score.reset_index(drop=True, inplace=True)
    return Score


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
        chromosome = np.ones(n_feat, dtype=np.bool)
        chromosome[: int(0.3 * n_feat)] = False
        np.random.shuffle(chromosome)
        population.append(chromosome)
    return population


def fitness_score(population, model, X_train, X_test, Y_train, Y_test):
    scores = []
    for chromosome in population:
        X_train_selected = X_train.iloc[:, chromosome]
        X_test_selected = X_test.iloc[:, chromosome]

        model.fit(X_train_selected, Y_train)
        predictions = model.predict(X_test_selected)
        scores.append(accuracy_score(Y_test, predictions))

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


def generations(model, df, label, size, n_feat, n_parents, mutation_rate, n_gen, X_train, X_test, Y_train, Y_test):
    best_chromo = []
    best_score = []
    population_nextgen = initilization_of_population(size, n_feat)

    for i in range(n_gen):
        scores, pop_after_fit = fitness_score(population_nextgen, model, X_train, X_test, Y_train, Y_test)
        print("Best score in generation", i + 1, ":", scores[:1])
        pop_after_sel = selection(pop_after_fit, n_parents)
        pop_after_cross = crossover(pop_after_sel)
        population_nextgen = mutation(pop_after_cross, mutation_rate, n_feat)

        best_chromo.append(pop_after_fit[0])
        best_score.append(scores[0])

    return best_chromo, best_score


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

target = df1["HeartDisease"]
features = df1[df1.columns.drop(["HeartDisease"])]

print("Heart Failure dataset:\n", features.shape[0], "Records\n", features.shape[1], "Features")

print(features.head())
print("All the features in this dataset have continuous values")

score1 = acc_score(features, target)
print(score1)

X_train, X_test, Y_train, Y_test = split(features, target)


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


final_results = []

print("--- Starting Feature Selection Optimization using Genetic Algorithm ---")
for name, model_obj in zip(classifiers, models):
    print(f"\nRunning GA for model: {name}...")

    # Run GA
    best_chromo_list, best_score_list = generations(
        model=model_obj,
        df=features,
        label=target,
        size=80,
        n_feat=features.shape[1],
        n_parents=64,
        mutation_rate=0.20,
        n_gen=10,
        X_train=X_train,
        X_test=X_test,
        Y_train=Y_train,
        Y_test=Y_test,
    )

    plot(best_score_list, 0.8, 1.0, c="orange")
    plt.title(f"GA Optimization Progress: {name}")
    plt.show()

    # Get the best result from the final generation
    best_gen_index = np.argmax(best_score_list)

    overall_best_score = best_score_list[best_gen_index]
    overall_best_features = features.columns[best_chromo_list[best_gen_index]].tolist()

    final_results.append(
        {
            "Classifier": name,
            "Best_GA_Accuracy": overall_best_score,
            "Selected_Features": overall_best_features,
            "Feature_Count": len(overall_best_features),
            "Best_Generation": best_gen_index + 1  # +1 vì index bắt đầu từ 0
        }
    )
    
pd.set_option('display.max_colwidth', None)
# Convert results to DataFrame for easier comparison
df_final_comparison = pd.DataFrame(final_results).sort_values(by="Best_GA_Accuracy", ascending=False)
print("\n--- COMPARISON TABLE AFTER GA ---")
print(df_final_comparison)

# final_results = []
# ga_gs_results = [] # Thêm list để lưu kết quả sau khi qua cả 2 bước

# print("--- Bắt đầu Pipeline: Tối ưu Features (GA) -> Tối ưu Model (Grid Search) ---")
# for name, model_obj in zip(classifiers, models):
#     print(f"\n========== MODEL: {name} ==========")
#     print("1. Đang chạy thuật toán GA để chọn Features...")

#     # Chạy GA
#     best_chromo_list, best_score_list = generations(
#         model=model_obj,
#         df=features,
#         label=target,
#         size=80,
#         n_feat=features.shape[1],
#         n_parents=64,
#         mutation_rate=0.20,
#         n_gen=10,
#         X_train=X_train,
#         X_test=X_test,
#         Y_train=Y_train,
#         Y_test=Y_test,
#     )

#     plot(best_score_list, 0.8, 1.0, c="orange")
#     plt.title(f"GA Optimization Progress: {name}")
#     plt.show()

#     # Lấy kết quả cao nhất từ GA (Global Best)
#     best_gen_index = np.argmax(best_score_list)
#     overall_best_score = best_score_list[best_gen_index]
#     overall_best_features = features.columns[best_chromo_list[best_gen_index]].tolist()

#     print(f"-> Hoàn thành GA! Đạt Accuracy {overall_best_score:.4f} với {len(overall_best_features)} features.")

#     final_results.append(
#         {
#             "Classifier": name,
#             "Best_GA_Accuracy": overall_best_score,
#             "Selected_Features": overall_best_features,
#             "Feature_Count": len(overall_best_features),
#             "Best_Generation": best_gen_index + 1
#         }
#     )
    
#     # ==========================================
#     # BƯỚC 2: TÍCH HỢP GRID SEARCH
#     # ==========================================
#     if name in param_grids:
#         print("2. Đang chạy Grid Search trên các features đã được chọn...")
        
#         # CHỈ lấy những features mà GA đã chọn ra
#         X_train_ga = X_train[overall_best_features]
#         X_test_ga = X_test[overall_best_features]
        
#         config = param_grids[name]
        
#         grid_search = GridSearchCV(
#             estimator=config["model"],
#             param_grid=config["params"],
#             scoring='accuracy',
#             cv=5,                # 5-fold cross validation
#             n_jobs=-1,           # Dùng toàn bộ nhân CPU
#             verbose=0
#         )
        
#         try:
#             # Huấn luyện GridSearch
#             grid_search.fit(X_train_ga, Y_train)
            
#             # Đánh giá lại trên tập test
#             best_estimator = grid_search.best_estimator_
#             y_pred_gs = best_estimator.predict(X_test_ga)
#             test_acc_gs = accuracy_score(Y_test, y_pred_gs)
            
#             print(f"-> Hoàn thành Grid Search! Cập nhật Accuracy thành: {test_acc_gs:.4f}")
            
#             ga_gs_results.append({
#                 "Classifier": name,
#                 "Base_GA_Acc": overall_best_score,
#                 "Final_GridSearch_Acc": test_acc_gs,
#                 "Best_Params": str(grid_search.best_params_)
#             })
            
#         except Exception as e:
#             print(f"-> Bỏ qua lưới cấu hình lỗi của {name}...")

# pd.set_option('display.max_colwidth', None)

# # In bảng 1: Kết quả sau khi chạy GA
# df_final_comparison = pd.DataFrame(final_results).sort_values(by="Best_GA_Accuracy", ascending=False)
# print("\n--- BẢNG 1: KẾT QUẢ CHỌN LỌC ĐẶC TRƯNG (GA) ---")
# print(df_final_comparison[['Classifier', 'Best_GA_Accuracy', 'Feature_Count', 'Best_Generation']])

# # In bảng 2: Kết quả cuối cùng (GA + Grid Search)
# if ga_gs_results:
#     df_grid_results = pd.DataFrame(ga_gs_results).sort_values(by="Final_GridSearch_Acc", ascending=False)
#     print("\n--- BẢNG 2: KẾT QUẢ CUỐI CÙNG (GA + GRID SEARCH) ---")
#     print(df_grid_results[['Classifier', 'Base_GA_Acc', 'Final_GridSearch_Acc']])