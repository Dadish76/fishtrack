.PHONY: help setup run lint sast test migrate migrate-create \
        backup restore verify clean

# Показать доступные команды
help:
	@echo "FishTrack — доступные команды:"
	@echo "  make setup          — установка окружения с нуля"
	@echo "  make run            — запуск приложения"
	@echo "  make lint           — проверка форматирования (black, ruff)"
	@echo "  make sast           — анализ безопасности (bandit)"
	@echo "  make test           — тесты с покрытием ≥ 40%"
	@echo "  make migrate        — применить миграции"
	@echo "  make migrate-create — создать миграцию (msg='...')"
	@echo "  make backup         — создать бэкап БД"
	@echo "  make restore        — восстановить из бэкапа (file='...')"
	@echo "  make verify         — ВСЕ проверки (lint + sast + test + migrate)"
	@echo "  make clean          — очистить временные файлы"

# ============================================
# SETUP
# ============================================
setup:
	@echo "→ Создание venv..."
	python3.11 -m venv venv
	@echo "→ Установка зависимостей..."
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r backend/requirements-dev.txt
	@echo "→ Запуск БД через Docker..."
	docker-compose up -d db
	@echo "✅ Setup завершён"

# ============================================
# RUN
# ============================================
run:
	cd backend && ../venv/bin/uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# ============================================
# LINT
# ============================================
lint:
	@echo "→ black проверяет форматирование..."
	./venv/bin/black backend/src/ backend/tests/ --check
	@echo "→ ruff проверяет код..."
	./venv/bin/ruff check backend/src/ backend/tests/

# ============================================
# SAST
# ============================================
sast:
	@echo "→ bandit проверяет безопасность..."
	./venv/bin/bandit -r backend/src/ -ll

# ============================================
# TEST
# ============================================
test:
	@echo "→ pytest запускает тесты..."
	./venv/bin/pytest backend/tests/ -v \
		--cov=backend/src \
		--cov-report=term \
		--cov-report=html \
		--cov-fail-under=40

# ============================================
# MIGRATIONS
# ============================================
migrate:
	cd backend && ../venv/bin/alembic upgrade head

migrate-create:
	cd backend && ../venv/bin/alembic revision --autogenerate -m "$(msg)"

# ============================================
# BACKUP / RESTORE
# ============================================
backup:
	@mkdir -p backups
	docker exec fishtrack_db pg_dump -U user fishtrack > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Бэкап создан"

restore:
	docker exec -i fishtrack_db psql -U user fishtrack < $(file)
	@echo "✅ Бэкап восстановлен"

# ============================================
# VERIFY — ГЛАВНАЯ КОМАНДА
# ============================================
verify: lint sast test migrate
	@echo ""
	@echo "✅✅✅ Все проверки пройдены! ✅✅✅"
	@echo ""

# ============================================
# CLEAN
# ============================================
clean:
	rm -rf .pytest_cache .coverage htmlcov .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "✅ Временные файлы удалены"