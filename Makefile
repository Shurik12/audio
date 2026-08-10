TUNNEL_PORT = 80

GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m # No Color

.DEFAULT_GOAL := help

.PHONY: help
help: 
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

.PHONY: up
up: ## Run containers
	docker-compose up -d
	@$(MAKE) status

.PHONY: down
down: ## Stop containers
	docker-compose down

.PHONY: restart
restart: ## Restart containers
	docker-compose restart
	@$(MAKE) status

.PHONY: logs
logs: ## Show logs all containers
	docker-compose logs -f

.PHONY: status
status: ## Show run containers
	docker-compose ps

.PHONY: build
build: ## Build containers
	docker-compose build

.PHONY: build-backend
build-backend: ## Build only backend container
	cd backend && docker build -t audio-backend .

.PHONY: build-frontend
build-frontend: ## Build only frontend container
	cd frontend && npm run build
	@$(MAKE) copy-frontend

.PHONY: rebuild
rebuild: down build up

.PHONY: frontend-install
frontend-install:
	cd frontend && npm install

.PHONY: frontend-build
frontend-build: ## Build frontend
	cd frontend && npm run build
	@$(MAKE) copy-frontend

.PHONY: copy-frontend
copy-frontend: ## Copy frontend to nginx
	@docker cp $(FRONTEND_DIR)/dist/. burnout-nginx:/usr/share/nginx/html/ 2>/dev/null
	@$(MAKE) reload-nginx

.PHONY: tunnel
tunnel: ## Run internet tunnel
	npx localtunnel --port $(TUNNEL_PORT)

.PHONY: reload-nginx
reload-nginx: ## Reload nginx
	@docker exec burnout-nginx nginx -s reload 2>/dev/null

.PHONY: nginx-config
nginx-config: ## Print nginx config
	@docker exec burnout-nginx cat /etc/nginx/nginx.conf 2>/dev/null

.PHONY: clean
clean: ## Stop and remove containers
	docker-compose down -v
	
.PHONY: clean-frontend
clean-frontend: ## Clean frontend
	rm -rf frontend/dist
	rm -rf frontend/node_modules/.vite

.PHONY: bash-backend
bash-backend: ## Exec into backend container
	@docker exec -it burnout-backend bash

.PHONY: bash-frontend
bash-frontend: ## Exec into frontend container
	@docker exec -it burnout-frontend bash

.PHONY: bash-nginx
bash-nginx: ## Exec into nginx container
	@docker exec -it burnout-nginx bash

.PHONY: start
start: frontend-build rebuild tunnel