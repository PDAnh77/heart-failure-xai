import os
from typing import Any
from core.config import settings


class LocalStorageBucket:
    def __init__(self, base_dir: str, bucket_name: str, api_url: str = ""):
        self.base_dir = os.path.abspath(base_dir)
        self.bucket_name = bucket_name
        self.api_url = api_url

    def _resolve_path(self, path: str) -> str:
        clean_path = path.lstrip("/\\").replace("\\", "/")
        parts = clean_path.split("/")
        return os.path.join(self.base_dir, self.bucket_name, *parts)

    def upload(self, path: str, file: Any, file_options: dict = None) -> dict:
        full_path = self._resolve_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Handle different file content types (bytes, str, or file-like object)
        if isinstance(file, (bytes, bytearray)):
            data = file
        elif isinstance(file, str):
            data = file.encode("utf-8")
        elif hasattr(file, "read"):
            data = file.read()
            if isinstance(data, str):
                data = data.encode("utf-8")
        else:
            data = bytes(file)

        with open(full_path, "wb") as f:
            f.write(data)

        return {"Key": f"{self.bucket_name}/{path}"}

    def download(self, path: str) -> bytes:
        full_path = self._resolve_path(path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Object '{path}' not found in local bucket '{self.bucket_name}'")

        with open(full_path, "rb") as f:
            return f.read()

    def get_public_url(self, path: str) -> str:
        clean_path = path.lstrip("/\\").replace("\\", "/")
        if self.api_url:
            return f"{self.api_url.rstrip('/')}/storage/{self.bucket_name}/{clean_path}"
        return f"/storage/{self.bucket_name}/{clean_path}"


class LocalStorageClient:
    def __init__(self, base_dir: str, api_url: str = ""):
        self.base_dir = base_dir
        self.api_url = api_url

    def from_(self, bucket_name: str) -> LocalStorageBucket:
        return LocalStorageBucket(self.base_dir, bucket_name, self.api_url)


def get_storage_client():
    storage_type = getattr(settings, "STORAGE_TYPE", "supabase").lower()

    if storage_type == "local":
        storage_dir = getattr(settings, "LOCAL_STORAGE_PATH", "storage")
        print(f"Using Local File Storage at: {os.path.abspath(storage_dir)}")
        return LocalStorageClient(base_dir=storage_dir, api_url=settings.API_URL)

    # Chế độ Supabase: Yêu cầu thông tin cấu hình rõ ràng, không fallback ngầm
    if not (settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY):
        raise ValueError(
            "STORAGE_TYPE is set to 'supabase', but SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing in .env."
        )

    from supabase import create_client

    print("Using Supabase Cloud Storage.")
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return client.storage


storage = get_storage_client()
