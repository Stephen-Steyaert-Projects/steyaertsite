.PHONY: help deploy deploy-moviesdb deploy-swccg up down restart logs k8s-apply k8s-deploy-website k8s-deploy-swccg k8s-rollback-website k8s-rollback-swccg k8s-logs-website k8s-logs-swccg k8s-restart-website k8s-restart-swccg k8s-down clean

NAMESPACE = steyaertsite
WEBSITE_IMAGE = ghcr.io/stephen-steyaert-projects/steyaertsite/steyaert-site
SWCCG_IMAGE = ghcr.io/stephen-steyaert-projects/steyaertsite/swccg-site

# k8s-deploy-* pin to this tag instead of :latest - a :latest update can
# no-op if the cluster doesn't see the tag string itself change, even though
# the digest behind it moved. CI passes TAG=sha-<short sha>. Defaults to
# latest for manual use.
TAG ?= latest

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

k8s-apply: ## Apply/update all k8s manifests (namespace, db, mail, website, swccg)
	kubectl apply -f k8s/

k8s-deploy-website: ## Force a fresh pull + redeploy of the movies site on k3s. Pass TAG=<tag> to pin a build (defaults to latest)
	kubectl set image deployment/website website=$(WEBSITE_IMAGE):$(TAG) -n $(NAMESPACE)
	kubectl rollout status deployment/website -n $(NAMESPACE)

k8s-deploy-swccg: ## Force a fresh pull + redeploy of the SWCCG site on k3s. Pass TAG=<tag> to pin a build (defaults to latest)
	kubectl set image deployment/swccg swccg=$(SWCCG_IMAGE):$(TAG) -n $(NAMESPACE)
	kubectl rollout status deployment/swccg -n $(NAMESPACE)

k8s-rollback-website: ## Roll the movies site back to its previous version on k3s
	kubectl rollout undo deployment/website -n $(NAMESPACE)

k8s-rollback-swccg: ## Roll the SWCCG site back to its previous version on k3s
	kubectl rollout undo deployment/swccg -n $(NAMESPACE)

k8s-logs-website: ## Tail logs from the movies site on k3s
	kubectl logs -f deployment/website -n $(NAMESPACE)

k8s-logs-swccg: ## Tail logs from the SWCCG site on k3s
	kubectl logs -f deployment/swccg -n $(NAMESPACE)

k8s-restart-website: ## Force a rolling restart of the movies site on k3s
	kubectl rollout restart deployment/website -n $(NAMESPACE)

k8s-restart-swccg: ## Force a rolling restart of the SWCCG site on k3s
	kubectl rollout restart deployment/swccg -n $(NAMESPACE)

k8s-down: ## Remove everything in the k8s namespace
	kubectl delete namespace $(NAMESPACE)

clean: ## Clean up Python cache and Docker resources
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	docker system prune -af
