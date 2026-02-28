.PHONY: help deploy up down restart logs clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

deploy: ## Pull latest image and deploy with docker compose
	docker compose --env-file .env.prod pull && \
	docker compose --env-file .env.prod up -d && \
	docker image prune -af

up: ## Start services (pulls website image if changed)
	docker compose --env-file .env.prod pull website && \
	docker compose --env-file .env.prod up -d && \
	docker image prune -af

down: ## Stop and remove services
	docker compose --env-file .env.prod down

restart: ## Restart services
	docker compose --env-file .env.prod restart

logs: ## View logs from services
	docker compose --env-file .env.prod logs -f

clean: ## Clean up Python cache and Docker resources
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	docker system prune -af
