from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os
from routers import auth_router, user_router, prediction_router, patient_router, dataset_router, train_router
from contextlib import asynccontextmanager
import httpx, asyncio
from sqlalchemy import text
from core.model_loader import load_model_startup
from core.config import settings
from db.database import init_db, engine
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware


async def ping_self():
    url = settings.API_URL
    if not url or "localhost" in url:
        print("Skipping self ping")
        return
    health_url = f"{url.rstrip('/')}/health"

    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(health_url)
                print(f"Pinged self: ({health_url}): {r.status_code}")
        except Exception as e:
            print(f"Error pinging self: {e}")
        await asyncio.sleep(10 * 60)


async def ping_db_daily():
    url = settings.API_URL
    if not url or "localhost" in url:
        print("Skipping DB ping")
        return
    db_health_url = f"{url.rstrip('/')}/health/db"

    # Đợi server khởi động xong trước lần gọi đầu tiên
    await asyncio.sleep(30)

    while True:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(db_health_url)
                print(f"Daily DB ping: ({db_health_url}): {r.status_code}")
        except Exception as e:
            print(f"Error pinging DB: {e}")
        # Chờ 1 ngày cho lần gọi tiếp theo
        await asyncio.sleep(24 * 60 * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    load_model_startup()
    ping_self_task = asyncio.create_task(ping_self())
    ping_db_task = asyncio.create_task(ping_db_daily())
    yield
    ping_self_task.cancel()  # Hủy task khi API tắt
    ping_db_task.cancel()


app = FastAPI(title="Heart Failure Analytics API", openapi_url="/api/openapi.json", docs_url="/docs", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CLIENT_URL,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=settings.JWT_SECRET_KEY, session_cookie="oauth_state_session")

app.include_router(auth_router.router, prefix="/api/auth", tags=["Auth"])
app.include_router(user_router.router, prefix="/api/users", tags=["User"])
app.include_router(prediction_router.router, prefix="/api/predictions", tags=["Heart failure prediction"])
app.include_router(patient_router.router, prefix="/api/patients", tags=["Patient"])
app.include_router(dataset_router.router, prefix="/api/datasets", tags=["Dataset Analytics"])
app.include_router(train_router.router, prefix="/api/train", tags=["Model Training"])

# Mount Local Storage directory để phục vụ file tĩnh (ảnh biểu đồ XAI, avatar, v.v.)
storage_dir = getattr(settings, "LOCAL_STORAGE_PATH", "storage")
os.makedirs(storage_dir, exist_ok=True)
app.mount("/storage", StaticFiles(directory=storage_dir), name="storage")


@app.get("/")
def root():
    return {"message": "API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/db")
async def db_health_check():
    # Thực hiện truy vấn xuống PostgreSQL
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    # Ping REST API Gateway của Supabase
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        rest_url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/"
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.get(rest_url, headers=headers)

    return {"status": "ok", "database": "connected"}
