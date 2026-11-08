# 知行书院 · 智慧图书馆全栈

基于 Vue 3 + Vite + JavaScript、Django + Django REST Framework 的大学智慧图书管理系统。JWT 认证、书目管理、借阅、归还罚款、智能预约排队、到馆锁定顺延、图书推荐算法、用户阅读画像和管理员统计均由前后端全栈提供。

默认数据库是 Django SQLite，适合开发和演示；通过 `DATABASE_URL` 可以切换 PostgreSQL。当前目录保留 Vue SPA，后端位于 `backend/`。

---

## 🚀 快速启动指南

> 💡 **重要说明**：本项目为**前后端分离全栈项目**，前端界面依赖后端 REST API（默认 `8000` 端口）提供数据支持。**请不要直接双击打开 `index.html`**（浏览器安全策略会拦截本地 ES Module 导致白屏）。

### 方案一：Windows 一键启动（最推荐 · 双击即开）

项目根目录下已为您内置好一键启动脚本，自动同时唤起后端服务与前端界面，并自动在浏览器中弹出：

- **方式 1**：在文件管理器中，直接**双击运行根目录下的 `启动项目.bat`**。
- **方式 2**：在 PowerShell 终端运行：
  ```powershell
  .\启动项目.ps1
  ```
启动后浏览器将自动打开 `http://localhost:5173`。

---

### 方案二：手动双终端标准启动

如果您希望在终端手动观察前后端输出，请分别开启 **两个独立的终端窗口**：

#### 终端 1：启动后端 Django 服务（必须）

```powershell
# 1. 进入后端目录
cd backend

# 2. 如果是首次运行，初始化环境与数据库：
# 方式 A（标准 Python）：
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo

# 方式 B（如果电脑安装了 uv 工具）：
# uv venv .venv
# uv pip install --python .venv\Scripts\python.exe -r requirements.txt
# uv run --python .venv\Scripts\python.exe python manage.py migrate
# uv run --python .venv\Scripts\python.exe python manage.py seed_demo

# 3. 启动后端服务器（运行在 8000 端口）
.\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```
> 后端服务就绪后，访问 `http://127.0.0.1:8000/api` 即可看到服务就绪状态。

#### 终端 2：启动前端 Vue 3 界面（另开一个终端）

```powershell
# 1. 确保在项目根目录（D:\智慧）
cd D:\智慧

# 2. 安装前端依赖（首次运行）
npm install

# 3. 启动开发服务器并自动弹出浏览器
npm run dev -- --open
```

默认前端开发地址：`http://localhost:5173`。

---

### 方案三：Docker Compose 一键启动

如果您本地安装了 Docker，可直接使用容器化一键部署：

```powershell
docker compose up --build
```
Compose 会同时拉起 Django 后端（包含自动数据迁移与 `seed_demo` 初始化）和 Vue 开发服务器。

---

## 🔑 演示账号密码

执行 `seed_demo` 后系统已预置好具备借阅与预约演示数据的测试账号：

| 身份角色 | 登录邮箱 | 初始密码 | 权限功能说明 |
| :--- | :--- | :--- | :--- |
| **学生 (读者)** | `student@zhixing.local` | `Student123!` | 书目检索、智能推荐、借阅还书、预约排队、到馆核销、个人 Reading DNA 画像 |
| **教职工** | `staff@zhixing.local` | `Staff123!` | 享受教职工借阅权限、预约排队与个人中心 |
| **管理员** | `admin@zhixing.local` | `Admin123!` | 书目增删改查录入、全馆流通数据大屏、预约排队监控与借阅 TOP10 统计 |

*(以上密码仅供本地开发和评审演示使用)*

---

## ❓ 常见“打不开前端 / 无法登录”排查指引 (FAQ)

- **Q1：为什么我直接双击 `index.html` 页面是空白的？**
  - **原因**：本项目采用 Vue 3 + Vite 现代工程化架构，代码通过原生 ES Modules（`<script type="module">`）加载。直接用文件浏览器打开（`file:///...` 协议）会被现代浏览器的沙箱跨域安全机制（CORS）拦截。
  - **解决办法**：请在终端中执行 `npm run dev`，并通过浏览器访问 `http://localhost:5173`。

- **Q2：打开前端网页后，输入账号密码点击登录提示“无法连接服务器”？**
  - **原因**：这是因为**只启动了前端、未启动后端 Django 服务**。
  - **解决办法**：在另一个独立的终端中进入 `backend/` 目录并运行 `python manage.py runserver`，确保后端在 `8000` 端口保持运行状态。

- **Q3：提示 5173 或 8000 端口被占用怎么办？**
  - Vite 会自动探测顺延至 `5174`、`5175` 端口并在控制台提示新地址；
  - 若 Django 的 8000 端口被其他程序占用，可指定端口启动：`python manage.py runserver 8001`，并同步更新 `.env` 中的 `VITE_API_BASE_URL`。

---

## 🌟 核心特色与智慧升级

本项目在基础借还书 CRUD 之上，重点攻关了图书馆业务场景中**性价比最高、可实现性最高、含金量最显著**的两大核心维度：

