"""
AI 服务：封装 minimax API 调用（文本与视觉分开配置）。
所有 AI 能力都通过本模块调用，便于后续替换模型。
"""
import json
import logging
from typing import Optional, List, Dict, Any
import httpx

from app.config import settings
from app.database import SessionLocal
from app.models import Setting

logger = logging.getLogger(__name__)


# ============ 设置读取（数据库优先，环境变量兜底） ============

def _get_db_setting(key: str, default: str = "") -> str:
    try:
        db = SessionLocal()
        s = db.query(Setting).filter(Setting.key == key).first()
        db.close()
        return s.value if s and s.value else default
    except Exception as e:
        logger.warning(f"读取设置失败 {key}: {e}")
        return default


def get_text_ai_config() -> Dict[str, str]:
    """通用 AI（文本）配置"""
    return {
        "api_key": _get_db_setting("text_api_key", settings.MINIMAX_API_KEY),
        "base_url": _get_db_setting("text_base_url", settings.MINIMAX_BASE_URL).rstrip("/"),
        "model": _get_db_setting("text_model", settings.MINIMAX_MODEL),
    }


def get_ocr_ai_config() -> Dict[str, str]:
    """OCR / 视觉 AI 配置"""
    return {
        "api_key": _get_db_setting("ocr_api_key", settings.OCR_API_KEY),
        "base_url": _get_db_setting("ocr_base_url", settings.OCR_BASE_URL).rstrip("/"),
        "model": _get_db_setting("ocr_model", settings.OCR_MODEL),
    }


# ============ 通用 HTTP 调用（OpenAI 兼容协议） ============

async def chat_completion(
    messages: List[Dict[str, Any]],
    cfg: Optional[Dict[str, str]] = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    timeout: float = 60.0,
) -> str:
    """通用对话完成。messages 兼容 OpenAI Chat 格式（含 image_url 多模态）。"""
    cfg = cfg or get_text_ai_config()
    if not cfg["api_key"]:
        raise RuntimeError(
            "AI 未配置：请到「设置」页填入 API Key，或在 docker-compose.yml 设置环境变量 MINIMAX_API_KEY"
        )

    url = f"{cfg['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code != 200:
            raise RuntimeError(f"AI 调用失败 [{r.status_code}]: {r.text[:300]}")
        data = r.json()
        return data["choices"][0]["message"]["content"]


# ============ 业务：错因诊断 + 答案步骤 ============

ERROR_ANALYZE_PROMPT = """你是一位资深的中小学教师。请分析学生这道错题，输出严格的 JSON 格式（不要任何多余文字）：

{
  "error_type": "concept|calculation|misread|method|careless 之一",
  "error_type_label": "概念不清|计算错误|审题失误|方法不当|粗心大意 之一",
  "error_reason": "一段话诊断（80~150字），点出具体错在哪里",
  "correct_answer": "标准答案",
  "solution_steps": "Markdown 格式的分步骤解答，每步一行，关键公式可用 LaTeX (如 $x^2+1$)",
  "knowledge_point": "本题考察的知识点（如'分数加减法'/'长方形周长'）"
}

题目：
{question_text}

学生作答：
{student_answer}

学科：{subject}
"""


async def analyze_error(
    question_text: str,
    student_answer: str,
    subject: str = "数学",
    knowledge_point: str = "",
) -> Dict[str, Any]:
    prompt = ERROR_ANALYZE_PROMPT.format(
        question_text=question_text,
        student_answer=student_answer or "（未作答）",
        subject=subject,
    )
    cfg = get_text_ai_config()
    content = await chat_completion(
        messages=[
            {"role": "system", "content": "你是一位资深的中小学老师，只输出 JSON。"},
            {"role": "user", "content": prompt},
        ],
        cfg=cfg,
        temperature=0.2,
    )
    # 解析 JSON（去除 markdown 包裹）
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```", 2)[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip().rstrip("`").strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.error(f"错因分析返回非 JSON: {content[:300]}")
        # 兜底：返回基础结构
        return {
            "error_type": "concept",
            "error_type_label": "概念不清",
            "error_reason": "AI 分析结果格式异常，请人工核对。",
            "correct_answer": "",
            "solution_steps": "",
            "knowledge_point": knowledge_point or "",
        }


# ============ 业务：相似题出题 ============

SIMILAR_QUESTIONS_PROMPT = """你是一位资深的中小学教师。基于下面的题目，生成 {count} 道相似变式题，用于学生巩固练习。
要求：
- 同考点，换数字、换场景、换问法
- 难度递增（前 70% 同难度，后 30% 略难）
- 客观题为主，避免开放性题目
- 输出严格 JSON 数组，不要任何多余文字

[
  {{"index": 1, "question": "题目内容", "answer": "标准答案", "steps": "简要步骤"}},
  ...
]

原题：
{question_text}

标准答案：
{correct_answer}

学科：{subject}
知识点：{knowledge_point}
"""


