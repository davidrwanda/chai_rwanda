# Data & ML Platform - Technical Assessment

[![Docker](https://img.shields.io/badge/Docker-Compose-blue)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.11-green)](https://www.python.org/)
[![dbt](https://img.shields.io/badge/dbt-1.7-orange)](https://www.getdbt.com/)
[![MLflow](https://img.shields.io/badge/MLflow-2.9-red)](https://mlflow.org/)

A production-ready, containerized data and ML platform demonstrating best practices in data engineering, platform engineering, data quality, and MLOps.

## 🏗️ Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                         Data Platform                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  GitHub API  ──► Ingestion ──► MinIO (Raw Storage)               │
│                     │                                             │
│                     ▼                                             │
│              Transformation ──► PostgreSQL (Warehouse)            │
│                     │                                             │
│                     ▼                                             │
│             Data Quality Validation                               │
│                     │                                             │
│                     ▼                                             │
│              dbt (Staging & Marts)                                │
│                     │                                             │
│                     ▼                                             │
│         ┌───────────┴────────────┐                                │
│         ▼                        ▼                                │
│    Analytics Models      ML Feature Engineering                  │
│                                  │                                │
│                                  ▼                                │
│                          Model Training (MLflow)                  │
│                                                                   │
│  ────────────────────────────────────────────────────────────    │
│                     Observability Layer                           │
│         Loki ◄── Promtail ──► Grafana (Dashboards)               │
└──────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker Desktop (20.10+) with Docker Compose
- 8GB RAM minimum (16GB recommended)
- 10GB free disk space

### Setup & Run

```bash
# 1. Clone and navigate to the project
cd "chai Rwanda"

# 2. Initial setup
make setup

# 3. Start all services
make up

# 4. Run the complete pipeline
make pipeline
```

That's it! The pipeline will execute all steps in order:
1. ✅ Data Ingestion
2. ✅ Data Transformation
3. ✅ Data Quality Validation
4. ✅ dbt Models
5. ✅ ML Model Training

### Alternative: Ansible Orchestration

For idempotent, production-ready orchestration:

```bash
# Install Ansible
pip install ansible

# Run complete workflow
make ansible-all

# Or individual steps
make ansible-setup
make ansible-start
make ansible-pipeline
make ansible-verify
```

See [ansible/README.md](ansible/README.md) for detailed Ansible usage.

### Access Services

Once running, access these services:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** (Logs & Dashboards) | http://localhost:3000 | admin / admin |
| **MLflow** (Experiment Tracking) | http://localhost:5000 | - |
| **MinIO Console** (Object Storage) | http://localhost:9001 | minioadmin / minioadmin |
| **PostgreSQL** | localhost:5432 | dataplatform / changeme123 |

## 📊 Verification Steps

### 1. Check All Services are Running

```bash
docker compose ps
```

All services should show status as "running" or "healthy".

### 2. View Pipeline Logs in Grafana

1. Open Grafana: http://localhost:3000
2. Login with `admin` / `admin`
3. Navigate to **Dashboards** → **Data Platform Logs**
4. View logs from all pipeline stages

**Example Log Queries:**

```logql
# View all pipeline logs
{container_name=~".*pipeline.*"}

# View only errors
{container_name=~".*pipeline.*"} |= "ERROR"

# View successful completions
{container_name=~".*pipeline.*"} |= "Completed Successfully"

# View data quality validation results
{container_name=~".*pipeline.*"} |= "Data Quality Validation"

# View dbt runs
{container_name=~".*dbt.*"} |= "Completed successfully"

# View ML training metrics
{container_name=~".*pipeline.*"} |= "Model Training Results"
```

### 3. Verify Data in PostgreSQL

```bash
# Connect to database
make db-shell

# Then run these queries:
```

```sql
-- Check raw data
SELECT COUNT(*) FROM raw.commits;
SELECT * FROM raw.commits LIMIT 5;

-- Check staging data
SELECT COUNT(*) FROM staging.stg_commits;

-- Check analytics mart
SELECT COUNT(*) FROM analytics.commit_metrics;
SELECT * FROM analytics.commit_metrics LIMIT 5;

-- Check ML features
SELECT COUNT(*) FROM analytics.ml_features;
```

### 4. Verify MLflow Experiments

1. Open MLflow: http://localhost:5000
2. Click on "commit-analysis" experiment
3. View run details including:
   - Model parameters
   - Training metrics (accuracy, precision, recall, F1)
   - Feature importance
   - Model artifacts

### 5. Verify MinIO Data Storage

1. Open MinIO Console: http://localhost:9001
2. Login with `minioadmin` / `minioadmin`
3. Navigate to `raw-data` bucket
4. Verify files under `github-commits/YYYY-MM-DD/`

### 6. Run Tests

```bash
# Run test suite
make test

# Expected output:
# - Unit tests for ingestion module
# - Integration tests for pipeline
# - Data quality tests
```

## 📁 Project Structure

```
chai Rwanda/
├── .env.example              # Environment configuration template
├── .gitignore               # Git ignore patterns
├── docker-compose.yml       # Service orchestration
├── Makefile                # Automation commands
│
├── pipeline/               # Python data pipeline
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── src/
│   │   ├── ingestion.py      # Data ingestion from API to MinIO
│   │   ├── transformation.py # Data transformation & loading
│   │   ├── validation.py     # Data quality validation
│   │   └── ml_pipeline.py    # ML feature engineering & training
│   └── tests/
│       ├── test_ingestion.py    # Unit tests
│       └── test_integration.py  # Integration tests
│
├── dbt/                    # dbt transformation models
│   ├── Dockerfile
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       ├── sources.yml          # Source definitions
│       ├── staging/
│       │   ├── stg_commits.sql  # Staging model
│       │   └── staging.yml      # Staging tests
│       └── marts/
│           ├── commit_metrics.sql # Analytics mart
│           └── marts.yml          # Mart tests
│
├── mlflow/                 # MLflow tracking server
│   └── Dockerfile
│
├── monitoring/             # Observability stack
│   ├── loki-config.yaml        # Log aggregation config
│   ├── promtail-config.yaml    # Log collection config
│   └── grafana/
│       ├── datasources/
│       │   └── loki.yml
│       └── dashboards/
│           ├── dashboard-provider.yml
│           └── platform-logs.json
│
├── sql/                    # Database initialization
│   └── init/
│       └── 01_init.sql
│
├── data/                   # Local data storage
│   ├── raw/
│   └── processed/
│
├── models/                 # Trained ML models
│
├── README.md              # This file
├── REPORT.md              # Detailed design decisions & analysis
└── DESIGN_APPENDIX.md     # Architecture & scaling strategies
```

## 🔄 Pipeline Components

### 1. Data Ingestion (`pipeline/src/ingestion.py`)

**Purpose:** Fetch data from GitHub API and store in MinIO object storage.

**Features:**
- Fetches commit data from GitHub REST API
- Organizes data by source and date: `github-commits/YYYY-MM-DD/HH-MM-SS.json`
- Stores raw JSON in MinIO (S3-compatible)
- Comprehensive logging
- Error handling and retries

**Run manually:**
```bash
make ingest
```

### 2. Data Transformation (`pipeline/src/transformation.py`)

**Purpose:** Transform raw data and load into PostgreSQL warehouse.

**Transformations:**
- Flatten nested JSON structures
- Data cleaning (nulls, whitespace, type conversions)
- Field normalization (lowercase emails, trim strings)
- Derived fields (message length, merge flag, temporal features)
- Add metadata (loaded_at, source)

**Run manually:**
```bash
make transform
```

### 3. Data Quality Validation (`pipeline/src/validation.py`)

**Purpose:** Ensure data quality through comprehensive checks.

**Validations Implemented:**
1. **Schema Validation**
   - Required columns present
   - Correct data types
   - SHA format validation (40-char hex)

2. **Null Checks**
   - Critical columns have <5% nulls
   - Reports null percentages

3. **Duplicate Detection**
   - Checks for duplicate commit SHAs
   - Reports duplicate samples

4. **Row Count Validation**
   - Ensures minimum row threshold
   - Validates data completeness

**Failure Handling:**
- Critical failures stop the pipeline
- Warnings logged but allow continuation
- Comprehensive validation report generated

**Run manually:**
```bash
make validate
```

### 4. dbt Transformations (`dbt/models/`)

**Purpose:** Build analytics-ready data models.

**Models:**
- **Source** (`sources.yml`): Raw commits table definition with tests
- **Staging** (`stg_commits.sql`): Cleaned and normalized data
- **Mart** (`commit_metrics.sql`): Analytics model with:
  - Author-level aggregations
  - Temporal patterns
  - Engagement metrics
  - Categorizations

**Tests:**
- Unique and not-null constraints
- Custom data quality checks
- Referential integrity

**Run manually:**
```bash
make dbt-run
```

### 5. ML Pipeline (`pipeline/src/ml_pipeline.py`)

**Purpose:** Feature engineering and model training with MLflow tracking.

**Features:**
- **Feature Engineering:**
  - Text features (message length, word count, references)
  - Temporal features (hour, day of week, business hours)
  - Author features (domain, company email, commit count)
  - Engagement features (comments, merge status)

- **Model Training:**
  - Binary classification (merge commit prediction)
  - RandomForest classifier
  - Train/test split with stratification
  - Feature scaling with StandardScaler

- **MLflow Tracking:**
  - Parameters logging
  - Metrics tracking (accuracy, precision, recall, F1)
  - Feature importance analysis
  - Model artifact storage
  - Experiment versioning

**Run manually:**
```bash
make ml
```

## 🛠️ Makefile Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make setup` | Initial project setup |
| `make up` | Start all services |
| `make down` | Stop all services |
| `make pipeline` | **Run complete pipeline** |
| `make logs` | View all service logs |
| `make test` | Run test suite |
| `make clean` | Clean data and stop services |
| `make health` | Check service health status |
| `make db-shell` | Connect to PostgreSQL |

## 🔍 Observability

### Centralized Logging with Loki + Promtail + Grafana

**Architecture:**
- **Promtail:** Collects logs from all Docker containers
- **Loki:** Stores and indexes log streams
- **Grafana:** Visualization and querying interface

**Pre-configured Dashboard:**
- Pipeline execution logs
- dbt transformation logs
- ML training logs
- Database logs
- Storage logs

**Benefits:**
- Single pane of glass for all logs
- Time-range filtering
- Log level filtering
- Real-time streaming
- Historical analysis

## 🧪 Testing

### Unit Tests

Located in `pipeline/tests/test_ingestion.py`:
- Data ingestion module tests
- Mock external API calls
- Bucket creation logic
- Data organization validation

### Integration Tests

Located in `pipeline/tests/test_integration.py`:
- End-to-end pipeline validation
- Database connectivity
- Schema existence
- Data quality checks
- Table population verification

### Run Tests

```bash
# Run all tests with coverage
make test

# View detailed output
docker compose run --rm pipeline pytest /app/tests/ -v -s

# Run specific test file
docker compose run --rm pipeline pytest /app/tests/test_ingestion.py -v
```

## 🐛 Troubleshooting

### Services not starting

```bash
# Check Docker resources
docker system df

# Restart everything
make down
make clean
make setup
make up
```

### Pipeline failures

```bash
# View logs
make logs-pipeline

# Run individual steps
make ingest
make transform
make validate
make dbt-run
make ml
```

### Database connection issues

```bash
# Check PostgreSQL is ready
docker compose exec postgres pg_isready -U dataplatform

# View database logs
make logs-postgres
```

### MinIO connection issues

```bash
# Check MinIO health
curl http://localhost:9000/minio/health/live

# View MinIO logs
make logs-minio

# Recreate buckets
docker compose restart minio-init
```

## 📚 Additional Documentation

- **[REPORT.md](REPORT.md)**: Comprehensive design decisions, trade-offs, assumptions, scaling strategies, security approaches, and ML evolution

## 🎯 Key Features Demonstrated

✅ **Containerized Architecture**: All services in Docker with orchestration  
✅ **Data Pipeline**: Ingest → Transform → Validate → Model → ML  
✅ **Object Storage**: MinIO for raw data lake  
✅ **Data Warehouse**: PostgreSQL with schema organization  
✅ **Data Quality**: Multi-level validation with failure handling  
✅ **Transformation**: dbt with sources, staging, and marts  
✅ **ML/AI**: Feature engineering, model training, experiment tracking  
✅ **Orchestration**: Makefile-based workflow automation  
✅ **Observability**: Centralized logging (Loki + Promtail + Grafana)  
✅ **Testing**: Unit and integration test suites  
✅ **Documentation**: Comprehensive README, reports, and design docs  

## 🤖 AI Tools Used

This project was built with assistance from:
- **GitHub Copilot**: Code completion, boilerplate generation, test creation
- **Claude AI**: Architecture design, documentation, best practices review

The tools helped accelerate development while maintaining high code quality and following industry best practices.

## 📝 License

This project is created for assessment purposes only.

---

**Built with demonstrating production-ready data platform engineering**
