# 飞牛 NAS（FNOS）部署指南

> 飞牛 NAS（FNOS）底层为 Linux + Docker，支持标准 docker-compose 部署。本指南针对 FNOS 做了特定优化。

## 一、FNOS 环境前提

| 项目 | 飞牛默认 | 说明 |
|------|---------|------|
| 存储卷路径 | `/vol1/`（或 `/vol2/` 等） | 数据盘挂载点 |
| SSH | 默认开启 | 用 admin 或普通用户登录 |
| Docker | 系统自带 | 可直接用 `docker` 命令 |
| Web 端口 | 8000/8080 等可能被占 | 错题本用 13001 避开 |

> 💡 **不熟悉 Linux 命令？** 也能用 FNOS 自带的 Container Manager 图形化部署，但推荐 SSH 方式（更稳）。

---

## 二、SSH 部署（推荐 · 5 分钟）

### 步骤 1：开启 SSH（如未开）

FNOS Web → 「系统设置」→「SSH」→ 启用

### 步骤 2：本地终端上传文件

在你的电脑（不是 NAS）上：

```bash
# 1. 把压缩包传到飞牛
scp cuoti-notebook-deploy.zip 用户名@飞牛IP:/vol1/docker/

# 2. SSH 登录飞牛
ssh 用户名@飞牛IP
```

### 步骤 3：解压并初始化

```bash
# 1. 创建部署目录
mkdir -p /vol1/docker/cuoti
cd /vol1/docker/cuoti

# 2. 解压
unzip ~/cuoti-notebook-deploy.zip   # 如果传到 ~/ 了
# 或者：unzip /vol1/docker/cuoti-notebook-deploy.zip

# 3. 进入项目目录
cd cuoti-notebook

# 4. （可选）创建 .env 填入 API Key
cp .env.example .env
vi .env   # 按 i 编辑，把 sk-你的Key 换成真实 Key；按 Esc + :wq 保存
```

### 步骤 4：检查/修改数据卷路径

```bash
# 确认你的存储卷路径
df -h
# 一般显示 /dev/mapper/... 挂载到 /vol1

# 如你的存储卷不是 /vol1（如 /vol2），修改 docker-compose.yml
sed -i 's|/vol1/docker/cuoti/data|/vol2/docker/cuoti/data|g' docker-compose.yml
```

### 步骤 5：一键启动

```bash
cd /vol1/docker/cuoti/cuoti-notebook
docker compose up -d

# 5 秒后查看日志
docker compose logs -f
# 看到 "Application startup complete" 即成功
# 按 Ctrl+C 退出（容器仍在后台）
```

### 步骤 6：访问

```
http://飞牛IP:13001
```

---

## 三、FNOS Container Manager 图形化部署

不熟命令的可走图形化路线，但 compose 功能较弱：

### 步骤 1：上传项目

在 FNOS 文件管理上传解压后的 `cuoti-notebook` 整个文件夹到 `/vol1/docker/`

### 步骤 2：Container Manager 部署

1. FNOS Web → 「Container Manager」/ 「容器管理」
2. 选择「Compose」→「上传 compose 文件」
3. 上传 `docker-compose.yml`
4. 修改 volumes 路径（如果界面允许）
5. 点击「部署」

> ⚠️ FNOS 自带 Container Manager 对 compose 支持不完善，**推荐用 SSH**。

---

## 五、关键配置说明

### 1. 数据卷路径（最容易出问题）

| 场景 | volumes 写法 | 是否安全 |
|------|------------|---------|
| 本地开发 | `./data:/data` | OK |
| 飞牛 NAS | `/vol1/docker/cuoti/data:/data` | ✅ 推荐 |
| 飞牛多盘 | `/vol2/docker/cuoti/data:/data` | ✅ 推荐 |
| 系统盘 | `/root/cuoti/data:/data` | ⚠️ 不推荐（重装丢数据） |

**飞牛默认 `vol1` 还是 `vol2`？**

SSH 登录后执行：
```bash
df -h | grep vol
# 输出类似：/dev/sda1  500G  120G  380G  24% /vol1
# 那就是 /vol1
```

### 2. 端口冲突

如 13001 被占用，修改 `docker-compose.yml`：

```yaml
ports:
  - "8888:80"   # 改这里的前一个数字
```

然后 `http://飞牛IP:8888` 访问。

### 3. 资源限制（重要！NAS 内存有限）

我已在 compose 里设置：
- 内存上限：2GB
- 内存预留：512MB

如 FNOS 总内存较小（如 4GB），改成：

```yaml
deploy:
  resources:
    limits:
      memory: 1G
    reservations:
      memory: 256M
```

### 4. API Key 配置方式（3 选 1）

| 方式 | 操作 | 优点 |
|------|------|------|
| **环境变量** | 创建 `.env` 文件填 Key | 容器启动即生效 |
| **网页设置** | 启动后访问「设置」页填 | 灵活，运行时改 |
| **混用** | .env 给 OCR，网页给文本 AI | 灵活组合 |

---

## 六、飞牛特定问题排查

### Q1：容器启动后立刻退出

```bash
docker logs cuoti-notebook
```

常见原因：
- `volumes` 路径写错（如 /vol1 不存在）
- 端口被占（其他容器用了 13001）
- 权限不足（FNOS 用户对 /vol1/docker 无写权限）

### Q2：FNOS 防火墙挡住了 13001

```bash
# FNOS 默认有防火墙，需要放行端口
# 方式 1：Web 端「安全」→「防火墙规则」→ 添加 13001 TCP
# 方式 2（命令行，需 root）：
iptables -I INPUT -p tcp --dport 13001 -j ACCEPT
```

### Q3：磁盘空间满

```bash
df -h /vol1
# 满了的话清理上传目录
du -sh /vol1/docker/cuoti/data/uploads/
# 删除过期 PDF
find /vol1/docker/cuoti/data/uploads/exports/ -mtime +30 -delete
```

### Q4：飞牛休眠后容器没起来

```bash
# 飞牛有"深度休眠"模式，可能影响 Docker
# 在 FNOS Web →「系统设置」→「电源」关闭深度休眠
# 或确保重启策略是 always
docker update --restart unless-stopped cuoti-notebook
```

---

## 七、自动化运维（可选）

### 自动备份

```bash
# 编辑 crontab
crontab -e
# 添加（每周日凌晨3点备份）：
0 3 * * 0 tar czf /vol1/docker/cuoti/backups/data-$(date +\%Y\%m\%d).tar.gz /vol1/docker/cuoti/data

# 创建备份目录
mkdir -p /vol1/docker/cuoti/backups
```

### 自动重启（FNOS 重启后）

compose 已设置 `restart: unless-stopped`，FNOS 重启后容器会自动起来。

### 看实时资源占用

```bash
docker stats cuoti-notebook
```

---

## 八、完整部署检查清单

部署完成后逐项验证：

- [ ] `docker ps` 看到 cuoti-notebook 在运行
- [ ] 浏览器打开 `http://飞牛IP:13001` 看到首页
- [ ] 进入「设置」→ 保存 AI 配置成功
- [ ] 「孩子管理」→ 添加一个孩子
- [ ] 「拍照录入」→ 上传一张图片测试
- [ ] 错题详情页 → AI 错因分析能跑通
- [ ] 「相似题」→ 生成 5 道题
- [ ] 「导出」→ 下载 PDF 成功
- [ ] 「报告」→ 生成周报成功

如有任一步骤报错，把 `docker logs cuoti-notebook` 的最后 30 行贴给我。