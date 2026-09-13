# 知行书院 · 智慧图书馆全栈

基于 Vue 3 + Vite + JavaScript、Django + Django REST Framework 的大学智慧图书管理系统。JWT 认证、书目管理、借阅、归还罚款、预约和管理员统计均由后端提供 REST API。

默认数据库是 Django SQLite，适合开发和演示；通过 `DATABASE_URL` 可以切换 PostgreSQL。当前目录保留 Vue SPA，后端位于 `backend/`。

## 启动

```bash
npm install
npm run dev
```

默认开发地址：`http://localhost:5173`

生产构建：

```bash
npm run build
npm run preview
```

## 全栈启动

后端使用 uv 管理 Python 环境：

```powershell
Set-Location backend
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
uv run --python .venv\Scripts\python.exe python manage.py migrate
uv run --python .venv\Scripts\python.exe python manage.py seed_demo
uv run --python .venv\Scripts\python.exe python manage.py runserver
```

另开终端启动 Vue：

```powershell
npm run dev
```

默认服务地址：前端 `http://localhost:5173`，后端 `http://localhost:8000`。

### Docker Compose

```powershell
docker compose up --build
```

Compose 会启动后端和 Vue 开发服务器。后端容器启动时自动迁移并执行 `seed_demo`。默认 Compose 仍使用 SQLite；生产环境建议注入 PostgreSQL `DATABASE_URL`，并替换 Django 密钥。

### 示例账户

种子命令创建以下本地演示账户：

- 管理员：`admin@zhixing.local` / `Admin123!`
- 学生：`student@zhixing.local` / `Student123!`
- 教职工：`staff@zhixing.local` / `Staff123!`

这些密码仅用于本地演示，不得用于生产环境。

## 环境变量

复制 `.env.example` 为 `.env`，按后端地址修改：

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

如果未配置，前端默认请求 `http://localhost:8000/api`。

## 页面

- `/login`：登录与注册，支持学生、教职工、管理员身份。
- `/books`：书目搜索、作者和分类筛选；管理员可以新增、编辑和删除书目。
- `/books/:id`：书目详情、库存信息和借阅操作。
- `/loans`：当前借阅、借阅历史、归还和逾期状态。
- `/admin`：管理员统计面板，仅管理员角色可访问。

## REST API

后端 API 位于 `backend/`，前端请求集中封装在 `src/api/index.js`。访问 `http://localhost:8000/` 会返回服务状态，业务接口统一使用 `/api/` 前缀。

### 认证

- `POST /auth/login`
- `POST /auth/register`
- 成功响应：`{ "token": "...", "refresh": "...", "user": { "id": "uuid", "name": "...", "email": "...", "role": "student|staff|admin" } }`
- 失败响应兼容：`{ "message": "错误说明" }`

登录后所有受保护请求自动携带：`Authorization: Bearer <token>`。

### 书目

- `GET /books?search=&author=&category=`
- `GET /books/:id`
- `POST /books`
- `PUT /books/:id`
- `DELETE /books/:id`

列表响应可以是数组，也可以是 `{ "items": [] }` 或 `{ "books": [] }`。书目建议包含 `id`、`title`、`author`、`category`、`isbn`、`description`、`totalCopies`、`availableCopies`。

### 借阅

- `GET /loans/my`
- `POST /loans`，请求体：`{ "book_id": "uuid" }`
- `PATCH /loans/:id/return`

借阅记录建议包含 `id`、`book`、`dueDate`、`status`、`returnedAt`。逾期判定以服务端 `status` 为准，前端会同时兼容根据 `dueDate` 展示提醒。

### 管理统计

- `GET /admin/stats`
- 建议返回 `totalBooks`、`availableBooks`、`activeLoans`、`overdueLoans`，前端也兼容对应的 `totalCopies`、`availableCopies`、`borrowedCount`、`overdueCount` 字段。

## 数据库设计

关键关系表由 Django migration 管理：

- `library_user`：UUID 主键、姓名、唯一邮箱、哈希密码、`student/staff/admin` 角色和时间字段。
- `library_book`：UUID 主键、书名、ISBN、出版社、年份、摘要、分类、总库存和可借库存。
- `library_author` 与 `library_bookauthor`：作者和书目多对多关系。
- `library_category`：分类字典。
- `library_loan`：用户、书目、借阅时间、应还时间、归还时间、借阅状态和罚款金额。
- `library_reservation`：用户预约书目、预约时间和等待/满足/取消状态，等待中的同一用户同一本书不可重复预约。
- `library_auditlog`：可选的操作审计记录。

本实现没有拆分物理副本表，库存由 `total_copies` 与 `available_copies` 表示。借阅使用 `transaction.atomic()` 和 `select_for_update()` 锁定书目，避免并发超借。

## 目录说明

```text
src/
  api/index.js          REST 请求与 JWT 会话
  router/index.js       路由和角色守卫
  components/NavBar.vue 全局导航
  views/                登录、书目、详情、借阅、管理员页面
  assets/main.css       全局响应式视觉样式
backend/
  config/                Django 配置和 URL
  library/models.py      关系模型
  library/serializers.py REST 序列化
  library/views.py       认证、书目、借阅、预约、统计 API
  library/management/    seed_demo 示例数据
docker-compose.yml       前后端开发容器
```

## 对接边界

- 前端只保存 JWT 和必要的用户会话信息，不把 token 放入 URL。
- 401 会自动清除本地会话，路由守卫会引导用户重新登录。
- 前端不会伪造书目、借阅或统计数据；后端不可用时展示明确错误。
- 角色权限必须由后端再次校验，前端路由守卫只负责改善使用体验。
