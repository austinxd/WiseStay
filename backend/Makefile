.PHONY: help setup venv install db migrate makemigrations run celery shell test lint check

PYTHON = python3
VENV = .venv
PIP = $(VENV)/bin/pip
MANAGE = $(VENV)/bin/python manage.py

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

venv: ## Create virtualenv
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip

install: ## Install development dependencies
	$(PIP) install -r requirements/development.txt

db: ## Create MySQL database
	mysql -u root -e "CREATE DATABASE IF NOT EXISTS wisestay CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

setup: venv install db migrate ## Full local setup (venv + deps + db + migrate)
	@echo "✔ Setup complete. Activate venv with: source $(VENV)/bin/activate"

migrate: ## Run migrations
	$(MANAGE) migrate

makemigrations: ## Generate migrations
	$(MANAGE) makemigrations

run: ## Start development server
	$(MANAGE) runserver

celery: ## Start Celery worker
	$(VENV)/bin/celery -A config worker -l info

celery-beat: ## Start Celery beat scheduler
	$(VENV)/bin/celery -A config beat -l info

shell: ## Django shell (IPython)
	$(MANAGE) shell

test: ## Run tests
	$(VENV)/bin/pytest --cov=apps --cov=common -v

lint: ## Run ruff linter
	$(VENV)/bin/ruff check .

check: ## Django system check
	$(MANAGE) check

superuser: ## Create superuser
	$(MANAGE) createsuperuser
