from sqlalchemy import create_engine, inspect
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
    """Kiểm tra kết nối và tạo các bảng trong database nếu chưa tồn tại."""
    import models  # Đảm bảo tất cả models đã đăng ký với Base.metadata

    try:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        expected_tables = set(Base.metadata.tables.keys())

        missing_tables = expected_tables - existing_tables

        if missing_tables:
            print(f"Creating missing tables: {sorted(list(missing_tables))}...")
            Base.metadata.create_all(bind=engine)
            print("Missing tables created successfully.")
        else:
            print("Database connected. All required tables are verified.")
    except Exception as e:
        print(f"Database connection error: {e}")
        raise e