### 1. 预约排队全生命周期与超时释放机制（类似高并发电商库存预占）
- **FIFO 严格有序队列**：多名读者排队预约同一无库存书目时，按预约时间严格排队，实时计算并展示排队名次（“排在第 1 位 / 前方还有 N 人”）。
- **还书自动分配与到馆锁定（Stock Hold）**：用户还书时，后端事务检测等待队列。若有读者排队，该副本**不会流入公开池**，而是转为该读者的专属预留状态（`notified`），锁定 48 小时保留期并下发站内到馆通知。
- **超时自动释放与级联顺延（Cascade Release）**：读者若在保留期限内未借取，系统自动将其状态流转为失效（`expired`），并自动唤醒顺延给队列中的下一位读者重设保留期；若队列无人则归还至公开可用库存。
- **到馆一键核销借阅（Claim & Borrow）**：持有预留副本的读者进入系统可一键直接核销借出。
- **定时与请求驱动清理**：提供 Django 管理命令 `python manage.py release_expired_reservations`，并在业务请求中自动懒惰巡检。

### 2. 智慧图书推荐引擎与读者画像系统（AI & Data Intelligence）
- **混合推荐架构（Hybrid Recommendation Engine）**：
  - **协同过滤（Item-based CF）**：基于全馆借阅行为共现矩阵与 Jaccard 相似度，推荐“借阅过同类书籍的其他读者也在看”的书目。
  - **基于内容的偏好匹配（Content-Based）**：提取读者偏好的分类权重与常读作者，进行个性化特征匹配打分。
  - **冷启动平滑保护（Cold Start）**：新读者无借阅历史时，自适应切换至全馆热门借阅 TOP 榜与新书发现。
  - **详情页相似关联**：详情页动态展示基于同作者、同类目和借阅共现的“喜欢本书的读者还借了”。
- **读者阅读 DNA 画像（Reading DNA Portrait）**：
  - 多维度分析读者的借阅总数、准时守信履约率、偏好领域占比雷达（进度分布）与常读作者。
  - 动态生成具有文人气息的读者画像标签（如 `💻 极客先锋 · 数字技术探索者`、`📖 文心墨韵 · 沉浸思辨漫游者`、`🎯 博雅贯通 · 跨界通识博学者` 等）。

### 3. 全局通知中心（Notification Center）
- 顶部导航栏集成实时通知铃铛与未读数字角标。
- 自动下发到馆待取提醒、超时失效通知、借阅还书提醒与系统公告，支持单条已读与一键全部已读。

---

## 页面

- `/login`：登录与注册，支持学生、教职工、管理员身份。
- `/books`：书目搜索、作者分类筛选、**✨ 智慧精选为你推荐**；管理员可新增/编辑/删除书目。
- `/books/:id`：书目详情、实时借阅/排队预约状态、到馆待取倒计时核销、**📚 读者相似推荐**。
- `/loans`：包含**当前在借**、**预约排队追踪**、**读者画像 Reading DNA**、**借阅历史**四合一中枢。
- `/admin`：管理员统计面板，实时监控流通、借出、逾期、预约排队中与到馆锁定册数，及全馆借阅 TOP10 榜。

## REST API

后端 API 位于 `backend/`，前端请求集中封装在 `src/api/index.js`。访问 `http://localhost:8000/` 会返回服务状态，业务接口统一使用 `/api/` 前缀。

### 认证
- `POST /auth/login`
- `POST /auth/register`
- 成功响应：`{ "token": "...", "refresh": "...", "user": { "id": "uuid", "name": "...", "email": "...", "role": "student|staff|admin" } }`

### 书目与推荐
- `GET /books?search=&author=&category=`：书目列表与条件检索
- `GET /books/:id`：书目详情
- `GET /recommendations/for-you`：个性化为你推荐（基于协同过滤与阅读画像）
- `GET /recommendations/books/:id/related`：指定书目的相似/关联推荐
- `GET /recommendations/user-profile`：当前登录读者的阅读画像与 Reading DNA 数据

### 借阅与预约
- `GET /loans/my`：当前用户的借阅记录
- `POST /loans`：借阅图书（自动支持普通借阅与到馆预约核销借阅）
- `PATCH /loans/:id/return`：归还图书并结算罚款，自动触发后续排队预约顺延
- `GET /reservations`：当前用户的预约列表（包含排队序号与保留剩余时间）
- `POST /reservations`：提交预约排队
- `POST /reservations/:id/claim`：预约到馆一键借出
- `POST /reservations/:id/cancel`：取消预约（若处于锁定保留期则顺延给下一位）

### 消息通知
- `GET /notifications`：获取个人通知列表
- `GET /notifications/unread-count`：未读消息数
- `POST /notifications/:id/read`：标记单条已读
- `POST /notifications/read-all`：一键全部已读

### 管理员中枢
- `GET /admin/stats`：全馆统计与借阅榜单

## 数据库设计

关键关系表由 Django migration 管理：

- `library_user`：UUID 主键、姓名、唯一邮箱、哈希密码、`student/staff/admin` 角色。
- `library_book`：UUID 主键、书名、ISBN、出版社、年份、摘要、分类、总库存和可借库存。
- `library_author` 与 `library_bookauthor`：作者和书目多对多关系。
- `library_category`：分类字典。
- `library_loan`：用户、书目、借阅时间、应还时间、归还时间、借阅状态和罚款金额。
- `library_reservation`：预约记录，支持 `waiting`（排队中）、`notified`（到馆保留）、`fulfilled`（已满足）、`expired`（超时失效）、`cancelled`（已取消），包含保留截止时间 `hold_expires_at`。
- `library_notification`：用户系统通知与到馆/失效提醒。
- `library_auditlog`：操作审计记录。

借阅与库存流转全程使用 `transaction.atomic()` 和 `select_for_update()`，严防并发超卖与库存悬挂。
