# Variables
CODE_PATHS := src tests

.PHONY: help logs clean format lint test

# Default target
help:
	@echo "Async-Download-Manager Commands"
	@echo ""
	@echo "Usage:"
	# consider displaying logs file
	# @echo "  make logs       View server logs (Ctrl+C to exit)"
	@echo "  make clean      Remove containers and images"
	@echo "  make format     Format code with black and isort"
	@echo "  make lint       Lint code with flake8"
	@echo "  make test       Run tests"

clean:
	@echo "Cleaning Python cache..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

format:
	@echo "Formatting code..."
	poetry run black $(CODE_PATHS)
	poetry run isort $(CODE_PATHS)

lint:
	@echo "Linting code..."
	poetry run flake8 $(CODE_PATHS)

test:
	@echo "Running tests..."
	poetry run pytest
