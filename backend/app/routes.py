"""
所有 API 路由（统一在一个文件，方便维护；如需拆分可后续按子文件拆）。
"""
import os
import json
import uuid
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.config import settings
from app.database import get_db, init_db, SessionLocal
from app import models, schemas
from app.ai_service import (
    analyze_error, generate_similar_questions, judge_answer,
    get_text_ai_config, get_ocr_ai_config,
)
from app.ocr_service import recognize_questions_from_image, encode_image_to_base64
from app.pdf_service import generate_pdf, save_pdf
from app.report_service import generate_weekly_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


# ============ Children ============

@router.get("/children", response_model=List[schemas.ChildOut])
def list_children(db: Session = Depends(get_db)):
    rows = db.query(models.Child).order_by(models.Child.id).all()
    out = []
    for c in rows:
        count = db.query(models.Question).filter(models.Question.child_id == c.id).count()
        out.append(schemas.ChildOut(
            id=c.id, name=c.name, grade=c.grade or "",
            textbook_version=c.textbook_version or "",
            avatar_color=c.avatar_color or "#185FA5",
            question_count=count,
            created_at=c.created_at,
        ))
    return out


@router.post("/children", response_model=schemas.ChildOut)
def create_child(payload: schemas.ChildCreate, db: Session = Depends(get_db)):
    c = models.Child(**payload.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return schemas.ChildOut(
        id=c.id, name=c.name, grade=c.grade or "",
        textbook_version=c.textbook_version or "",
        avatar_color=c.avatar_color or "#185FA5",
        question_count=0,
        created_at=c.created_at,
    )


@router.put("/children/{child_id}", response_model=schemas.ChildOut)
def update_child(child_id: int, payload: schemas.ChildUpdate, db: Session = Depends(get_db)):
    c = db.query(models.Child).filter(models.Child.id == child_id).first()
    if not c:
        raise HTTPException(404, "孩子不存在")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    count = db.query(models.Question).filter(models.Question.child_id == c.id).count()
    return schemas.ChildOut(
        id=c.id, name=c.name, grade=c.grade or "",
        textbook_version=c.textbook_version or "",
        avatar_color=c.avatar_color or "#185FA5",
        question_count=count,
        created_at=c.created_at,
    )


@router.delete("/children/{child_id}")
def delete_child(child_id: int, db: Session = Depends(get_db)):
    c = db.query(models.Child).filter(models.Child.id == child_id).first()
    if not c:
        raise HTTPException(404, "孩子不存在")
    db.delete(c)
    db.commit()
    return {"ok": True}


# ============ Upload ============

@router.post("/upload/image")
async def upload_image(file: UploadFile = File(...)):
    """上传图片，返回 URL"""
    upload_dir = Path(settings.UPLOAD_DIR) / "questions"
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "img.jpg").suffix.lower() or ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".heic"}:
        raise HTTPException(400, "不支持的图片格式")

    new_name = f"{uuid.uuid4().hex}{ext}"
    file_path = upload_dir / new_name

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"图片超过 {settings.MAX_UPLOAD_SIZE_MB}MB")

    file_path.write_bytes(content)
    return {"url": f"/files/questions/{new_name}", "filename": new_name}


# ============ OCR ============

