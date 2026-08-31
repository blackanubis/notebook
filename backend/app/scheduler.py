"""
定时任务：每周日晚 20:00 生成学情报告并推送。
"""
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app.models import Child, Setting
from app.report_service import generate_weekly_report

logger = logging.getLogger(__name__)


async def _send_push(title: str, content: str, token: str) -> bool:
    """PushPlus 微信推送"""
    if not token:
        return False
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://www.pushplus.plus/send",
                json={"token": token, "title": title, "content": content, "template": "markdown"},
            )
            return r.status_code == 200
    except Exception as e:
        logger.warning(f"推送失败: {e}")
        return False


def _format_report_for_push(report, child_name: str) -> str:
    """把报告格式化为推送文本"""
    import json
    suggestions = json.loads(report.suggestions or "[]")
    text = f"""# {child_name} 本周学情报告

**概览**：答题 {report.total_questions} 道，正确率 {report.accuracy_rate*100:.1f}%

**总结**：{report.summary}

**建议**：
"""
    for i, s in enumerate(suggestions, 1):
        text += f"{i}. {s}\n"
    text += f"\n---\n查看完整报告：http://您的服务地址/reports/{report.id}"
    return text


async def generate_all_weekly_reports():
    """为所有孩子生成周报并推送"""
    db = SessionLocal()
    try:
        children = db.query(Child).all()
        pushplus = _get_db_setting(db, "pushplus_token", "")

        for child in children:
            try:
                report = await generate_weekly_report(db, child.id)
                if pushplus:
                    await _send_push(
                        f"{child.name} 的本周学情报告",
                        _format_report_for_push(report, child.name),
                        pushplus,
                    )
                    logger.info(f"已推送周报到微信: child={child.id}")
            except Exception as e:
                logger.error(f"生成周报失败 child={child.id}: {e}")

    finally:
        db.close()


def _get_db_setting(db, key: str, default: str = "") -> str:
    s = db.query(Setting).filter(Setting.key == key).first()
    return s.value if s and s.value else default


scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


def start_scheduler():
    """启动定时任务"""
    # 每周日晚 20:00 生成周报
    scheduler.add_job(
        generate_all_weekly_reports,
        CronTrigger(day_of_week="sun", hour=20, minute=0),
        id="weekly_report",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[scheduler] 定时任务已启动：每周日晚 20:00 生成学情报告")