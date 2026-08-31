"""
OCR 服务：调用 minimax 视觉模型识别题目图片。
支持单题与整页试卷两种场景。
"""
import json
import base64
import logging
from typing import List, Dict, Any
import httpx

from app.ai_service import get_ocr_ai_config, chat_completion

logger = logging.getLogger(__name__)


OCR_PROMPT = """你是中小学题目识别专家。请仔细识别这张图片里的所有题目，并输出严格的 JSON（不要任何多余文字）：

{
  "subject": "推测的学科（数学/语文/英语/物理/化学/生物/历史/地理/政治）",
  "questions": [
    {
      "index": 1,
      "text": "题目的完整文本（含题干、选项；数学公式用 LaTeX，如 $\\\\frac{{1}}{{2}}$）",
      "has_formula": true|false
    }
  ]
}

注意：
- 保留题号与选项
- 数学公式必须用 LaTeX
- 识别不到的字符用 □ 占位
- 如果是空题目或图片模糊，跳过该题
"""


async def recognize_questions_from_image(image_base64: str, image_mime: str = "image/jpeg") -> Dict[str, Any]:
    """
    调用视觉模型识别图片中的题目。
    image_base64: 不含 data:image/... 前缀的纯 base64
    """
    cfg = get_ocr_ai_config()
    if not cfg["api_key"]:
        raise RuntimeError("OCR 未配置：请到「设置」页填入 OCR AI 的 API Key，或在环境变量中设置 OCR_API_KEY")

    url = f"{cfg['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }

    # 多模态消息格式（OpenAI 兼容）
    payload = {
        "model": cfg["model"],
        "messages": [
            {
                "role": "system",
                "content": "你是中小学题目 OCR 识别专家。",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": OCR_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{image_mime};base64,{image_base64}"
                        },
                    },
                ],
            },
        ],
        "temperature": 0.1,
        "max_tokens": 3000,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code != 200:
            raise RuntimeError(f"OCR 调用失败 [{r.status_code}]: {r.text[:300]}")
        data = r.json()
        content = data["choices"][0]["message"]["content"]

    # 解析 JSON
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```", 2)[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip().rstrip("`").strip()
    try:
        result = json.loads(content)
        return {
            "subject": result.get("subject", ""),
            "questions": result.get("questions", []),
            "raw_text": content,
        }
    except json.JSONDecodeError:
        logger.error(f"OCR 返回非 JSON: {content[:500]}")
        # 兜底：整段作为一道题
        return {
            "subject": "",
            "questions": [
                {"index": 1, "text": content[:1500], "has_formula": False}
            ],
            "raw_text": content,
        }


async def encode_image_to_base64(image_path: str) -> tuple[str, str]:
    """读取图片文件，返回 (base64_str, mime)"""
    import mimetypes
    import os
    from pathlib import Path

    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"图片不存在: {image_path}")

    mime, _ = mimetypes.guess_type(str(path))
    if not mime:
        # 默认 jpeg
        mime = "image/jpeg"

    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("utf-8"), mime