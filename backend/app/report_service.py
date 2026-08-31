"""
报告生成服务：基于错题数据生成周报/月报。
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from app import models
from app.ai_service import generate_report

logger = logging.getLogger(__name__)


def get_kp_breakdown(db: Session, child_id: int, start: datetime, end: datetime) -> List[Dict]:
    """知识点 × 错题率"""
    questions = db.query(models.Question).filter(
        models.Question.child_id == child_id,
        models.Question.created_at >= start,
        models.Question.created_at < end,
        models.Question.knowledge_point != "",
    ).all()

    buckets: Dict[str, Dict[str, int]] = {}
    for q in questions:
        kp = q.knowledge_point
        if kp not in buckets:
            buckets[kp] = {"total": 0, "wrong": 0}
        buckets[kp]["total"] += 1
        if not q.is_correct:
            buckets[kp]["wrong"] += 1

    breakdown = []
    for kp, b in buckets.items():
        if b["total"] >= 2:  # 样本太少的忽略
            rate = b["wrong"] / b["total"]
            breakdown.append({
                "kp": kp,
                "total": b["total"],
                "wrong": b["wrong"],
                "rate": round(rate, 2),
            })
    breakdown.sort(key=lambda x: x["rate"], reverse=True)
    return breakdown


def get_improvement_kps(db: Session, child_id: int, current_start: datetime, previous_start: datetime, current_end: datetime) -> List[Dict]:
    """对比上一周期，找出进步知识点"""
    curr = {b["kp"]: b["rate"] for b in get_kp_breakdown(db, child_id, current_start, current_end)}
    prev = {b["kp"]: b["rate"] for b in get_kp_breakdown(db, child_id, previous_start, current_start)}
    improvements = []
    for kp, now_rate in curr.items():
        if kp in prev and prev[kp] > now_rate:
            improvements.append({
                "kp": kp,
                "from": prev[kp],
                "to": now_rate,
                "delta": round(prev[kp] - now_rate, 2),
            })
    improvements.sort(key=lambda x: x["delta"], reverse=True)
    return improvements


async def generate_weekly_report(db: Session, child_id: int) -> models.Report:
    """生成周报"""
    child = db.query(models.Child).filter(models.Child.id == child_id).first()
    if not child:
        raise ValueError(f"Child {child_id} not found")

    now = datetime.utcnow()
    end = now
    start = now - timedelta(days=7)
    prev_start = start - timedelta(days=7)

    # 数据统计
    qs = db.query(models.Question).filter(
        models.Question.child_id == child_id,
        models.Question.created_at >= start,
        models.Question.created_at < end,
    ).all()

    total = len(qs)
    correct = sum(1 for q in qs if q.is_correct)
    wrong = total - correct
    accuracy = (correct / total) if total > 0 else 0.0
    mastered = sum(1 for q in qs if q.review_status == "mastered")
    stubborn = sum(1 for q in qs if q.is_stubborn)

    breakdown = get_kp_breakdown(db, child_id, start, end)
    improvements = get_improvement_kps(db, child_id, start, prev_start, end)

    kp_text = "\n".join([
        f"- {b['kp']}：{b['wrong']}/{b['total']}（错题率 {b['rate']*100:.0f}%）"
        for b in breakdown[:10]
    ]) or "（暂无足够数据）"

    imp_text = "\n".join([
        f"- {i['kp']}：从 {i['from']*100:.0f}% 降到 {i['to']*100:.0f}%"
        for i in improvements[:5]
    ]) or "（本周暂无明显进步，建议持续记录）"

    ai_data = await generate_report(
        child_name=child.name,
        grade=child.grade or "",
        period_start=start.strftime("%Y-%m-%d"),
        period_end=end.strftime("%Y-%m-%d"),
        total=total,
        correct=correct,
        wrong=wrong,
        accuracy=accuracy,
        mastered=mastered,
        stubborn=stubborn,
        kp_breakdown=kp_text,
        improvement_kps=imp_text,
    )

    # 落库
    report = models.Report(
        child_id=child_id,
        report_type="weekly",
        period_start=start,
        period_end=end,
        total_questions=total,
        total_correct=correct,
        total_wrong=wrong,
        accuracy_rate=accuracy,
        mastered_count=mastered,
        stubborn_count=stubborn,
        summary=ai_data.get("summary", ""),
        strengths=json.dumps(ai_data.get("strengths", []), ensure_ascii=False),
        weaknesses=json.dumps(ai_data.get("weaknesses", []), ensure_ascii=False),
        improvements=json.dumps(ai_data.get("improvements", []), ensure_ascii=False),
        suggestions=json.dumps(ai_data.get("suggestions", []), ensure_ascii=False),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    logger.info(f"生成周报：child={child_id}, report_id={report.id}")
    return report