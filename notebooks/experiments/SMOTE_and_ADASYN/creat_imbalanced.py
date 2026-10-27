import pandas as pd
import os
from sklearn.preprocessing import LabelEncoder

# 1. Đường dẫn file đầu vào (raw dataset — chưa encode)
input_path = "../input/heart-failure-prediction/heart.csv"
df = pd.read_csv(input_path)

# ----------------------------------------------------------
# 2. LABEL ENCODING cho các cột categorical
# ----------------------------------------------------------
categorical_cols = ['Sex', 'ChestPainType', 'RestingECG', 'ExerciseAngina', 'ST_Slope']
le = LabelEncoder()
for col in categorical_cols:
    df[col] = le.fit_transform(df[col].astype(str))

print("Sau khi encode:")
print(df[categorical_cols].head(3))

# ----------------------------------------------------------
# 3. ÉP MẤT CÂN BẰNG
# ----------------------------------------------------------
df_class_1 = df[df['HeartDisease'] == 1]
df_class_0 = df[df['HeartDisease'] == 0]

# Giữ nguyên lớp 1, chỉ lấy ngẫu nhiên 100 dòng của lớp 0
df_class_0_minority = df_class_0
df_class_1_sampled = df_class_1.sample(n=331, random_state=42)

df_imbalanced = pd.concat([df_class_1_sampled, df_class_0_minority]).sample(frac=1, random_state=42).reset_index(drop=True)

# ----------------------------------------------------------
# 4. LƯU KẾT QUẢ
# ----------------------------------------------------------
original_filename = os.path.basename(input_path)
new_filename = f"test_balanced_{original_filename}"
output_folder = "../input/testing_dataset"
os.makedirs(output_folder, exist_ok=True)
output_path = os.path.join(output_folder, new_filename)

df_imbalanced.to_csv(output_path, index=False)

print(f"\nĐã lưu file thành công tại: {output_path}")
print("-" * 30)
print("Phân phối mới:\n", df_imbalanced['HeartDisease'].value_counts())
