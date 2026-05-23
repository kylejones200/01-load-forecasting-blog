# Makefile for LEAP local development

.PHONY: help install run test clean lint format

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

run: ## Run the Flask application
	python run.py

test: ## Run tests
	python -m pytest tests/

clean: ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf app/static/img/*.png

lint: ## Run linting
	@echo "Linting not configured yet"

format: ## Format code
	@echo "Formatting not configured yet"

dev: ## Run in development mode with auto-reload
	FLASK_ENV=development python run.py

prod: ## Run in production mode
	gunicorn -w 4 -b 0.0.0.0:8000 run:app

check-env: ## Check environment configuration
	@echo "Checking environment configuration..."
	@if [ ! -f .env ]; then echo "Warning: .env file not found. Copy from env.example"; fi
	@echo "Environment check complete"

setup: install check-env ## Initial setup
	@echo "Setup complete. Run 'make run' to start the application"

