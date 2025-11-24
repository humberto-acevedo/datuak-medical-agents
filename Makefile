.PHONY: help build up down test clean logs

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker containers
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

test: ## Run tests
	docker-compose exec xml-parser-agent pytest tests/ -v

test-coverage: ## Run tests with coverage
	docker-compose exec xml-parser-agent pytest tests/ --cov=src --cov-report=html

logs: ## Show logs from all services
	docker-compose logs -f

logs-xml: ## Show logs from XML parser agent
	docker-compose logs -f xml-parser-agent

logs-summary: ## Show logs from medical summarization agent
	docker-compose logs -f medical-summarization-agent

logs-research: ## Show logs from research correlation agent
	docker-compose logs -f research-correlation-agent

shell-xml: ## Open shell in XML parser agent
	docker-compose exec xml-parser-agent /bin/bash

clean: ## Clean up containers and volumes
	docker-compose down -v
	docker system prune -f

setup-env: ## Copy environment template
	cp .env.example .env
	@echo "Please edit .env with your AWS credentials"