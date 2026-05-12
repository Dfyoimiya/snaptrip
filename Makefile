.PHONY: help init dev up down build logs test-backend test lint migrate clean

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ===== 初始化 =====

init: .env docker-compose.override.yml ## 初始化项目（复制配置、安装依赖）
	@echo "==> 安装后端依赖..."
	cd backend && python3 -m venv .venv && .venv/bin/pip install uv && .venv/bin/uv pip install -r pyproject.toml
	@echo "==> 安装前端依赖..."
	cd frontend && npm install
	@echo "==> 初始化完成! 运行 make dev 启动开发环境"

.env:
	cp -n .env.example .env 2>/dev/null || true

docker-compose.override.yml:
	cp -n docker-compose.override.example.yml docker-compose.override.yml 2>/dev/null || true

# ===== Docker =====

up: ## 启动全栈（production 模式）
	docker compose up -d --build

down: ## 停止全栈
	docker compose down

dev: ## 启动开发环境（热重载）
	BUILD_TARGET=development docker compose -f docker-compose.yml -f docker-compose.override.yml up --build

build: ## 构建所有镜像
	docker compose build

logs: ## 查看日志
	docker compose logs -f

# ===== 后端 =====

backend-dev: ## 仅启动后端（本地）
	cd backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

backend-shell: ## 进入后端容器
	docker compose exec backend bash

# ===== 测试 =====

test-backend: ## 运行后端测试
	cd backend && .venv/bin/pytest tests/ -v --cov=app --cov-report=term-missing

test: test-backend ## 运行全部测试

# ===== 代码质量 =====

lint: ## 代码检查
	cd backend && .venv/bin/ruff check app/ && .venv/bin/mypy app/
	cd frontend && npx tsc --noEmit

format: ## 代码格式化
	cd backend && .venv/bin/ruff format app/

# ===== 数据库 =====

migrate: ## 生成数据库迁移
	cd backend && .venv/bin/alembic revision --autogenerate -m "auto"

migrate-up: ## 执行数据库迁移
	cd backend && .venv/bin/alembic upgrade head

migrate-down: ## 回滚数据库迁移
	cd backend && .venv/bin/alembic downgrade -1

# ===== 清理 =====

clean: ## 清理临时文件
	docker compose down -v
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.venv frontend/node_modules
