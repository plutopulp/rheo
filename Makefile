# Async Downloader - Makefile
CODE_PATHS := src tests

.PHONY: help clean format lint test test-cov test-quick type-check ci docs-cli

.DEFAULT_GOAL := help

help:
	@echo "Async Downloader - Make Commands"
	@echo ""
	@echo "Usage: make <command>"
	@echo ""
	@echo "Development:"
	@echo "  make format                   Format code with black and isort"
	@echo "  make lint                     Lint code with flake8"
	@echo "  make type-check               Run type checking with mypy"
	@echo "  make test                     Run tests with coverage"
	@echo "  make test-quick               Run tests without coverage"
	@echo "  make test-cov                 Run tests with coverage and open HTML report"
	@echo "  make ci                       Run all CI checks locally"
	@echo "  make docs-cli                 Generate CLI documentation"
	@echo "  make clean                    Clean up build artifacts"

clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml junit.xml .pytest_cache/ .mypy_cache/
	rm -rf dist/ build/ *.egg-info

format:
	@echo "Formatting code..."
	poetry run black $(CODE_PATHS)
	poetry run isort $(CODE_PATHS)

lint:
	@echo "Linting code..."
	poetry run flake8 $(CODE_PATHS)

type-check:
	@echo "Running type checks..."
	poetry run mypy src

test:
	@echo "Running tests with coverage..."
	poetry run pytest tests --cov=src/async_download_manager --cov-report=term-missing --cov-report=html -v

test-quick:
	@echo "Running tests without coverage..."
	poetry run pytest tests -v

test-cov:
	@echo "Running tests with coverage and opening report..."
	poetry run pytest tests --cov=src/async_download_manager --cov-report=html --cov-report=term-missing -v
	@echo "Opening coverage report..."
	open htmlcov/index.html || xdg-open htmlcov/index.html

ci:
	@echo "Running all CI checks..."
	@echo "\n=== Format Check ==="
	poetry run isort --check-only $(CODE_PATHS)
	poetry run black --check $(CODE_PATHS)
	@echo "\n=== Linting ==="
	poetry run flake8 $(CODE_PATHS)
	@echo "\n=== Type Checking ==="
	poetry run mypy src
	@echo "\n=== Tests with Coverage ==="
	poetry run pytest tests --cov=src/async_download_manager --cov-report=term-missing --cov-report=html -v

docs-cli:
	@echo "Generating CLI documentation..."
	poetry run typer async_download_manager.cli.main utils docs --name adm --output docs/CLI.md
	@echo "CLI documentation generated at docs/CLI.md"
