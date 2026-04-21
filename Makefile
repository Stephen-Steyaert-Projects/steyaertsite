.PHONY: help deploy deploy-moviesdb deploy-swccg up down restart logs clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

deploy: ## Pull latest images and deploy all services
	docker compose pull && \
	docker compose up -d && \
	docker image prune -af

deploy-moviesdb: ## Pull and deploy only the movies site
	docker compose pull website && \
	docker compose up -d website && \
	docker image prune -af

deploy-swccg: ## Pull and deploy only the SWCCG site
	docker compose pull swccg && \
	docker compose up -d swccg && \
	docker image prune -af

down: ## Stop and remove services
	docker compose down

restart: ## Restart services
	docker compose restart

logs: ## View logs from services
	docker compose logs -f

clean: ## Clean up Python cache and Docker resources
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	docker system prune -af
