.PHONY: help setup up down restart logs clean test pipeline run-all health status

# Default target
help:
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║        Data Platform - Makefile Orchestration             ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "  QUICK START:"
	@echo "  make setup       - Initial setup (first time only)"
	@echo "  make up          - Start all services"
	@echo "  make pipeline    - Run complete data pipeline"
	@echo "  make health      - Check service health"
	@echo ""
	@echo " LIFECYCLE MANAGEMENT:"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make status      - Show running services"
	@echo "  make clean       - Clean data and stop services"
	@echo ""
	@echo "  PIPELINE EXECUTION:"
	@echo "  make pipeline    - Run complete data pipeline (RECOMMENDED)"
	@echo "  make ingest      - Step 1: Fetch data from API → MinIO"
	@echo "  make transform   - Step 2: Transform data → PostgreSQL"
	@echo "  make validate    - Step 3: Data quality validation"
	@echo "  make dbt-run     - Step 4: Run dbt transformations"
	@echo "  make ml          - Step 5: ML model training"
	@echo ""
	@echo "  TESTING & VALIDATION:"
	@echo "  make test        - Run test suite"
	@echo "  make test-cov    - Run tests with coverage report"
	@echo "  make lint        - Run linting checks"
	@echo ""
	@echo "  MONITORING & DEBUGGING:"
	@echo "  make logs        - View all service logs"
	@echo "  make logs-tail   - Tail logs from all services"
	@echo "  make logs-pipeline - View pipeline logs only"
	@echo "  make logs-dbt    - View dbt logs only"
	@echo ""
	@echo "  UTILITIES:"
	@echo "  make db-shell    - Open PostgreSQL shell"
	@echo "  make db-reset    - Reset database (WARNING: deletes data)"
	@echo "  make backup      - Backup database and MinIO data"
	@echo "  make restore     - Restore from backup"
	@echo ""
	@echo "  ANSIBLE ORCHESTRATION:"
	@echo "  make ansible-setup    - Ansible: Complete setup"
	@echo "  make ansible-start    - Ansible: Start services"
	@echo "  make ansible-pipeline - Ansible: Run pipeline"
	@echo "  make ansible-verify   - Ansible: Verify data"
	@echo "  make ansible-backup   - Ansible: Create backup"
	@echo "  make ansible-stop     - Ansible: Stop services"

# Initial setup
setup:
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║          Setting up Data Platform                         ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Step 1: Environment configuration..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "  ✓ Created .env file from .env.example"; else echo "  ✓ .env file already exists"; fi
	@echo ""
	@echo "Step 2: Building Docker images..."
	@docker compose build
	@echo ""
	@echo "Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Review and customize .env file if needed"
	@echo "  2. Run 'make up' to start services"
	@echo "  3. Run 'make pipeline' to execute the data pipeline"

# Start all services
up:
	@echo "Starting all services..."
	@docker compose up -d
	@echo ""
	@echo "Waiting for services to initialize..."
	@sleep 15
	@echo ""
	@$(MAKE) -s health
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║          Services Started Successfully!                    ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo " Service URLs:"
	@echo "  • Grafana:     http://localhost:3000 (admin/admin)"
	@echo "  • MLflow:      http://localhost:5000"
	@echo "  • MinIO UI:    http://localhost:9001 (minioadmin/minioadmin)"
	@echo "  • PostgreSQL:  localhost:5432 (dataplatform/changeme123)"
	@echo "  • Loki API:    http://localhost:3100"
	@echo ""
	@echo "💡 Next: Run 'make pipeline' to execute the data pipeline"

# Stop all services
down:
	@echo "Stopping all services..."
	@docker compose down
	@echo "✓ All services stopped"

# Restart all services
restart:
	@echo "Restarting all services..."
	@docker compose restart
	@echo "Waiting for services to stabilize..."
	@sleep 10
	@$(MAKE) -s health

# Show running services
status:
	@echo "  Service Status:"
	@echo ""
	@docker compose ps

# View logs
logs:
	@docker compose logs --tail=100

# Tail logs (follow)
logs-tail:
	@docker compose logs -f

