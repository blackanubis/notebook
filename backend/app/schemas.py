"""
Pydantic 数据校验模型（请求/响应）
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ========== Children ==========
class ChildCreate(BaseModel):
    name: str
    grade: Optional[str] = ""
    textbook_version: Optional[str] = "人教版"
    avatar_color: Optional[str] = "#185FA5"


class ChildUpdate(BaseModel):
    name: Optional[str] = None
    grade: Optional[str] = None
    textbook_version: Optional[str] = None
    avatar_color: Optional[str] = None


class ChildOut(BaseModel):
    id: int
    name: str
    grade: str
    textbook_version: str
    avatar_color: str
    question_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


# ========== Questions ==========
class QuestionCreate(BaseModel):
    child_id: int
    image_url: Optional[str] = ""
    ocr_text: Optional[str] = ""
    student_answer: Optional[str] = ""
    is_correct: bool = False
    subject: Optional[str] = ""
    source: Optional[str] = "photo"


class QuestionUpdate(BaseModel):
    ocr_text: Optional[str] = None
    student_answer: Optional[str] = None
    correct_answer: Optional[str] = None
    solution_steps: Optional[str] = None
    error_reason: Optional[str] = None
    subject: Optional[str] = None
    knowledge_point: Optional[str] = None
    error_type: Optional[str] = None
    difficulty: Optional[str] = None
    is_correct: Optional[bool] = None
    review_status: Optional[str] = None


class QuestionOut(BaseModel):
    id: int
    child_id: int
    image_url: str
    ocr_text: str
    student_answer: str
    correct_answer: str
    solution_steps: str
    error_reason: str
    subject: str
    knowledge_point: str
    error_type: str
    difficulty: str
    is_correct: bool
    review_status: str
    is_stubborn: bool
    created_at: datetime
    last_reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== OCR ==========
class OCRRequest(BaseModel):
    image_url: str
    child_id: int


class OCRQuestionItem(BaseModel):
    index: int
    text: str
    subject_hint: str = ""
    is_correct: bool = False  # 用户后补


class OCRResponse(BaseModel):
    questions: List[OCRQuestionItem]
    raw_text: str
    note: str = ""  # 兜底提示


# ========== AI: 错因分析 ==========
class ErrorAnalyzeRequest(BaseModel):
    question_text: str
    student_answer: str
    subject: str = "数学"
    knowledge_point: str = ""


class ErrorAnalyzeResponse(BaseModel):
    error_type: str
    error_reason: str
    correct_answer: str
    solution_steps: str  # Markdown
    knowledge_point: str


# ========== AI: 相似题出题 ==========
class SimilarQuestionsRequest(BaseModel):
    question_text: str
    correct_answer: str
    subject: str = "数学"
    knowledge_point: str = ""
    count: int = 5


class SimilarQuestionItem(BaseModel):
    index: int
    question: str
    answer: str
    steps: str = ""


class SimilarQuestionsResponse(BaseModel):
    questions: List[SimilarQuestionItem]


# ========== AI: 评判 ==========
class JudgeRequest(BaseModel):
    practice_question: str
    practice_answer: str  # 标准答案
    student_response: str
    subject: str = "数学"


class JudgeResponse(BaseModel):
    score: float  # 0-100
    is_correct: bool
    error_point: str
    ai_judgment: str  # 详细评判


# ========== AI: 报告 ==========
class ReportRequest(BaseModel):
    child_id: int
    report_type: str = "weekly"  # weekly/monthly


class ReportOut(BaseModel):
    id: int
    child_id: int
    report_type: str
    period_start: datetime
    period_end: datetime
    total_questions: int
    total_correct: int
    total_wrong: int
    accuracy_rate: float
    summary: str
    strengths: str
    weaknesses: str
    improvements: str
    suggestions: str
    pdf_url: str
    created_at: datetime

    class Config:
        from_attributes = True


# ========== Settings ==========
class SettingItem(BaseModel):
    key: str
    value: str


class AISettings(BaseModel):
    """AI 设置分组（OCR 与文本分开）"""
    # 通用 AI
    text_api_key: str = ""
    text_base_url: str = ""
    text_model: str = ""
    # OCR AI
    ocr_api_key: str = ""
    ocr_base_url: str = ""
    ocr_model: str = ""
    # 推送
    pushplus_token: str = ""
    smtp_host: str = ""
    smtp_user: str = ""
    smtp_pass: str = ""
    notify_email: str = ""


# ========== Export ==========
class ExportRequest(BaseModel):
    question_ids: List[int]  # 选中的题目 ID
    template: str = "questions_only"  # questions_only / with_answers / with_answer_sheet
    child_id: int


class ExportResponse(BaseModel):
    pdf_url: str
    file_size: int