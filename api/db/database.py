from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """Tự động tạo tất cả các bảng trong database nếu chưa tồn tại (áp dụng cho cả Local Postgres và Supabase)."""
    import models  # Đảm bảo tất cả models đã đăng ký với Base.metadata

    print("Checking and creating database tables if not exist...")
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")
