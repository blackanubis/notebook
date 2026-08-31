"""
PDF 生成服务：基于 WeasyPrint + Jinja2 模板。
支持 3 种模板：仅题目 / 题目+答案 / 题目+答题卡。
"""
import os
import logging
import io
import qrcode
from datetime import datetime
from pathlib import Path
from typing import List
from jinja2 import Template
from weasyprint import HTML

from app.config import settings

logger = logging.getLogger(__name__)


PDF_TEMPLATE_QUESTIONS_ONLY = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @page { size: A4; margin: 18mm 15mm; }
  body { font-family: "Noto Sans CJK SC", "WenQuanYi Micro Hei", sans-serif; font-size: 11pt; color: #222; line-height: 1.6; }
  .header { text-align: center; border-bottom: 1px solid #185FA5; padding-bottom: 8px; margin-bottom: 16px; }
  .header h1 { margin: 0 0 4px 0; font-size: 16pt; color: #185FA5; }
  .header .meta { font-size: 9pt; color: #888; }
  .question { margin-bottom: 18px; page-break-inside: avoid; }
  .q-title { font-weight: 500; color: #534AB7; margin-bottom: 4px; }
  .q-body { margin-bottom: 6px; }
  .answer-area { border: 0.5px dashed #B4B2A9; height: 60mm; border-radius: 2px; }
  .footer { position: fixed; bottom: 8mm; left: 15mm; right: 15mm; text-align: center; font-size: 8pt; color: #999; border-top: 0.5px solid #eee; padding-top: 4px; }
  .qr { display: inline-block; vertical-align: middle; }
</style></head>
<body>
<div class="header">
  <h1>{{ child_name }} · {{ subject }} 练习</h1>
  <div class="meta">{{ date }} · 共 {{ count }} 题 · 答答案二维码见底部</div>
</div>

{% for q in questions %}
<div class="question">
  <div class="q-title">第 {{ loop.index }} 题</div>
  <div class="q-body">{{ q.text|safe }}</div>
  <div class="answer-area"></div>
</div>
{% endfor %}

<div class="footer">
  第 <span class="page"></span> 页 · 扫描下方二维码查看答案
  <span class="qr"><img src="{{ qr_data_uri }}" width="40" height="40"></span>
</div>
</body></html>"""


PDF_TEMPLATE_WITH_ANSWERS = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @page { size: A4; margin: 18mm 15mm; }
  body { font-family: "Noto Sans CJK SC", "WenQuanYi Micro Hei", sans-serif; font-size: 10pt; color: #222; line-height: 1.5; }
  .header { text-align: center; border-bottom: 1px solid #185FA5; padding-bottom: 6px; margin-bottom: 14px; }
  .header h1 { margin: 0 0 3px 0; font-size: 14pt; color: #185FA5; }
  .header .meta { font-size: 8pt; color: #888; }
  .question { margin-bottom: 14px; padding: 8px; border: 0.5px solid #eee; border-radius: 4px; page-break-inside: avoid; }
  .q-title { font-weight: 500; color: #534AB7; margin-bottom: 3px; font-size: 11pt; }
  .q-body { margin-bottom: 6px; }
  .answer { background: #EAF3DE; padding: 6px 8px; border-radius: 3px; margin-top: 4px; }
  .answer-label { color: #3B6D11; font-weight: 500; }
  .steps { background: #F1EFE8; padding: 6px 8px; border-radius: 3px; margin-top: 4px; font-size: 9pt; }
  .steps-label { color: #633806; font-weight: 500; }
  .footer { text-align: center; font-size: 8pt; color: #999; margin-top: 16px; }
</style></head>
<body>
<div class="header">
  <h1>{{ child_name }} · {{ subject }} 练习 · 家长版（含答案）</h1>
  <div class="meta">{{ date }} · 共 {{ count }} 题</div>
</div>

{% for q in questions %}
<div class="question">
  <div class="q-title">第 {{ loop.index }} 题 · {{ q.knowledge_point or '' }}</div>
  <div class="q-body">{{ q.text|safe }}</div>
  {% if q.answer %}
  <div class="answer">
    <span class="answer-label">答案：</span>{{ q.answer|safe }}
  </div>
  {% endif %}
  {% if q.steps %}
  <div class="steps">
    <span class="steps-label">步骤：</span>{{ q.steps|safe }}
  </div>
  {% endif %}
</div>
{% endfor %}

<div class="footer">家长辅导版 · 请勿交给孩子独立使用</div>
</body></html>"""


PDF_TEMPLATE_WITH_ANSWER_SHEET = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @page { size: A4; margin: 18mm 15mm; }
  body { font-family: "Noto Sans CJK SC", "WenQuanYi Micro Hei", sans-serif; font-size: 11pt; color: #222; line-height: 1.6; }
  .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #185FA5; padding-bottom: 8px; margin-bottom: 14px; }
  .header h1 { margin: 0; font-size: 15pt; color: #185FA5; }
  .name-line { font-size: 10pt; color: #444; }
  .question { margin-bottom: 16px; page-break-inside: avoid; }
  .q-title { font-weight: 500; color: #534AB7; margin-bottom: 4px; }
  .answer-area { border: 0.5px dashed #B4B2A9; height: 35mm; margin-top: 6px; border-radius: 2px; }
  .footer { text-align: center; font-size: 8pt; color: #999; margin-top: 14px; }
</style></head>
<body>
<div class="header">
  <h1>{{ child_name }} · {{ subject }} 模拟练习</h1>
  <div class="name-line">姓名：__________ 班级：__________ 日期：__________</div>
</div>

{% for q in questions %}
<div class="question">
  <div class="q-title">第 {{ loop.index }} 题（知识点：{{ q.knowledge_point or '综合' }}）</div>
  <div class="q-body">{{ q.text|safe }}</div>
  <div class="answer-area"></div>
</div>
{% endfor %}

<div class="footer">本卷共 {{ count }} 题 · {{ date }} · 答题完成后请家长批改</div>
</body></html>"""


TEMPLATES = {
    "questions_only": PDF_TEMPLATE_QUESTIONS_ONLY,
    "with_answers": PDF_TEMPLATE_WITH_ANSWERS,
    "with_answer_sheet": PDF_TEMPLATE_WITH_ANSWER_SHEET,
}


def _make_qr_data_uri(payload: str) -> str:
    """生成 base64 内嵌二维码"""
    qr = qrcode.QRCode(version=1, box_size=10, border=1)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def _escape_latex_for_html(text: str) -> str:
    """把 LaTeX 简单包裹，让浏览器/PDF 不报错（不渲染数学符号）"""
    # WeasyPrint 不支持 MathJax，所以 LaTeX 直接以文本呈现
    # 用户可在 V2 阶段加 MathJax 渲染
    return text or ""


import base64  # noqa: E402  # 用于 _make_qr_data_uri


def generate_pdf(
    questions: List[dict],
    child_name: str,
    subject: str,
    template_name: str = "questions_only",
    extra_meta: dict = None,
) -> bytes:
    """
    生成 PDF。
    questions: [{"text":..., "answer":..., "steps":..., "knowledge_point":...}, ...]
    """
    template_str = TEMPLATES.get(template_name, PDF_TEMPLATE_QUESTIONS_ONLY)
    tmpl = Template(template_str)
    html_str = tmpl.render(
        child_name=child_name,
        subject=subject or "综合",
        date=datetime.now().strftime("%Y-%m-%d"),
        count=len(questions),
        questions=questions,
        qr_data_uri=_make_qr_data_uri(f"cuoti://answers/{datetime.now().strftime('%Y%m%d')}"),
        **(extra_meta or {}),
    )
    pdf_bytes = HTML(string=html_str).write_pdf()
    return pdf_bytes


def save_pdf(pdf_bytes: bytes, filename: str) -> str:
    """保存 PDF 到上传目录，返回访问 URL"""
    upload_dir = Path(settings.UPLOAD_DIR) / "exports"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename
    file_path.write_bytes(pdf_bytes)
    return f"/files/exports/{filename}"