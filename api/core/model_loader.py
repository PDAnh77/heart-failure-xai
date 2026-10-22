import io
import os
import joblib
from fastapi import HTTPException, status
from core.supabase_client import supabase

_pipeline_instance = None

BUCKET_NAME = "heart-prediction-models"
MODEL_FILENAME = "model_predict.pkl"

# Đường dẫn model ở Local
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_MODEL_PATH = os.path.normpath(os.path.join(CURRENT_DIR, "../../notebooks/models/model_predict.pkl"))


def load_model_startup():
    global _pipeline_instance

    # Thử load từ local path
    if os.path.exists(LOCAL_MODEL_PATH):
        print(f"Found local model at: {LOCAL_MODEL_PATH}")
        try:
            _pipeline_instance = joblib.load(LOCAL_MODEL_PATH)
            print("Model loaded successfully from Local.")
            return
        except Exception as e:
            print(f"Failed to load local model. Error: {e}")
            print("Switching to Storage download...")
    else:
        print(f"Local model not found at {LOCAL_MODEL_PATH}. Attempting to download from Storage...")

    # Thử tải từ Storage (Supabase Storage hoặc Local File Storage)
    try:
        data = supabase.storage.from_(BUCKET_NAME).download(MODEL_FILENAME)

        # Load trực tiếp từ memory buffer
        _pipeline_instance = joblib.load(io.BytesIO(data))
        print("Model downloaded and loaded complete from Storage.")

        # Lưu file về local để các lần khởi động tiếp theo không phải tải lại qua mạng
        try:
            model_dir = os.path.dirname(LOCAL_MODEL_PATH)
            if model_dir:
                os.makedirs(model_dir, exist_ok=True)
            with open(LOCAL_MODEL_PATH, "wb") as f:
                f.write(data)
            print(f"Saved model locally at: {LOCAL_MODEL_PATH}")
        except Exception as save_err:
            print(f"Notice: Could not save model to disk ({save_err}).")
    except Exception as e:
        print(f"Notice: Pretrained model not found ({e}).")
        print(
            "API started successfully in graceful mode. Prediction endpoints will be disabled until a model is trained or provided."
        )
        _pipeline_instance = None


def get_pipeline():
    global _pipeline_instance
    if _pipeline_instance is None:
        # Thử nạp lại phòng trường hợp model vừa được train hoặc thêm mới
        load_model_startup()

    if _pipeline_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pretrained AI model is not loaded.",
        )
    return _pipeline_instance
