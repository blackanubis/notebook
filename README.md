# 家庭错题本 · Home Cuoti Notebook

> 一款为家庭场景打造的轻量级错题本，H5 移动端 + Docker 一键部署，集成 minimax AI 实现智能错因诊断、相似题出题、作答评判与学情报告。

## ✨ 核心功能

- 📷 **拍照录入**：整页试卷自动切题，支持错题 + 正题双标记
- 🤖 **AI 错因诊断**：识别错因类型（概念/计算/审题/方法/粗心） + 文字诊断
- ✅ **标准答案 + 步骤详解**：含公式（LaTeX）渲染
- 🎯 **相似题出题**：基于错题生成 3~5 道变式题
- 📊 **作答评判**：客观题自动判分，主观题给步骤对比
- 📥 **全选导出 / 打印**：3 种 PDF 模板（仅题目 / 含答案 / 含答题卡）
- 📈 **学情报告**：周报自动生成，含优势 / 薄弱 / 进步 / 3 条建议
- 👨‍👩‍👧‍👦 **多孩子支持**：独立档案，错题数据隔离
- 📱 **移动端优先**：H5 响应式设计，手机即开即用

## 🛠 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2.0 |
| 数据库 | SQLite（单文件，零运维）|
| 前端 | Vue 3 + Vite + Vant 4 |
| AI | minimax API（通用文本 + 视觉模型，分别配置）|
| PDF | WeasyPrint + Jinja2 模板 |
| 反代 | Nginx |
| 定时任务 | APScheduler |
| 部署 | Docker + docker-compose |

## 🚀 快速开始

### 前置要求

- Docker 20.10+
- Docker Compose v2+
- 至少 1GB 可用内存

### 一键启动

```bash
# 1. 进入项目目录
cd cuoti-notebook

# 2. （可选）在 .env 或 docker-compose.yml 配置 API Key
# 也可以启动后在「设置」页面配置

# 3. 启动
docker compose up -d

# 4. 查看日志
docker compose logs -f

# 5. 访问
# 浏览器打开：http://localhost:13001
```

### 首次配置

1. 打开 http://localhost:13001
2. 进入「设置」页面
3. 分别填入：
   - **通用 AI**（错因/出题/报告）：API Key、Base URL、模型名
   - **OCR AI**（题目识别）：API Key、Base URL、模型名
4. 进入「孩子管理」，添加第一个孩子档案
5. 开始拍照录入错题

## ⚙️ 环境变量（docker-compose.yml）

```yaml
environment:
  # 通用 AI（可选，也可在「设置」页配置）
  - MINIMAX_API_KEY=sk-xxx
  - MINIMAX_BASE_URL=https://api.minimax.chat/v1
  - MINIMAX_MODEL=MiniMax-Text-01
  
  # OCR / 视觉 AI
  - OCR_API_KEY=sk-xxx
  - OCR_BASE_URL=https://api.minimax.chat/v1
  - OCR_MODEL=MiniMax-VL-01
  
  - TZ=Asia/Shanghai
```

## 📁 目录结构

```
cuoti-notebook/
├── Dockerfile                # 单镜像构建
├── docker-compose.yml        # 一键编排
├── nginx/
│   ├── nginx.conf            # 反代配置
│   └── entrypoint.sh         # 启动脚本
├── backend/                  # FastAPI 后端
│   ├── main.py
│   ├── requirements.txt
│   └── app/
│       ├── config.py         # 配置（环境变量）
│       ├── database.py       # SQLAlchemy + SQLite
│       ├── models.py         # ORM 模型
│       ├── schemas.py        # Pydantic 数据校验
│       ├── ai_service.py     # minimax AI（文本）
│       ├── ocr_service.py    # minimax AI（视觉）
│       ├── pdf_service.py    # WeasyPrint PDF 生成
│       ├── report_service.py # 报告生成
│       ├── scheduler.py      # APScheduler 定时任务
│       └── routes.py         # 所有 API 路由
└── frontend/                 # Vue 3 前端
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.js
        ├── App.vue
        ├── api.js
        ├── styles.css
        └── views/            # 8 个核心页面
            ├── Home.vue
            ├── Camera.vue
            ├── QuestionList.vue
            ├── QuestionDetail.vue
            ├── Practice.vue
            ├── ExportView.vue
            ├── Report.vue
            ├── Settings.vue
            └── Children.vue
```

## 🔧 数据持久化

所有用户数据保存在宿主机 `./data/` 目录：

```
data/
├── db/
│   └── app.db          # SQLite 数据库
├── uploads/
│   ├── questions/      # 错题原图
│   └── exports/        # 导出的 PDF
└── ...
```

**备份只需复制整个 `data/` 目录**。

## 🔌 API 端点（部分）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET/POST/PUT/DELETE | `/api/v1/children` | 孩子管理 |
| GET/POST/PUT/DELETE | `/api/v1/questions` | 题目 CRUD |
| POST | `/api/v1/upload/image` | 上传图片 |
| POST | `/api/v1/ocr/recognize` | OCR 识别 |
| POST | `/api/v1/ai/analyze-error` | 错因分析 |
| POST | `/api/v1/ai/similar-questions` | 相似题出题 |
| POST | `/api/v1/practice/judge` | 作答评判 |
| POST | `/api/v1/export/pdf` | 导出 PDF |
| GET/POST | `/api/v1/reports` | 学情报告 |
| GET/PUT | `/api/v1/settings/ai` | AI 设置 |

完整文档：`http://localhost:13001/docs`（FastAPI 自动生成）

## ⚠️ 关于 minimax 视觉模型做 OCR

- minimax VL 模型支持图像理解与 OCR，中文场景精度约 85~90%
- **手写数学公式识别率较低**，建议在录入页手动核对与编辑
- 后续可在「设置」切换到更专业的 OCR 服务（如 Mathpix）

## 📋 后续迭代清单

- [ ] 数学公式渲染（KaTeX/MathJax）
- [ ] PDF 中嵌入真实二维码（扫码查看在线答案）
- [ ] 智能复习（艾宾浩斯遗忘曲线推送）
- [ ] 错题本归档（已掌握自动隐藏）
- [ ] 学情趋势图（折线、雷达图）
- [ ] 答题横屏白板模式
- [ ] 多孩子数据横向对比
- [ ] HTTPS 支持（Nginx + Let's Encrypt）
- [ ] PWA（添加到主屏幕）

## 🐛 常见问题

**Q: 启动后访问 13001 显示空白？**
A: 检查容器日志：`docker compose logs -f cuoti`，确认前端构建是否成功。

**Q: AI 提示"未配置"？**
A: 进入「设置」页面填入 API Key，或在环境变量中设置 `MINIMAX_API_KEY` 和 `OCR_API_KEY`。

**Q: OCR 识别结果不准确？**
A: minimax VL 模型对手写公式识别较弱，建议在录入页手动编辑；可换用专业 OCR。

**Q: PDF 中文乱码？**
A: 镜像已内置 Noto CJK + 文泉驿字体，确保未自定义 Dockerfile 删除了字体安装步骤。

**Q: 如何升级？**
```bash
docker compose pull   # 拉取新镜像
docker compose up -d  # 重启
```

## 📜 许可证

仅供个人/家庭学习使用。

---

**Enjoy learning, together with your kid!** 🎓