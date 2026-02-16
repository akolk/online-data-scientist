# Makefile for Online Data Scientist
# Provides convenient commands for development, testing, and quality checks

.PHONY: help install install-dev test test-cov lint format clean setup-hooks check-syntax check-security docker-build

# Default target
help:
	@echo "Online Data Scientist - Development Commands"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make install        Install production dependencies"
	@echo "  make install-dev    Install all development dependencies (test, lint, precommit)"
	@echo "  make setup-hooks    Install and configure pre-commit hooks"
	@echo ""
	@echo "Development Commands:"
	@echo "  make test           Run all tests"
	@echo "  make test-cov       Run tests with coverage report"
	@echo "  make lint           Run all linting checks (pycodestyle, flake8)"
	@echo "  make format         Format code with black and isort"
	@echo "  make check-syntax   Validate Python syntax for all files"
	@echo "  make check-security Run security checks (bandit)"
	@echo ""
	@echo "Quality Assurance:"
	@echo "  make check-all      Run all checks (syntax, lint, test)"
	@echo "  make fix            Auto-fix code style issues"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make docker-build   Build Docker image"
	@echo "  make docker-run     Run Docker container locally"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          Remove Python cache files and artifacts"
	@echo "  make clean-all      Clean + remove virtual environment"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev,test,lint,precommit]"

# Pre-commit hooks
setup-hooks:
	@echo "Installing pre-commit hooks..."
	pip install pre-commit
	pre-commit install
	pre-commit install --hook-type pre-push
	@echo "Pre-commit hooks installed successfully!"
	@echo "Run 'pre-commit run --all-files' to check all files manually"

# Testing
test:
	python -m pytest tests/ -v

test-cov:
	python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html

# Code quality checks
lint:
	@echo "Running pycodestyle..."
	python -m pycodestyle --max-line-length=120 app.py code_executor.py data_processor.py pages/Settings.py
	@echo "Running flake8..."
	python -m flake8 --max-line-length=120 --extend-ignore=E203,W503 app.py code_executor.py data_processor.py pages/Settings.py

check-syntax:
	@echo "Validating Python syntax..."
	python -m py_compile app.py code_executor.py data_processor.py pages/Settings.py
	@find tests -name "*.py" -exec python -m py_compile {} \;
	@echo "✓ All Python files have valid syntax"

check-security:
	@echo "Running security checks..."
	python -m bandit -r app.py code_executor.py data_processor.py pages/ -ll -ii

check-all: check-syntax lint test
	@echo "✓ All checks passed!"

# Code formatting
format:
	@echo "Formatting with black..."
	python -m black --line-length=120 app.py code_executor.py data_processor.py pages/Settings.py tests/
	@echo "Sorting imports with isort..."
	python -m isort --profile=black --line-length=120 app.py code_executor.py data_processor.py pages/Settings.py tests/

# Auto-fix
fix: format
	@echo "Auto-fixing issues where possible..."

# Docker commands
docker-build:
	docker build -t online-data-scientist:latest .

docker-run:
	@echo "Running container on http://localhost:8501"
	docker run -p 8501:8501 -e OPENAI_API_KEY=$${OPENAI_API_KEY} online-data-scientist:latest

# Cleanup
clean:
	@echo "Cleaning Python cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name "*.pyd" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleanup complete"

clean-all: clean
	@echo "Removing virtual environment..."
	rm -rf venv/ .venv/
	@echo "✓ Full cleanup complete"