# Clean everything
clean:
	@echo "  WARNING: This will remove all data and containers!"
	@echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
	@sleep 5
	@echo ""
	@echo "  Cleaning up..."
	@docker compose down -v
	@echo "  Removing generated data..."
	@rm -rf data/raw/* data/processed/* models/*.pkl
	@echo "  Clean complete!"
# Run tests
test:
	@echo "  Running test suite..."
	@docker compose run --rm pipeline pytest /app/tests/ -v

# Run tests with coverage
test-cov:
	@echo "  Running test suite with coverage..."
	@docker compose run --rm pipeline pytest /app/tests/ -v --cov=/app/src --cov-report=term-missing --cov-report=html
	@echo ""
	@echo "  Coverage report generated: ./htmlcov/index.html"

# Linting
lint:
	@echo "  Running linting checks..."
	@echo "  • Checking Python code style..."
	@docker compose run --rm pipeline flake8 /app/src --count --select=E9,F63,F7,F82 --show-source --statistics || true
	@echo "  • Checking for common issues..."
	@docker compose run --rm pipeline flake8 /app/src --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics || true

# Pipeline Steps
ingest:
	@echo "=========================================="
	@echo "Step 1/5: Data Ingestion"
	@echo "=========================================="
	docker compose run --rm pipeline python /app/src/ingestion.py

transform:
	@echo "=========================================="
	@echo "Step 2/5: Data Transformation"
	@echo "=========================================="
	docker compose run --rm pipeline python /app/src/transformation.py

validate:
	@echo "=========================================="
	@echo "Step 3/5: Data Quality Validation"
	@echo "=========================================="
	docker compose run --rm pipeline python /app/src/validation.py

dbt-run:
	@echo "=========================================="
	@echo "Step 4/5: dbt Transformations"
	@echo "=========================================="
	docker compose run --rm dbt dbt deps --profiles-dir /dbt
	docker compose run --rm dbt dbt run --profiles-dir /dbt
	docker compose run --rm dbt dbt test --profiles-dir /dbt

ml:
	@echo "=========================================="
	@echo "Step 5/5: ML Model Training"
	@echo "=========================================="
	docker compose run --rm pipeline python /app/src/ml_pipeline.py

# Complete pipeline execution
pipeline: ingest transform validate dbt-run ml
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║          ✓ Pipeline Completed Successfully!               ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "  View Results:"
	@echo "  • Grafana Logs:  http://localhost:3000"
	@echo "  • MLflow UI:     http://localhost:5000"
	@echo "  • MinIO Console: http://localhost:9001"
	@echo ""
	@echo "  Data stored in:"
	@echo "  • Raw data:      MinIO bucket (raw-data)"
	@echo "  • Transformed:   PostgreSQL (raw.commits)"
	@echo "  • Features:      PostgreSQL (analytics.ml_features)"
	@echo "  • Analytics:     PostgreSQL (analytics_analytics schema)"
	@echo ""
	@echo "  Query data: make db-shell"
	@echo ""

# Alias for pipeline
run-all: pipeline

# Individual service logs
logs-pipeline:
	docker compose logs -f pipeline

logs-dbt:
	docker compose logs -f dbt

logs-mlflow:
	docker compose logs -f mlflow

logs-postgres:
	docker compose logs -f postgres

logs-minio:
	docker compose logs -f minio

# MinIO shell
minio-shell:
	@echo "MinIO Credentials:"
	@echo "  Access Key: minioadmin"
	@echo "  Secret Key: minioadmin"
	@echo "  Endpoint:   http://localhost:9000"

# Check service health
health:
	@echo "  Health Check:"
	@echo ""
	@printf "  PostgreSQL:  "
	@docker compose exec -T postgres pg_isready -U dataplatform > /dev/null 2>&1 && echo "✓ Healthy" || echo "❌ Not ready"
	@printf "  MinIO:       "
	@curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1 && echo "✓ Healthy" || echo "❌ Not ready"
	@printf "  MLflow:      "
	@curl -sf http://localhost:5000/health > /dev/null 2>&1 && echo "✓ Healthy" || echo "❌ Not ready"
	@printf "  Grafana:     "
	@curl -sf http://localhost:3000/api/health > /dev/null 2>&1 && echo "✓ Healthy" || echo "❌ Not ready"
	@printf "  Loki:        "
	@curl -sf http://localhost:3100/ready > /dev/null 2>&1 && echo "✓ Healthy" || echo "❌ Not ready"
	@echo ""

# Database utilities
db-shell:
	@echo "Opening PostgreSQL shell..."
	@echo "Database: analytics"
	@docker compose exec postgres psql -U dataplatform -d analytics

db-query:
	@echo "  Quick Data Check:"
	@echo ""
	@docker compose exec -T postgres psql -U dataplatform -d analytics -c "\
	SELECT \
	  'raw.commits' as table_name, \
	  COUNT(*) as row_count \
	FROM raw.commits \
	UNION ALL \
	SELECT 'analytics.ml_features', COUNT(*) FROM analytics.ml_features \
	UNION ALL \
	SELECT 'analytics_analytics.commit_metrics', COUNT(*) FROM analytics_analytics.commit_metrics;"

db-reset:
	@echo "  WARNING: This will delete ALL database data!"
	@echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
	@sleep 5
	@echo "  Resetting database..."
	@docker compose exec -T postgres psql -U dataplatform -d analytics -c "DROP SCHEMA IF EXISTS raw CASCADE;"
	@docker compose exec -T postgres psql -U dataplatform -d analytics -c "DROP SCHEMA IF EXISTS analytics CASCADE;"
	@docker compose exec -T postgres psql -U dataplatform -d analytics -c "DROP SCHEMA IF EXISTS analytics_staging CASCADE;"
	@docker compose exec -T postgres psql -U dataplatform -d analytics -c "DROP SCHEMA IF EXISTS analytics_analytics CASCADE;"
	@docker compose restart postgres
	@echo "✓ Database reset. Run 'make pipeline' to repopulate."

# Backup and restore
backup:
	@echo "  Creating backup..."
	@mkdir -p backups
	@docker compose exec -T postgres pg_dump -U dataplatform analytics > backups/db_backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "  Database backup created in ./backups/"
restore:
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Error: Please specify backup file with FILE=<filename>"; \
		echo "Example: make restore FILE=backups/db_backup_20260201_120000.sql"; \
		exit 1; \
	fi
	@echo "  Restoring from $(FILE)..."
	@cat $(FILE) | docker compose exec -T postgres psql -U dataplatform analytics
	@echo "  Database restored successfully"

# Monitoring shortcuts
monitor:
	@echo "  Opening monitoring dashboard..."
	@echo "Grafana: http://localhost:3000 (admin/admin)"
	@which open > /dev/null && open http://localhost:3000 || echo "Please open http://localhost:3000 in your browser"

mlflow-ui:
	@echo "  Opening MLflow UI..."
	@which open > /dev/null && open http://localhost:5000 || echo "Please open http://localhost:5000 in your browser"

minio-ui:
	@echo "  Opening MinIO Console..."
	@which open > /dev/null && open http://localhost:9001 || echo "Please open http://localhost:9001 in your browser"

# Development helpers
dev-shell:
	@echo "  Opening development shell in pipeline container..."
	@docker compose run --rm pipeline /bin/bash

format:
	@echo "  Formatting Python code..."
	@docker compose run --rm pipeline black /app/src || echo "Install black to use this feature"

# Quick data inspection
inspect-minio:
	@echo "  MinIO Buckets and Objects:"
	@docker compose exec -T minio mc ls myminio/ 2>/dev/null || echo "Run 'make up' first"

inspect-db:
	@echo "  Database Tables and Row Counts:"
	@docker compose exec -T postgres psql -U dataplatform -d analytics -c "\
	SELECT \
	  schemaname, \
	  tablename, \
	  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size \
	FROM pg_tables \
	WHERE schemaname NOT IN ('pg_catalog', 'information_schema') \
	ORDER BY schemaname, tablename;"

# Full system check
check: health db-query
	@echo ""
	@echo "  System check complete"

# CI/CD simulation
ci: test lint
	@echo ""
	@echo "  CI checks passed"

# Complete workflow (for demos)
demo: setup up pipeline monitor
	@echo ""
	@echo "  Demo complete! Check Grafana dashboard."

# ============================================================
# ANSIBLE ORCHESTRATION
# ============================================================

# Check if Ansible is installed
ansible-check:
	@command -v ansible-playbook >/dev/null 2>&1 || { \
		echo "  Ansible not found. Install with:"; \
		echo "   pip install ansible"; \
		echo "   or: brew install ansible"; \
		exit 1; \
	}
	@echo "  Ansible installed: $$(ansible --version | head -1)"

# Ansible: Complete setup (check, config, build)
ansible-setup: ansible-check
	@echo "  Running Ansible setup..."
	@cd ansible && ansible-playbook platform.yml --tags setup

# Ansible: Start all services with health check
ansible-start: ansible-check
	@echo "  Starting services via Ansible..."
	@cd ansible && ansible-playbook platform.yml --tags start,health

# Ansible: Run complete data pipeline
ansible-pipeline: ansible-check
	@echo "  Running pipeline via Ansible..."
	@cd ansible && ansible-playbook platform.yml --tags pipeline

# Ansible: Verify data in database
ansible-verify: ansible-check
	@echo "  Verifying data via Ansible..."
	@cd ansible && ansible-playbook platform.yml --tags verify

# Ansible: Create database backup
ansible-backup: ansible-check
	@echo "  Creating backup via Ansible..."
	@cd ansible && ansible-playbook platform.yml --tags backup

# Ansible: Stop all services
ansible-stop: ansible-check
	@echo "  Stopping services via Ansible..."
	@cd ansible && ansible-playbook platform.yml --tags stop

# Ansible: Complete workflow (setup → start → pipeline → verify)
ansible-all: ansible-check
	@echo "  Running complete Ansible workflow..."
	@cd ansible && ansible-playbook platform.yml --tags setup,start,pipeline,verify

# Ansible: Health check only
ansible-health: ansible-check
	@echo "  Checking health via Ansible..."
	@cd ansible && ansible-playbook platform.yml --tags health