async def generate_similar_questions(
    question_text: str,
    correct_answer: str,
    subject: str = "数学",
    knowledge_point: str = "",
    count: int = 5,
) -> List[Dict[str, Any]]:
    prompt = SIMILAR_QUESTIONS_PROMPT.format(
        count=count,
        question_text=question_text,
        correct_answer=correct_answer,
        subject=subject,
        knowledge_point=knowledge_point,
    )
    content = await chat_completion(
        messages=[
            {"role": "system", "content": "你是资深中小学老师，只输出 JSON 数组。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=2500,
    )
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```", 2)[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip().rstrip("`").strip()
    try:
        result = json.loads(content)
        if isinstance(result, list):
            return result[:count]
        if isinstance(result, dict) and "questions" in result:
            return result["questions"][:count]
    except json.JSONDecodeError:
        logger.error(f"相似题生成返回非 JSON: {content[:300]}")

    # 兜底
    return [{
        "index": i + 1,
        "question": f"（AI 生成失败，请手动补充）第 {i+1} 道相似题",
        "answer": "",
        "steps": "",
    } for i in range(count)]


# ============ 业务：作答评判 ============

JUDGE_PROMPT = """你是资深中小学老师。学生正在做这道题，请评判他的作答，输出严格 JSON：

{{
  "score": 0~100 的整数,
  "is_correct": true|false,
  "error_point": "具体错在哪一步（答对了就写'全部正确'）",
  "ai_judgment": "Markdown 格式的详细评判，包括得分点、扣分点、改进建议（150~250字）"
}}

题目：
{question}

标准答案：
{answer}

学生作答：
{response}
"""


async def judge_answer(
    question: str,
    answer: str,
    response: str,
    subject: str = "数学",
) -> Dict[str, Any]:
    prompt = JUDGE_PROMPT.format(question=question, answer=answer, response=response or "（未作答）")
    content = await chat_completion(
        messages=[
            {"role": "system", "content": "你是阅卷老师，只输出 JSON。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=1500,
    )
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```", 2)[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip().rstrip("`").strip()
    try:
        result = json.loads(content)
        # 字段兜底
        result.setdefault("score", 0)
        result.setdefault("is_correct", False)
        result.setdefault("error_point", "")
        result.setdefault("ai_judgment", "")
        # 强制类型
        result["score"] = float(result.get("score", 0))
        result["is_correct"] = bool(result.get("is_correct", False))
        return result
    except json.JSONDecodeError:
        logger.error(f"评判返回非 JSON: {content[:300]}")
        return {
            "score": 0,
            "is_correct": False,
            "error_point": "AI 评判异常",
            "ai_judgment": "AI 评判返回格式异常，请人工核对。",
        }


# ============ 业务：学情报告 ============

REPORT_PROMPT = """你是资深班主任。基于本周学生的学习数据，生成给家长看的学情报告。
输出严格 JSON（不要任何多余文字）：

{{
  "summary": "本周学习概览（100~150字）",
  "strengths": [{{"kp": "知识点", "rate": 0.95, "note": "一句话说明"}}],
  "weaknesses": [{{"kp": "知识点", "rate": 0.25, "note": "一句话说明"}}],
  "improvements": [{{"kp": "知识点", "from": 0.3, "to": 0.7, "note": "进步说明"}}],
  "suggestions": ["给家长的3条具体建议，每条30~50字"]
}}

孩子：{child_name} · {grade}
周期：{period_start} 至 {period_end}
总答题：{total}（错 {wrong} / 对 {correct}）
整体正确率：{accuracy}%
已掌握：{mastered} 道，顽固错题：{stubborn} 道

错题按知识点分布：
{kp_breakdown}

进步知识点：
{improvement_kps}
"""


async def generate_report(
    child_name: str,
    grade: str,
    period_start: str,
    period_end: str,
    total: int,
    correct: int,
    wrong: int,
    accuracy: float,
    mastered: int,
    stubborn: int,
    kp_breakdown: str,
    improvement_kps: str,
) -> Dict[str, Any]:
    prompt = REPORT_PROMPT.format(
        child_name=child_name,
        grade=grade or "未知年级",
        period_start=period_start,
        period_end=period_end,
        total=total,
        correct=correct,
        wrong=wrong,
        accuracy=f"{accuracy*100:.1f}",
        mastered=mastered,
        stubborn=stubborn,
        kp_breakdown=kp_breakdown or "（暂无数据）",
        improvement_kps=improvement_kps or "（暂无）",
    )
    content = await chat_completion(
        messages=[
            {"role": "system", "content": "你是班主任，只输出 JSON。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,
        max_tokens=2000,
    )
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```", 2)[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip().rstrip("`").strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.error(f"报告生成返回非 JSON: {content[:300]}")
        return {
            "summary": "本周数据已采集，详细分析生成中。",
            "strengths": [],
            "weaknesses": [],
            "improvements": [],
            "suggestions": ["请关注孩子的错题复习节奏", "建议周末集中练习一次", "鼓励孩子坚持每天 10 分钟"],
        }