# Makefile Quick Reference Card

## Essential Commands (Use These Daily)

```bash
make help       # Show all available commands
make up         # Start all services
make pipeline   # Run complete data pipeline
make health     # Check if all services are running
make status     # Show container status
make down       # Stop all services
```

##  Common Workflows

### First Time Setup
```bash
make setup      # Initial setup (creates .env, builds images)
make up         # Start all services
make pipeline   # Run the pipeline
```

### Daily Development
```bash
make up         # Start your day
make health     # Verify everything is running
make pipeline   # Run pipeline to test changes
make logs-tail  # Watch logs in real-time
make down       # End of day
```

### Debugging
```bash
make logs-pipeline  # View pipeline logs
make logs-dbt       # View dbt logs
make db-shell       # Open PostgreSQL shell
make db-query       # Quick row count check
make inspect-db     # Show all tables and sizes
make inspect-minio  # List MinIO objects
```

### Testing
```bash
make test       # Run test suite
make test-cov   # Run tests with coverage
make lint       # Check code quality
make ci         # Run all CI checks (test + lint)
```

## Pipeline Steps (Individual)

```bash
make ingest     # Step 1: API → MinIO
make transform  # Step 2: MinIO → PostgreSQL
make validate   # Step 3: Data quality checks
make dbt-run    # Step 4: dbt transformations
make ml         # Step 5: ML model training
```

Or run all at once:
```bash
make pipeline   # Runs all 5 steps in order
```

##  Database Operations

```bash
make db-shell   # Open PostgreSQL interactive shell
make db-query   # Quick data check (row counts)
make db-reset   # ⚠️  Delete all data (destructive!)
make backup     # Create database backup
make restore FILE=backups/db_backup_20260201_120000.sql  # Restore
```

##  Open Web UIs

```bash
make monitor    # Open Grafana (localhost:3000)
make mlflow-ui  # Open MLflow (localhost:5000)
make minio-ui   # Open MinIO Console (localhost:9001)
```

##  Advanced Commands

```bash
make restart        # Restart all services
make clean          # ⚠️  Remove all data and volumes
make dev-shell      # Open bash in pipeline container
make format         # Format Python code
make check          # Full system check (health + data)
make demo           # Complete demo workflow
```

##  Ansible Orchestration

### Installation
```bash
pip install ansible
# or: brew install ansible
```

### Ansible Commands
```bash
make ansible-check    # Verify Ansible is installed
make ansible-health   # Health check via Ansible
make ansible-setup    # Complete setup with Ansible
make ansible-start    # Start services via Ansible
make ansible-pipeline # Run pipeline via Ansible
make ansible-verify   # Verify data via Ansible
make ansible-backup   # Create backup via Ansible
make ansible-stop     # Stop services via Ansible
make ansible-all      # Complete workflow (setup → pipeline)
```

### Direct Ansible Usage
```bash
cd ansible

# Run complete workflow
ansible-playbook platform.yml --tags setup,start,pipeline

# Individual operations
ansible-playbook platform.yml --tags health
ansible-playbook platform.yml --tags verify
ansible-playbook platform.yml --tags backup

# See ansible/README.md for more details
```

##  Service Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3000 | admin / admin |
| **MLflow** | http://localhost:5000 | (none) |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin |
| **PostgreSQL** | localhost:5432 | dataplatform / changeme123 |
| **Loki API** | http://localhost:3100 | (none) |

##  Pro Tips

1. **Always check health first**: Run `make health` after `make up`
2. **View logs while debugging**: Use `make logs-tail` in a separate terminal
3. **Quick data check**: Run `make db-query` to see row counts
4. **Backup before reset**: Use `make backup` before `make db-reset`
5. **Run CI locally**: Use `make ci` before committing code
6. **Get help anytime**: Run `make help` to see all commands

##  Troubleshooting

### Services won't start
```bash
docker info                    # Check Docker is running
make status                    # Check what's running
make logs-tail                 # See error messages
make down && make up          # Fresh restart
```

### Pipeline fails
```bash
make health                    # Check service health
make logs-pipeline            # View pipeline logs
make db-query                 # Check data state
make db-reset && make pipeline  # Clean restart
```

### Database issues
```bash
make db-shell                 # Open PostgreSQL shell
# Then run: \dt *.*           # List all tables
# Or: SELECT * FROM raw.commits LIMIT 5;
```

### Reset everything
```bash
make clean                    # ⚠️  Deletes ALL data
make setup                    # Rebuild
make up                       # Start fresh
```

##  Learn More

- Full documentation: `cat ORCHESTRATION.md`
- Compare approaches: `cat ORCHESTRATION_COMPARISON.md`
- Project overview: `cat README.md`

---

**Remember**: Use `make help` anytime to see available commands!
