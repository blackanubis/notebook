"""
应用配置：基于环境变量与数据库存储的可变设置。
- 启动期配置（如端口、上传目录）从环境变量读取
- 运行期配置（如用户自定义的 AI Key/URL/Model）从数据库读取，支持热修改
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ===== 基础 =====
    APP_ENV: str = "production"
    APP_NAME: str = "家庭错题本"
    APP_VERSION: str = "0.1.0"

    # ===== 文件存储 =====
    UPLOAD_DIR: str = "/data/uploads"
    DB_PATH: str = "/data/db/app.db"
    STATIC_DIR: str = "/app/static"

    # ===== minimax 通用 AI（错因诊断/相似题/报告）=====
    MINIMAX_API_KEY: str = ""
    MINIMAX_BASE_URL: str = "https://api.minimax.chat/v1"
    MINIMAX_MODEL: str = "MiniMax-Text-01"

    # ===== minimax OCR / 视觉 AI（题目识别）=====
    OCR_API_KEY: str = ""
    OCR_BASE_URL: str = "https://api.minimax.chat/v1"
    OCR_MODEL: str = "MiniMax-VL-01"

    # ===== 业务约束 =====
    MAX_UPLOAD_SIZE_MB: int = 20
    SIMILAR_QUESTIONS_PER_BATCH: int = 5
    REVIEW_INTERVALS_DAYS: str = "1,3,7,14,30"  # 艾宾浩斯

    # ===== 数据库 URL（SQLAlchemy）=====
    @property
    def database_url(self) -> str:
        # 确保父目录存在
        db_path = Path(self.DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path.as_posix()}"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()