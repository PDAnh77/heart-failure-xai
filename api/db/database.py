from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from alembic.runtime.migration import MigrationContext
from alembic.autogenerate import produce_migrations
from alembic.operations import Operations
from alembic.operations.ops import ModifyTableOps, AddColumnOp
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


def _apply_alembic_migrations(conn, expected_tables: set[str]):
    """Tự động đối chiếu Base.metadata với database thực tế và cập nhật các cột thay đổi bằng Alembic."""

    def include_object(obj, name, type_, reflected, compare_to):
        if type_ == "table":
            return name in expected_tables
        return True

    mc = MigrationContext.configure(
        conn,
        opts={
            "compare_type": True,
            "compare_server_default": True,
            "include_object": include_object,
        },
    )
    migration_script = produce_migrations(mc, Base.metadata)
    if not migration_script.upgrade_ops or not migration_script.upgrade_ops.ops:
        print("Database connected. All tables and columns are up to date.")
        return

    op_runner = Operations(mc)
    is_sqlite = engine.dialect.name == "sqlite"
    applied_changes = 0

    for top_op in migration_script.upgrade_ops.ops:
        sub_ops = top_op.ops if isinstance(top_op, ModifyTableOps) else [top_op]
        for sub_op in sub_ops:
            op_name = type(sub_op).__name__
            table_name = getattr(sub_op, "table_name", "")
            col_name = getattr(sub_op, "column_name", None) or getattr(getattr(sub_op, "column", None), "name", "")
            print(f"Applying {op_name} on {table_name}{f'.{col_name}' if col_name else ''}...")

            # Xử lý trường hợp thêm cột NOT NULL vào bảng đã có sẵn dữ liệu nhưng chưa có server_default
            if isinstance(sub_op, AddColumnOp) and not sub_op.column.nullable and sub_op.column.server_default is None:
                has_rows = conn.execute(text(f'SELECT 1 FROM "{table_name}" LIMIT 1')).first() is not None
                if has_rows:
                    default_arg = (
                        sub_op.column.default.arg
                        if (sub_op.column.default is not None and getattr(sub_op.column.default, "is_scalar", False))
                        else None
                    )
                    sub_op.column.nullable = True
                    op_runner.invoke(sub_op)
                    if default_arg is not None and not is_sqlite:
                        conn.execute(
                            text(f'UPDATE "{table_name}" SET "{col_name}" = :val WHERE "{col_name}" IS NULL'),
                            {"val": default_arg},
                        )
                        op_runner.alter_column(table_name, col_name, nullable=False)
                    else:
                        print(f"Added '{table_name}.{col_name}' as nullable because table already contains rows.")
                    applied_changes += 1
                    continue

            if is_sqlite and isinstance(top_op, ModifyTableOps) and op_name not in ("CreateIndexOp", "DropIndexOp"):
                with op_runner.batch_alter_table(table_name) as batch_op:
                    batch_op.invoke(sub_op)
            else:
                op_runner.invoke(sub_op)
            applied_changes += 1

    if applied_changes > 0:
        print(f"Successfully applied {applied_changes} schema change(s).")
    else:
        print("Database connected. All tables and columns are up to date.")


def init_db():
    """Kiểm tra kết nối, tạo bảng mới và tự động đồng bộ các thay đổi cột khi khởi động."""
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

        with engine.begin() as conn:
            _apply_alembic_migrations(conn, expected_tables)
    except Exception as e:
        print(f"Database connection/migration error: {e}")
        raise e
