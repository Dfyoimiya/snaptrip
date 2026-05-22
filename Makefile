.PHONY: help init dev up down build logs test test-backend test-unit test-integration lint format migrate migrate-up migrate-down mock-up test-up test-down clean

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ===== 初始化 =====

init: .env docker-compose.override.yml ## 初始化项目（复制配置、安装依赖）
	@echo "==> 安装后端依赖 (workspace)..."
	uv sync --extra dev
	@echo "==> 安装前端依赖..."
	cd frontend && npm install
	@echo "==> 初始化完成! 运行 make dev 启动开发环境"

.env:
	cp -n .env.example .env 2>/dev/null || true

docker-compose.override.yml:
	cp -n docker-compose.override.example.yml docker-compose.override.yml 2>/dev/null || true

# ===== Docker =====

up: ## 启动全栈（production 模式）
	docker compose --profile full up -d --build

down: ## 停止全栈
	docker compose down

dev: ## 启动开发环境（热重载）
	BUILD_TARGET=development docker compose --profile dev -f docker-compose.yml -f docker-compose.override.yml up --build

build: ## 构建所有镜像
	docker compose build

logs: ## 查看日志
	docker compose logs -f

# ===== 后端 =====

backend-dev: ## 仅启动后端（本地）
	cd backend && uv run uvicorn marketplace.app.main:app --host 0.0.0.0 --port 8080 --reload

backend-shell: ## 进入 Marketplace 容器
	docker compose exec marketplace bash

# ===== 测试 =====

TEST_ENV = APP_ENV=test DATABASE_TEST_URL=postgresql+asyncpg://snaptrip:snaptrip_dev_pass@localhost:5433/snaptrip_test REDIS_URL=redis://localhost:6380/0 APP_SECRET_KEY=test-secret JWT_SECRET_KEY=test-jwt-secret OPENROUTER_API_KEY=placeholder MOCK_FAULT_RATE=0 MOCK_DELAY_RATE=0

test-unit: ## 运行单元测试
	cd backend && $(TEST_ENV) uv run pytest tests/unit/ -v --cov=marketplace --cov=agent_worker --cov=shared --cov-report=xml --cov-report=term

test-integration: ## 运行集成测试
	cd backend && $(TEST_ENV) uv run pytest tests/integration/ -v

test-backend: test-unit test-integration ## 运行全部后端测试

test: test-backend ## 运行全部测试

test-up: ## 启动测试数据库
	docker compose -f docker-compose.test.yml up -d

test-down: ## 停止测试数据库
	docker compose -f docker-compose.test.yml down

# ===== Mock 服务 =====

mock-up: ## 启动 Mock 服务（本地）
	cd mock_server && uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload &

# ===== 代码质量 =====

lint: ## 代码检查（ruff + mypy）
	cd backend && uv run ruff check marketplace/ agent_worker/ shared/ tests/
	cd backend && uv run mypy marketplace/ agent_worker/ shared/

lint-frontend: ## 前端类型检查
	cd frontend && npx -p typescript tsc --noEmit

format: ## 代码格式化
	cd backend && uv run ruff format marketplace/ agent_worker/ shared/ tests/

# ===== 数据库 =====

migrate: ## 生成数据库迁移
	cd backend && uv run alembic revision --autogenerate -m "auto"

migrate-up: ## 执行数据库迁移
	cd backend && uv run alembic upgrade head

migrate-down: ## 回滚数据库迁移
	cd backend && uv run alembic downgrade -1

# ===== 清理 =====

clean: ## 清理临时文件
	docker compose down -v 2>/dev/null || true
	docker compose -f docker-compose.test.yml down -v 2>/dev/null || true
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.venv frontend/node_modules
