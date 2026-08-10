"""创建 SQLAlchemy 引擎、会话、基类，FastAPI 依赖注入用。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI 依赖注入：每次请求获取会话，结束后自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
