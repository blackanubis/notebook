"""
SQLAlchemy 数据库初始化。
SQLite 单文件，零运维；后续可平滑迁移到 PostgreSQL。
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

from app.config import settings


# SQLite 专用配置：单线程 + StaticPool（避免多 worker 锁文件）
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI 依赖注入：每次请求一个 Session。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """建表 + 默认数据。"""
    from app import models  # noqa: F401  注册模型
    Base.metadata.create_all(bind=engine)
    print(f"[db] 数据库已初始化: {settings.database_url}")