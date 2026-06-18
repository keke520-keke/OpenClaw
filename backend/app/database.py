"""数据库配置"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DB_PATH = os.getenv("OPENCLAW_DB", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "openclaw.db"))
DB_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DB_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import app.models.db_models  # noqa: 确保所有模型注册到 Base.metadata
    Base.metadata.create_all(bind=engine)
