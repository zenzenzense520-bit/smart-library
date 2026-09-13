# Django REST API

运行前端和后端的完整说明见仓库根目录 `README.md`。本服务默认使用 SQLite；设置 `DATABASE_URL` 后可切换 PostgreSQL。

```bash
uv venv .venv
uv pip install --python .venv\\Scripts\\python.exe -r requirements.txt
uv run --python .venv\\Scripts\\python.exe python manage.py migrate
uv run --python .venv\\Scripts\\python.exe python manage.py seed_demo
uv run --python .venv\\Scripts\\python.exe python manage.py runserver
```
