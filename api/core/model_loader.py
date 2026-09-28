import io
import os
import joblib
from core.supabase_client import supabase

_pipeline_instance = None

BUCKET_NAME = "heart-prediction-models"
MODEL_FILENAME = "model_predict.pkl"

# Đường dẫn model ở Local
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_MODEL_PATH = os.path.normpath(os.path.join(CURRENT_DIR, "../../notebooks/models/model_predict.pkl"))


def load_model_startup():
    global _pipeline_instance

    # --- Load từ local path ---
    if os.path.exists(LOCAL_MODEL_PATH):
        print(f"Found local model at: {LOCAL_MODEL_PATH}")
        try:
            _pipeline_instance = joblib.load(LOCAL_MODEL_PATH)
            print("Model loaded successfully from Local.")
            return
        except Exception as e:
            print(f"Failed to load local model. Error: {e}")
            print("Switching to Supabase download...")
    else:
        print(f"Local model not found at {LOCAL_MODEL_PATH}. Downloading from Cloud...")

    # --- Fallback tải từ Supabase ---
    print(f"Connecting Storage to download {MODEL_FILENAME}...")
    try:
        data = supabase.storage.from_(BUCKET_NAME).download(MODEL_FILENAME)
        
        # Load trực tiếp từ memory buffer (hoạt động đa nền tảng Windows, Linux, macOS, Docker)
        _pipeline_instance = joblib.load(io.BytesIO(data))
        print("Download and load complete from Supabase.")

        # Tùy chọn: Lưu cache về local để các lần khởi động tiếp theo không phải tải lại qua mạng
        try:
            cache_dir = os.path.dirname(LOCAL_MODEL_PATH)
            if cache_dir:
                os.makedirs(cache_dir, exist_ok=True)
            with open(LOCAL_MODEL_PATH, "wb") as f:
                f.write(data)
            print(f"Downloaded model locally at: {LOCAL_MODEL_PATH}")
        except Exception as cache_err:
            print(f"Notice: Could not download model to disk ({cache_err}).")
    except Exception as e:
        print("Unable to download model from Supabase.")
        print(f"Error details: {str(e)}")
        raise e


def get_pipeline():
    if _pipeline_instance is None:
        # Fallback: Nếu chưa load thì load ngay lập tức
        load_model_startup()
    return _pipeline_instance
