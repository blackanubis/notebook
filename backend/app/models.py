"""
SQLAlchemy ORM 模型
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, JSON,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Child(Base):
    """孩子档案"""
    __tablename__ = "children"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False)
    grade = Column(String(32), default="")  # 三年级
    textbook_version = Column(String(32), default="人教版")  # 人教版/北师大版/苏教版
    avatar_color = Column(String(16), default="#185FA5")  # 头像背景色
    created_at = Column(DateTime, default=datetime.utcnow)

    questions = relationship("Question", back_populates="child", cascade="all, delete-orphan")


class Question(Base):
    """题目（错题/正题统一存储）"""
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    child_id = Column(Integer, ForeignKey("children.id", ondelete="CASCADE"), nullable=False)

    # 内容
    image_url = Column(String(255), default="")  # 题目原图
    ocr_text = Column(Text, default="")          # OCR 识别的题目文本
    student_answer = Column(Text, default="")    # 学生答案
    correct_answer = Column(Text, default="")    # 标准答案（AI 生成）
    solution_steps = Column(Text, default="")   # 解答步骤（AI 生成，Markdown）
    error_reason = Column(Text, default="")      # 错因诊断（AI 生成）

    # 分类
    subject = Column(String(32), default="")          # 学科
    knowledge_point = Column(String(128), default="") # 知识点
    error_type = Column(String(32), default="")       # 错因类型：concept/calculation/misread/method/careless
    difficulty = Column(String(16), default="medium") # easy/medium/hard

    # 状态
    is_correct = Column(Boolean, default=False)  # ⭐ 对/错（手动标记）
    correct_source = Column(String(16), default="user")  # user/ai
    review_status = Column(String(16), default="new")  # new/learning/mastered/archive/stubborn
    is_stubborn = Column(Boolean, default=False)  # 顽固错题标记

    # 元数据
    source = Column(String(32), default="photo")  # photo/manual/import
    extra = Column(JSON, default=dict)             # 扩展字段

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_reviewed_at = Column(DateTime, nullable=True)

    child = relationship("Child", back_populates="questions")
    practices = relationship("Practice", back_populates="question", cascade="all, delete-orphan")


class Practice(Base):
    """练习记录（变式题作答与评判）"""
    __tablename__ = "practices"

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)

    # AI 生成的相似题
    practice_question = Column(Text, default="")
    practice_answer = Column(Text, default="")  # 标准答案
    practice_steps = Column(Text, default="")   # 步骤

    # 学生作答与评判
    student_response = Column(Text, default="")  # 学生作答
    student_image_url = Column(String(255), default="")  # 拍照作答
    score = Column(Float, default=0.0)            # 得分 0-100
    is_correct = Column(Boolean, default=False)
    error_point = Column(Text, default="")        # 扣分点说明
    ai_judgment = Column(Text, default="")        # AI 评判详情

    created_at = Column(DateTime, default=datetime.utcnow)

    question = relationship("Question", back_populates="practices")


class ReviewSchedule(Base):
    """复习计划（艾宾浩斯）"""
    __tablename__ = "review_schedules"

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    child_id = Column(Integer, ForeignKey("children.id", ondelete="CASCADE"), nullable=False)
    next_review_at = Column(DateTime, nullable=False)
    interval_days = Column(Integer, default=1)
    review_round = Column(Integer, default=1)  # 第几轮复习
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Report(Base):
    """学情报告（周报/月报）"""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    child_id = Column(Integer, ForeignKey("children.id", ondelete="CASCADE"), nullable=False)
    report_type = Column(String(16), default="weekly")  # weekly/monthly
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # 数据快照
    total_questions = Column(Integer, default=0)
    total_correct = Column(Integer, default=0)
    total_wrong = Column(Integer, default=0)
    accuracy_rate = Column(Float, default=0.0)
    mastered_count = Column(Integer, default=0)
    stubborn_count = Column(Integer, default=0)

    # AI 生成的报告内容
    summary = Column(Text, default="")
    strengths = Column(Text, default="")  # JSON: [{"kp":"...", "rate":0.95}]
    weaknesses = Column(Text, default="")
    improvements = Column(Text, default="")
    suggestions = Column(Text, default="")  # 3 条建议

    # 文件
    pdf_url = Column(String(255), default="")

    created_at = Column(DateTime, default=datetime.utcnow)


class Setting(Base):
    """运行期设置（用户可修改，存数据库）"""
    __tablename__ = "settings"

    key = Column(String(64), primary_key=True)
    value = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)