@router.post("/ocr/recognize", response_model=schemas.OCRResponse)
async def ocr_recognize(payload: schemas.OCRRequest, db: Session = Depends(get_db)):
    """
    识别图片中的所有题目（基于 minimax 视觉模型）。
    注意：minimax 视觉模型对手写公式的精度不如专用 OCR，
    识别结果应在录入页手动核对与编辑。
    """
    # 把 /files/xxx 转换为本地路径
    if not payload.image_url.startswith("/files/"):
        raise HTTPException(400, "image_url 必须以 /files/ 开头")
    rel_path = payload.image_url[len("/files/"):]
    file_path = Path(settings.UPLOAD_DIR) / rel_path
    if not file_path.exists():
        raise HTTPException(404, "图片文件不存在")

    try:
        b64, mime = await encode_image_to_base64(str(file_path))
        result = await recognize_questions_from_image(b64, mime)
    except Exception as e:
        logger.exception("OCR 识别失败")
        raise HTTPException(500, f"OCR 识别失败: {e}")

    note = ""
    if not result.get("subject"):
        note = "未识别出学科，请在录入页手动选择。"
    return schemas.OCRResponse(
        questions=[
            schemas.OCRQuestionItem(
                index=q.get("index", i + 1),
                text=q.get("text", ""),
                subject_hint=result.get("subject", ""),
                is_correct=False,
            )
            for i, q in enumerate(result.get("questions", []))
        ],
        raw_text=result.get("raw_text", ""),
        note=note,
    )


# ============ Questions ============

