import pandas as pd
import numpy as np
from collections import Counter
from imblearn.over_sampling import ADASYN

# ----------------------------------------------------------
# CẤU HÌNH
# ----------------------------------------------------------
INPUT_PATH = "../input/testing_dataset/test_imbalanced_heart.csv"
TARGET_COLUMN = "HeartDisease"
OUTPUT_PATH = "../input/testing_dataset/test_adasyn_output.csv"

# ----------------------------------------------------------
# 1. LOAD DỮ LIỆU
# ----------------------------------------------------------
df = pd.read_csv(INPUT_PATH)
print(f"Shape ban đầu: {df.shape}")

X = df.drop(columns=[TARGET_COLUMN])
y = df[TARGET_COLUMN]

print(f"\nPhân phối nhãn TRƯỚC khi xử lý: {Counter(y)}")
minority_ratio = y.value_counts().min() / y.value_counts().max()
print(f"Tỷ lệ thiểu số / đa số: {minority_ratio:.2%}")

# ----------------------------------------------------------
# 2. KIỂM TRA CÂN BẰNG — chỉ chạy ADASYN khi thực sự mất cân bằng
# ----------------------------------------------------------
if minority_ratio >= 0.9:
    print("\n[SKIP] Dataset đã cân bằng (ratio >= 0.9). ADASYN không cần thiết.")
else:
    # ----------------------------------------------------------
    # 3. ÁP DỤNG ADASYN
    # ----------------------------------------------------------
    adasyn = ADASYN(random_state=42)
    X_resampled, y_resampled = adasyn.fit_resample(X, y)

    # ----------------------------------------------------------
    # 4. SỬA LỖI NỘI SUY — làm tròn cột phân loại
    # ADASYN nội suy nên các cột phân loại có thể bị ra số thập phân (VD: 0.6, 1.3)
    # ----------------------------------------------------------
    categorical_cols = [col for col in X.columns if X[col].nunique() <= 6]
    X_resampled = pd.DataFrame(X_resampled, columns=X.columns)
    for col in categorical_cols:
        X_resampled[col] = X_resampled[col].round()

    y_resampled = pd.Series(y_resampled, name=TARGET_COLUMN)

    print(f"\nPhân phối nhãn SAU khi xử lý:  {Counter(y_resampled)}")
    print(f"Shape sau khi xử lý: {X_resampled.shape}")
    print(f"Số dòng được thêm:   {len(X_resampled) - len(X)}")

    # ----------------------------------------------------------
    # 5. KIỂM TRA GIÁ TRỊ SAU KHI LÀM TRÒN
    # ----------------------------------------------------------
    if categorical_cols:
        print(f"\nKiểm tra unique values các cột phân loại sau khi round:")
        for col in categorical_cols:
            print(f"  {col}: {sorted(X_resampled[col].unique())}")

    # ----------------------------------------------------------
    # 6. LƯU KẾT QUẢ
    # ----------------------------------------------------------
    df_output = pd.concat([X_resampled, y_resampled], axis=1)
    df_output.to_csv(OUTPUT_PATH, index=False)
    print(f"\nĐã lưu kết quả tại: {OUTPUT_PATH}")