@router.get("/questions", response_model=List[schemas.QuestionOut])
def list_questions(
    child_id: Optional[int] = None,
    subject: Optional[str] = None,
    is_correct: Optional[bool] = None,
    review_status: Optional[str] = None,
    knowledge_point: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(models.Question)
    if child_id is not None:
        q = q.filter(models.Question.child_id == child_id)
    if subject:
        q = q.filter(models.Question.subject == subject)
    if is_correct is not None:
        q = q.filter(models.Question.is_correct == is_correct)
    if review_status:
        q = q.filter(models.Question.review_status == review_status)
    if knowledge_point:
        q = q.filter(models.Question.knowledge_point.contains(knowledge_point))
    q = q.order_by(desc(models.Question.created_at))
    rows = q.offset(offset).limit(limit).all()
    return rows


@router.get("/questions/{question_id}", response_model=schemas.QuestionOut)
def get_question(question_id: int, db: Session = Depends(get_db)):
    q = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not q:
        raise HTTPException(404, "题目不存在")
    return q


@router.post("/questions", response_model=schemas.QuestionOut)
def create_question(payload: schemas.QuestionCreate, db: Session = Depends(get_db)):
    q = models.Question(**payload.model_dump())
    q.updated_at = datetime.utcnow()
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


@router.put("/questions/{question_id}", response_model=schemas.QuestionOut)
def update_question(question_id: int, payload: schemas.QuestionUpdate, db: Session = Depends(get_db)):
    q = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not q:
        raise HTTPException(404, "题目不存在")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(q, k, v)
    q.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(q)
    return q


@router.delete("/questions/{question_id}")
def delete_question(question_id: int, db: Session = Depends(get_db)):
    q = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not q:
        raise HTTPException(404, "题目不存在")
    db.delete(q)
    db.commit()
    return {"ok": True}


# ============ AI: 错因分析 ============

@router.post("/ai/analyze-error", response_model=schemas.ErrorAnalyzeResponse)
async def ai_analyze_error(payload: schemas.ErrorAnalyzeRequest):
    try:
        result = await analyze_error(
            question_text=payload.question_text,
            student_answer=payload.student_answer,
            subject=payload.subject,
            knowledge_point=payload.knowledge_point,
        )
        return schemas.ErrorAnalyzeResponse(
            error_type=result.get("error_type", "concept"),
            error_reason=result.get("error_reason", ""),
            correct_answer=result.get("correct_answer", ""),
            solution_steps=result.get("solution_steps", ""),
            knowledge_point=result.get("knowledge_point", payload.knowledge_point),
        )
    except Exception as e:
        logger.exception("错因分析失败")
        raise HTTPException(500, f"AI 分析失败: {e}")


# ============ AI: 相似题 ============

@router.post("/ai/similar-questions", response_model=schemas.SimilarQuestionsResponse)
async def ai_similar_questions(payload: schemas.SimilarQuestionsRequest):
    try:
        items = await generate_similar_questions(
            question_text=payload.question_text,
            correct_answer=payload.correct_answer,
            subject=payload.subject,
            knowledge_point=payload.knowledge_point,
            count=min(payload.count, 10),
        )
        return schemas.SimilarQuestionsResponse(
            questions=[
                schemas.SimilarQuestionItem(
                    index=q.get("index", i + 1),
                    question=q.get("question", ""),
                    answer=q.get("answer", ""),
                    steps=q.get("steps", ""),
                )
                for i, q in enumerate(items)
            ]
        )
    except Exception as e:
        logger.exception("相似题生成失败")
        raise HTTPException(500, f"AI 生成失败: {e}")


# ============ Practice ============

@router.post("/practice/judge", response_model=schemas.JudgeResponse)
async def practice_judge(payload: schemas.JudgeRequest):
    try:
        result = await judge_answer(
            question=payload.practice_question,
            answer=payload.practice_answer,
            response=payload.student_response,
            subject=payload.subject,
        )
        return schemas.JudgeResponse(**result)
    except Exception as e:
        logger.exception("评判失败")
        raise HTTPException(500, f"AI 评判失败: {e}")


@router.post("/practice/save")
def save_practice(
    question_id: int = Form(...),
    practice_question: str = Form(...),
    practice_answer: str = Form(...),
    student_response: str = Form(""),
    score: float = Form(0),
    is_correct: bool = Form(False),
    error_point: str = Form(""),
    ai_judgment: str = Form(""),
    db: Session = Depends(get_db),
):
    p = models.Practice(
        question_id=question_id,
        practice_question=practice_question,
        practice_answer=practice_answer,
        student_response=student_response,
        score=score,
        is_correct=is_correct,
        error_point=error_point,
        ai_judgment=ai_judgment,
    )
    db.add(p)
    # 更新题目的复习状态
    q = db.query(models.Question).filter(models.Question.id == question_id).first()
    if q:
        q.last_reviewed_at = datetime.utcnow()
        if is_correct:
            q.review_status = "mastered"
        else:
            # 重做又错 -> 升级为顽固
            if q.review_status in ("learning", "new"):
                q.is_stubborn = True
                q.review_status = "stubborn"
    db.commit()
    db.refresh(p)
    return {"practice_id": p.id, "ok": True}


# ============ Export / 打印 ============

@router.post("/export/pdf", response_model=schemas.ExportResponse)
def export_pdf(payload: schemas.ExportRequest, db: Session = Depends(get_db)):
    child = db.query(models.Child).filter(models.Child.id == payload.child_id).first()
    if not child:
        raise HTTPException(404, "孩子不存在")
    qs = db.query(models.Question).filter(models.Question.id.in_(payload.question_ids)).all()
    if not qs:
        raise HTTPException(400, "没有选中任何题目")

    # 转 PDF 模板数据
    template_name = payload.template
    items = []
    subject = qs[0].subject or "综合"
    for q in qs:
        item = {
            "text": q.ocr_text or "[图片题]",
            "answer": q.correct_answer or "",
            "steps": q.solution_steps or "",
            "knowledge_point": q.knowledge_point or "",
        }
        items.append(item)

    try:
        pdf_bytes = generate_pdf(
            questions=items,
            child_name=child.name,
            subject=subject,
            template_name=template_name,
        )
        filename = f"similar_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.pdf"
        url = save_pdf(pdf_bytes, filename)
        return schemas.ExportResponse(pdf_url=url, file_size=len(pdf_bytes))
    except Exception as e:
        logger.exception("PDF 生成失败")
        raise HTTPException(500, f"PDF 生成失败: {e}")


# ============ Reports ============

@router.post("/reports/generate")
async def trigger_generate_report(
    child_id: int,
    report_type: str = "weekly",
    db: Session = Depends(get_db),
):
    try:
        report = await generate_weekly_report(db, child_id)
        return {"report_id": report.id, "ok": True}
    except Exception as e:
        logger.exception("生成报告失败")
        raise HTTPException(500, f"生成报告失败: {e}")


@router.get("/reports", response_model=List[schemas.ReportOut])
def list_reports(child_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(models.Report)
    if child_id:
        q = q.filter(models.Report.child_id == child_id)
    return q.order_by(desc(models.Report.created_at)).limit(50).all()


@router.get("/reports/{report_id}", response_model=schemas.ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)):
    r = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not r:
        raise HTTPException(404, "报告不存在")
    return r


# ============ Settings ============

@router.get("/settings/ai", response_model=schemas.AISettings)
def get_ai_settings(db: Session = Depends(get_db)):
    db_settings = {
        s.key: s.value for s in db.query(models.Setting).all()
    }
    # 不返回完整 API Key（安全），前端展示"已配置"标识
    def mask(v: str) -> str:
        if not v:
            return ""
        if len(v) <= 8:
            return "*" * len(v)
        return v[:4] + "*" * (len(v) - 8) + v[-4:]
    return schemas.AISettings(
        text_api_key=mask(db_settings.get("text_api_key", "")),
        text_base_url=db_settings.get("text_base_url", settings.MINIMAX_BASE_URL),
        text_model=db_settings.get("text_model", settings.MINIMAX_MODEL),
        ocr_api_key=mask(db_settings.get("ocr_api_key", "")),
        ocr_base_url=db_settings.get("ocr_base_url", settings.OCR_BASE_URL),
        ocr_model=db_settings.get("ocr_model", settings.OCR_MODEL),
        pushplus_token=db_settings.get("pushplus_token", ""),
        smtp_host=db_settings.get("smtp_host", ""),
        smtp_user=db_settings.get("smtp_user", ""),
        smtp_pass="",
        notify_email=db_settings.get("notify_email", ""),
    )


@router.put("/settings/ai")
def update_ai_settings(payload: schemas.AISettings, db: Session = Depends(get_db)):
    items = {
        "text_api_key": payload.text_api_key,
        "text_base_url": payload.text_base_url,
        "text_model": payload.text_model,
        "ocr_api_key": payload.ocr_api_key,
        "ocr_base_url": payload.ocr_base_url,
        "ocr_model": payload.ocr_model,
        "pushplus_token": payload.pushplus_token,
        "smtp_host": payload.smtp_host,
        "smtp_user": payload.smtp_user,
        "notify_email": payload.notify_email,
    }
    if payload.smtp_pass:
        items["smtp_pass"] = payload.smtp_pass
    for k, v in items.items():
        if not v:
            continue
        existing = db.query(models.Setting).filter(models.Setting.key == k).first()
        if existing:
            existing.value = v
            existing.updated_at = datetime.utcnow()
        else:
            db.add(models.Setting(key=k, value=v))
    db.commit()
    return {"ok": True}


@router.get("/settings/ai/status")
def ai_status():
    """探测 AI 是否就绪"""
    text_cfg = get_text_ai_config()
    ocr_cfg = get_ocr_ai_config()
    return {
        "text_ai": {"configured": bool(text_cfg["api_key"]), "model": text_cfg["model"]},
        "ocr_ai": {"configured": bool(ocr_cfg["api_key"]), "model": ocr_cfg["model"]},
    }


# ============ Stats ============

@router.get("/stats/summary")
def stats_summary(child_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(models.Question)
    if child_id:
        q = q.filter(models.Question.child_id == child_id)
    all_qs = q.all()
    total = len(all_qs)
    correct = sum(1 for q in all_qs if q.is_correct)
    return {
        "total": total,
        "correct": correct,
        "wrong": total - correct,
        "accuracy": (correct / total) if total > 0 else 0.0,
        "mastered": sum(1 for q in all_qs if q.review_status == "mastered"),
        "stubborn": sum(1 for q in all_qs if q.is_stubborn),
    }