# Design Appendix: Production Architecture & Operations

**Document Version:** 1.0  
**Last Updated:** February 1, 2026  
**Author:** Data & ML Platform Team  
**Status:** Technical Design Document

---

## Executive Overview

This appendix provides detailed technical specifications for production deployment, CI/CD automation, security hardening, and MLOps operations for the Data & ML Platform. It serves as the authoritative reference for platform engineers, DevOps teams, and security architects.

---

## 1. Platform Architecture

### 1.1 Kubernetes Deployment Approach

**Deployment Model:** Multi-tenant, namespace-isolated architecture with GitOps-driven continuous deployment.

#### Cluster Architecture

```
[DIAGRAM PLACEHOLDER: Kubernetes Cluster Architecture]

Diagram Description (for external tool):
- Title: "Production Kubernetes Cluster Architecture"
- 3 Node Pools:
  1. System Pool (2 nodes, 4 vCPU, 16GB RAM) - kube-system, monitoring
  2. Data Pool (3 nodes, 8 vCPU, 32GB RAM) - PostgreSQL, MinIO, stateful workloads
  3. Compute Pool (5-20 nodes, autoscaling, 4 vCPU, 16GB RAM) - Pipeline workers, dbt, MLflow
- Network Policy between pools
- Persistent Volume Claims (PVC) for data storage
- Ingress Controller (NGINX) for external access
- Service Mesh (Istio) for internal communication
```

#### Namespace Strategy

| Namespace | Purpose | Resource Limits | Network Policy |
|-----------|---------|-----------------|----------------|
| `platform-prod` | Production workloads | CPU: 32 cores, Mem: 128GB | Restricted egress |
| `platform-staging` | Pre-production testing | CPU: 16 cores, Mem: 64GB | Internet access |
| `platform-dev` | Development environment | CPU: 8 cores, Mem: 32GB | Full access |
| `platform-monitoring` | Observability stack | CPU: 8 cores, Mem: 32GB | All namespaces |
| `platform-mlops` | MLflow, model registry | CPU: 16 cores, Mem: 64GB | Restricted |

#### Helm Chart Structure

```yaml
# values.yaml - Environment-specific configuration
environment: production

postgresql:
  enabled: true
  replicaCount: 3
  persistence:
    size: 500Gi
    storageClass: ssd-retain
  resources:
    requests:
      cpu: 2000m
      memory: 8Gi
    limits:
      cpu: 4000m
      memory: 16Gi
  backup:
    enabled: true
    schedule: "0 2 * * *"  # Daily at 2 AM
    retention: 30

minio:
  enabled: true
  mode: distributed
  replicas: 4
  persistence:
    size: 1Ti
    storageClass: ssd-retain
  resources:
    requests:
      cpu: 1000m
      memory: 4Gi

pipeline:
  enabled: true
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 20
    targetCPUUtilizationPercentage: 70
  image:
    repository: registry.company.io/data-platform/pipeline
    tag: "{{ .Values.imageTag }}"
    pullPolicy: Always
  resources:
    requests:
      cpu: 500m
      memory: 2Gi
    limits:
      cpu: 2000m
      memory: 8Gi

mlflow:
  enabled: true
  replicaCount: 2
  persistence:
    size: 100Gi
  backendStore: "postgresql://mlflow:${MLFLOW_DB_PASSWORD}@postgres:5432/mlflow"
  artifactStore: "s3://mlflow-artifacts"

grafana:
  enabled: true
  persistence:
    enabled: true
    size: 10Gi
  ingress:
    enabled: true
    hostname: grafana.company.io
    tls:
      enabled: true
      secretName: grafana-tls

dbt:
  enabled: true
  schedule: "0 */6 * * *"  # Every 6 hours
  resources:
    requests:
      cpu: 1000m
      memory: 4Gi
```

#### Deployment Commands

```bash
# Production deployment
helm upgrade --install data-platform ./helm/data-platform \
  --namespace platform-prod \
  --values values-prod.yaml \
  --set imageTag=${GIT_SHA} \
  --wait --timeout 10m

# Rollback to previous version
helm rollback data-platform -n platform-prod

# View deployment status
kubectl get pods -n platform-prod -w
```

### 1.2 Environment Separation

**Strategy:** Complete isolation with progressive promotion through environments.

```
[DIAGRAM PLACEHOLDER: Environment Promotion Flow]

Diagram Description (for external tool):
- Title: "Environment Promotion Pipeline"
- 4 Environments in sequence:
  1. Development (dev) - Feature branches, rapid iteration
  2. Integration (int) - Integration testing, PR validation
  3. Staging (staging) - Production mirror, pre-release testing
  4. Production (prod) - Live customer workloads
- Arrows showing promotion gates between environments
- Each environment has: Git branch, Database, K8s namespace, Domain
- Automated promotion: dev → int
- Manual approval: int → staging → prod
```

#### Environment Configuration Matrix

| Aspect | Development | Staging | Production |
|--------|-------------|---------|------------|
| **Git Branch** | `feature/*`, `dev` | `main` | `release/*`, `main` |
| **Kubernetes Namespace** | `platform-dev` | `platform-staging` | `platform-prod` |
| **Database** | Shared dev PostgreSQL | Staging PostgreSQL | Production HA cluster (3 replicas) |
| **Object Storage** | MinIO single node | MinIO 2-node | S3 or MinIO 4-node |
| **Domain** | `dev.internal.company.io` | `staging.company.io` | `app.company.io` |
| **Secrets** | Plaintext (dev only) | Sealed Secrets | Sealed Secrets + KMS |
| **Monitoring** | Basic logs | Full observability | Full + alerting + PagerDuty |
| **Data Refresh** | Weekly snapshot | Daily from prod | Live data |
| **Resource Limits** | 25% of prod | 50% of prod | Full allocation |
| **SLA** | None | 95% uptime | 99.9% uptime |
| **Backup Retention** | None | 7 days | 30 days |
| **Deployment Frequency** | On every commit | Daily | Weekly (Tue/Thu) |

#### Network Isolation

```yaml
# NetworkPolicy: Production isolation
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: prod-isolation
  namespace: platform-prod
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # Only allow traffic from ingress controller
    - from:
      - namespaceSelector:
          matchLabels:
            name: ingress-nginx
  egress:
    # Allow DNS
    - to:
      - namespaceSelector:
          matchLabels:
            name: kube-system
      ports:
        - protocol: UDP
          port: 53
    # Allow PostgreSQL
    - to:
      - podSelector:
          matchLabels:
            app: postgresql
      ports:
        - protocol: TCP
          port: 5432
    # Block all other egress (no internet access)
```

---

## 2. CI/CD & Automation

### 2.1 CI/CD Pipeline Architecture

**Toolchain:** GitHub Actions → Docker Registry → ArgoCD → Kubernetes

```
[DIAGRAM PLACEHOLDER: CI/CD Pipeline Flow]

Diagram Description (for external tool):
- Title: "End-to-End CI/CD Pipeline"
- Stages (left to right):
  1. Code Commit (GitHub) → Triggers webhook
  2. CI Stage (GitHub Actions):
     - Lint (flake8, pylint)
     - Unit Tests (pytest)
     - Integration Tests (docker-compose)
     - Security Scan (Trivy, Bandit)
     - Build Docker Image
     - Push to Registry (tag: git-sha)
  3. CD Stage (ArgoCD):
     - Update manifest in GitOps repo
     - ArgoCD detects change
     - Deploy to dev (automatic)
     - Deploy to staging (manual approval)
     - Deploy to prod (manual approval + change window)
  4. Post-Deployment:
     - Health checks (readiness probes)
     - Smoke tests (API endpoints)
     - Rollback if failed
- Color coding: Green for automated, Yellow for approval gates
```

### 2.2 GitHub Actions Workflow

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, dev, 'feature/*']
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # ===== STAGE 1: Code Quality =====
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run flake8
        run: |
          pip install flake8
          flake8 pipeline/src --count --select=E9,F63,F7,F82 --show-source --statistics
          flake8 pipeline/src --count --exit-zero --max-complexity=10 --max-line-length=127

  # ===== STAGE 2: Testing =====
  test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v3
      
      - name: Run unit tests
        run: |
          docker compose run --rm pipeline pytest /app/tests/ -v --cov=/app/src --cov-report=xml
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true

  integration-test:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v3
      
      - name: Start services
        run: docker compose up -d postgres minio mlflow
      
      - name: Wait for services
        run: sleep 30
      
      - name: Run integration tests
        run: docker compose run --rm pipeline pytest /app/tests/integration/ -v
      
      - name: Cleanup
        run: docker compose down -v

  # ===== STAGE 3: Security Scanning =====
  security:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Run Bandit security linter
        run: |
          pip install bandit
          bandit -r pipeline/src -f json -o bandit-report.json || true
      
      - name: Upload SARIF to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  # ===== STAGE 4: Build & Push =====
  build:
    runs-on: ubuntu-latest
    needs: [test, integration-test, security]
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/dev'
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Log in to Container Registry
        uses: docker/login-action@v2
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix={{branch}}-
            type=ref,event=branch
            type=semver,pattern={{version}}
      
      - name: Build and push Docker image
        uses: docker/build-push-action@v4
        with:
          context: ./pipeline
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ===== STAGE 5: Deploy to Dev =====
  deploy-dev:
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/dev'
    steps:
      - name: Update GitOps repository
        run: |
          git clone https://${{ secrets.GITOPS_TOKEN }}@github.com/company/gitops-repo.git
          cd gitops-repo/environments/dev
          yq eval -i '.pipeline.image.tag = "${{ needs.build.outputs.image-tag }}"' values.yaml
          git add .
          git commit -m "Deploy ${{ github.sha }} to dev"
          git push

  # ===== STAGE 6: Deploy to Staging (Manual Approval) =====
  deploy-staging:
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    environment:
      name: staging
      url: https://staging.company.io
    steps:
      - name: Update GitOps repository
        run: |
          git clone https://${{ secrets.GITOPS_TOKEN }}@github.com/company/gitops-repo.git
          cd gitops-repo/environments/staging
          yq eval -i '.pipeline.image.tag = "${{ needs.build.outputs.image-tag }}"' values.yaml
          git add .
          git commit -m "Deploy ${{ github.sha }} to staging"
          git push

  # ===== STAGE 7: Deploy to Production (Manual Approval + Change Window) =====
  deploy-prod:
    runs-on: ubuntu-latest
    needs: [build, deploy-staging]
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://app.company.io
    steps:
      - name: Check change window
        run: |
          # Only allow deployments Tue/Thu 10am-2pm UTC
          DAY=$(date +%u)  # 1=Mon, 2=Tue, ..., 7=Sun
          HOUR=$(date +%H)
          if [[ "$DAY" != "2" && "$DAY" != "4" ]] || [[ "$HOUR" -lt "10" || "$HOUR" -ge "14" ]]; then
            echo "❌ Outside change window (Tue/Thu 10am-2pm UTC)"
            exit 1
          fi
      
      - name: Create deployment issue
        uses: actions/github-script@v6
        with:
          script: |
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `Production Deployment: ${context.sha}`,
              body: `Deploying commit ${context.sha} to production`,
              labels: ['deployment', 'production']
            })
      
      - name: Update GitOps repository
        run: |
          git clone https://${{ secrets.GITOPS_TOKEN }}@github.com/company/gitops-repo.git
          cd gitops-repo/environments/prod
          yq eval -i '.pipeline.image.tag = "${{ needs.build.outputs.image-tag }}"' values.yaml
          git add .
          git commit -m "Deploy ${{ github.sha }} to production"
          git push
      
      - name: Wait for deployment
        run: sleep 60
      
      - name: Run smoke tests
        run: |
          curl -f https://app.company.io/health || exit 1
          curl -f https://app.company.io/api/v1/status || exit 1
      
      - name: Notify Slack
        if: always()
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "🚀 Production deployment ${{ job.status }}",
              "commit": "${{ github.sha }}",
              "author": "${{ github.actor }}"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### 2.3 Testing & Promotion Strategy

#### Test Pyramid

```
[DIAGRAM PLACEHOLDER: Test Pyramid]

Diagram Description (for external tool):
- Title: "Testing Strategy Pyramid"
- 4 layers (bottom to top):
  1. Unit Tests (70% coverage) - Fast, isolated, run on every commit
     Examples: test_transformation.py, test_validation.py
  2. Integration Tests (20% coverage) - API integration, DB queries
     Examples: test_postgres_connection.py, test_minio_upload.py
  3. End-to-End Tests (8% coverage) - Full pipeline execution
     Examples: test_complete_pipeline.py
  4. Manual Testing (2% coverage) - UI testing, edge cases
     Examples: Grafana dashboard validation
- Execution time increases going up (10s → 5min → 30min → hours)
```

#### Promotion Gates

| Gate | Environment | Automated Checks | Manual Approval | Rollback Time |
|------|-------------|-----------------|-----------------|---------------|
| **Gate 1** | dev → int | • All tests pass<br>• Code coverage ≥70%<br>• No security vulnerabilities | ❌ Automatic | 30 seconds |
| **Gate 2** | int → staging | • Integration tests pass<br>• Performance benchmarks<br>• No regression | ✅ Tech Lead approval | 2 minutes |
| **Gate 3** | staging → prod | • Smoke tests pass<br>• Load tests pass<br>• Security sign-off<br>• Change ticket approved | ✅ Platform Lead + QA<br>✅ Change Advisory Board | 5 minutes |

#### Safe Deployment Patterns

**Blue-Green Deployment:**
```yaml
# Deploy new version (Green) alongside current (Blue)
apiVersion: v1
kind: Service
metadata:
  name: pipeline-service
spec:
  selector:
    app: pipeline
    version: blue  # Switch to 'green' after validation
```

**Canary Deployment:**
```yaml
# Istio VirtualService for gradual rollout
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: pipeline-canary
spec:
  http:
    - match:
      - headers:
          x-canary:
            exact: "true"
      route:
        - destination:
            host: pipeline
            subset: v2
          weight: 10  # 10% traffic to new version
        - destination:
            host: pipeline
            subset: v1
          weight: 90  # 90% traffic to stable version
```

---

## 3. Security

### 3.1 Secrets Management

**Strategy:** Layered secrets management with encryption at rest and in transit.

```
[DIAGRAM PLACEHOLDER: Secrets Management Architecture]

Diagram Description (for external tool):
- Title: "Secrets Management Flow"
- Components (left to right):
  1. Developer → Sealed Secrets CLI → Encrypted secret (Git)
  2. Git → ArgoCD → Sealed Secrets Controller (K8s)
  3. Controller → Decrypts → Kubernetes Secret (memory only)
  4. Secret → Mounted as volume → Pod (application)
  5. AWS KMS or HashiCorp Vault as external secret store
- Show encryption symbols at each stage
- Highlight: Secrets never stored unencrypted in Git
```

#### Implementation with Sealed Secrets

```bash
# 1. Install Sealed Secrets controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# 2. Install kubeseal CLI
brew install kubeseal

# 3. Create and seal a secret
echo -n 'changeme123' | kubectl create secret generic postgres-password \
  --dry-run=client \
  --from-file=password=/dev/stdin \
  -o yaml | \
  kubeseal -o yaml > sealed-postgres-password.yaml

# 4. Commit sealed secret to Git (safe!)
git add sealed-postgres-password.yaml
git commit -m "Add sealed PostgreSQL password"
git push

# 5. Apply to cluster (controller auto-decrypts)
kubectl apply -f sealed-postgres-password.yaml -n platform-prod
```

#### Secrets Rotation Policy

| Secret Type | Rotation Frequency | Automation | Notification |
|-------------|-------------------|------------|--------------|
| Database passwords | 90 days | Automated via CronJob | 7 days before expiry |
| API keys (external) | 180 days | Manual | 14 days before expiry |
| TLS certificates | 365 days | Let's Encrypt (auto) | 30 days before expiry |
| Service accounts | 60 days | Automated | 7 days before expiry |
| JWT signing keys | 30 days | Automated | No notification |

### 3.2 Encryption

**Encryption Strategy:**

1. **Data at Rest:**
   - PostgreSQL: Transparent Data Encryption (TDE) with AES-256
   - MinIO/S3: Server-side encryption (SSE-KMS)
   - Kubernetes Secrets: Encrypted with KMS provider
   - Persistent Volumes: LUKS encryption

2. **Data in Transit:**
   - All HTTP traffic: TLS 1.3 only
   - Inter-service communication: mTLS via Istio service mesh
   - Database connections: SSL/TLS enforced

```yaml
# PostgreSQL with TLS
postgresql:
  ssl:
    enabled: true
    certificatesSecret: postgres-tls
    certFilename: tls.crt
    keyFilename: tls.key
    caFilename: ca.crt
  postgresqlParameters:
    ssl: "on"
    ssl_ciphers: "HIGH:!aNULL:!MD5"
    ssl_min_protocol_version: "TLSv1.3"
```

### 3.3 Access Control

#### RBAC (Role-Based Access Control)

```yaml
# roles.yaml - Kubernetes RBAC
---
# Platform Admin (Full access)
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: platform-admin
  namespace: platform-prod
rules:
  - apiGroups: ["*"]
    resources: ["*"]
    verbs: ["*"]

---
# Data Engineer (Deploy, view logs, exec)
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: data-engineer
  namespace: platform-prod
rules:
  - apiGroups: ["apps", "batch"]
    resources: ["deployments", "jobs", "cronjobs"]
    verbs: ["get", "list", "create", "update", "patch"]
  - apiGroups: [""]
    resources: ["pods", "pods/log"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods/exec"]
    verbs: ["create"]

---
# Data Analyst (Read-only)
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: data-analyst
  namespace: platform-prod
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/log", "services"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments", "statefulsets"]
    verbs: ["get", "list"]

---
# CI/CD Service Account (Deploy only)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: argocd-deployer
  namespace: platform-prod
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: deployer
  namespace: platform-prod
rules:
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "update", "patch"]
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list"]
```

#### Database Access Control

```sql
-- Role hierarchy
CREATE ROLE platform_admin WITH SUPERUSER;
CREATE ROLE data_engineer WITH CREATEDB;
CREATE ROLE data_analyst;
CREATE ROLE pipeline_service;
CREATE ROLE mlflow_service;
CREATE ROLE dbt_service;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE dataplatform TO data_engineer;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO data_analyst;
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA raw TO pipeline_service;
GRANT ALL ON SCHEMA analytics TO dbt_service;

-- Row-level security (RLS)
ALTER TABLE analytics.user_data ENABLE ROW LEVEL SECURITY;
CREATE POLICY analyst_policy ON analytics.user_data
  FOR SELECT
  TO data_analyst
  USING (department = current_setting('app.current_department'));
```

#### Audit Logging

```yaml
# Kubernetes audit policy
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  # Log all secret access
  - level: RequestResponse
    resources:
      - group: ""
        resources: ["secrets"]
  
  # Log all RBAC changes
  - level: RequestResponse
    verbs: ["create", "update", "patch", "delete"]
    resources:
      - group: "rbac.authorization.k8s.io"
  
  # Log pod exec (shell access)
  - level: Request
    verbs: ["create"]
    resources:
      - group: ""
        resources: ["pods/exec"]
```

---

## 4. MLOps

### 4.1 Model Versioning

**Semantic Versioning for ML Models:**

```
v{major}.{minor}.{patch}-{stage}

Example: v2.3.1-production
         │ │ │   └─ stage (dev, staging, production)
         │ │ └───── patch (bug fixes, no retraining)
         │ └─────── minor (new features, retrained model)
         └───────── major (new architecture, breaking changes)
```

#### MLflow Model Registry Workflow

```python
# model_registry.py - Model versioning automation
import mlflow
from mlflow.tracking import MlflowClient

def register_model(run_id, model_name, tags=None):
    """Register a trained model to MLflow Model Registry"""
    client = MlflowClient()
    
    # Register model
    model_uri = f"runs:/{run_id}/model"
    model_details = mlflow.register_model(
        model_uri=model_uri,
        name=model_name,
        tags={
            "git_commit": os.getenv("GIT_SHA"),
            "git_branch": os.getenv("GIT_BRANCH"),
            "training_date": datetime.now().isoformat(),
            "dataset_version": "v2026.02",
            "framework": "scikit-learn",
            "framework_version": sklearn.__version__,
            "python_version": platform.python_version(),
            **(tags or {})
        }
    )
    
    version = model_details.version
    print(f"✅ Model registered: {model_name} v{version}")
    
    # Add model description
    client.update_model_version(
        name=model_name,
        version=version,
        description=f"""
        Commit Classifier Model v{version}
        
        Training Metrics:
        - Accuracy: 0.87
        - F1 Score: 0.85
        - Training samples: 10,000
        
        Features: message_length, has_issue_ref, hour_of_day, etc.
        Target: is_merge_commit (binary classification)
        """
    )
    
    return model_details

def promote_model(model_name, version, stage):
    """Promote model to a new stage (Staging or Production)"""
    client = MlflowClient()
    
    # Validation checks before promotion
    if stage == "Production":
        # Check model performance
        run_id = client.get_model_version(model_name, version).run_id
        run = client.get_run(run_id)
        f1_score = run.data.metrics.get("f1_score", 0)
        
        if f1_score < 0.80:
            raise ValueError(f"❌ F1 score {f1_score} below threshold 0.80")
        
        # Check for approval
        approval = input(f"Promote {model_name} v{version} to Production? (yes/no): ")
        if approval.lower() != "yes":
            print("❌ Promotion cancelled")
            return
    
    # Archive existing production models
    if stage == "Production":
        production_models = client.get_latest_versions(model_name, stages=["Production"])
        for prod_model in production_models:
            client.transition_model_version_stage(
                name=model_name,
                version=prod_model.version,
                stage="Archived"
            )
    
    # Promote new model
    client.transition_model_version_stage(
        name=model_name,
        version=version,
        stage=stage,
        archive_existing_versions=(stage == "Production")
    )
    
    print(f"✅ Model {model_name} v{version} promoted to {stage}")
    
    # Send notification
    notify_slack(f"🚀 Model {model_name} v{version} promoted to {stage}")
```

### 4.2 Model Deployment

```
[DIAGRAM PLACEHOLDER: Model Deployment Pipeline]

Diagram Description (for external tool):
- Title: "ML Model Deployment Workflow"
- Stages:
  1. Training (MLflow) → Model artifacts saved → S3/MinIO
  2. Registration → MLflow Model Registry → Version tagged
  3. Validation Gate:
     - Performance metrics check (F1 > 0.80)
     - Schema validation (input/output)
     - Integration tests pass
  4. Staging Deployment:
     - Deploy to staging namespace
     - Shadow mode (predictions logged, not used)
     - A/B test with 10% traffic
  5. Production Deployment:
     - Manual approval
     - Blue-green deployment
     - 100% traffic cutover after validation
  6. Monitoring:
     - Prediction latency
     - Drift detection
     - Performance degradation alerts
- Color code: Green for automated, Red for approval gates
```

#### Deployment Strategies

**Option 1: Batch Inference (Current)**
```yaml
# batch-inference-job.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: batch-inference
  namespace: platform-prod
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: inference
            image: ghcr.io/company/ml-inference:latest
            env:
              - name: MODEL_URI
                value: "models:/commit-classifier/Production"
              - name: MLFLOW_TRACKING_URI
                value: "http://mlflow:5000"
            command:
              - python
              - /app/batch_inference.py
          restartPolicy: OnFailure
```

**Option 2: Real-Time API Serving**
```yaml
# model-serving.yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: commit-classifier
  namespace: platform-mlops
spec:
  predictor:
    serviceAccountName: mlflow-sa
    mlflow:
      storageUri: "models:/commit-classifier/Production"
      protocolVersion: v2
      runtime: kserve-mlserver
    resources:
      requests:
        cpu: 500m
        memory: 2Gi
      limits:
        cpu: 2000m
        memory: 4Gi
    autoscaling:
      minReplicas: 2
      maxReplicas: 10
      target: 70  # CPU utilization
```

### 4.3 Model Monitoring

**Metrics to Track:**

| Metric Category | Metrics | Alert Threshold | Tool |
|-----------------|---------|-----------------|------|
| **Performance** | Accuracy, F1, Precision, Recall | Drop >5% | MLflow |
| **Data Quality** | Null rate, schema violations | >1% | Great Expectations |
| **Data Drift** | Feature distribution shift | PSI >0.2 | Evidently AI |
| **Prediction Drift** | Output distribution change | KL Divergence >0.1 | Alibi Detect |
| **System Metrics** | Latency (p95), throughput, errors | p95 >500ms, errors >1% | Prometheus |
| **Business Metrics** | Conversion rate, user engagement | Drop >10% | Custom dashboard |

#### Monitoring Implementation

```python
# model_monitoring.py
import evidently
from evidently.metrics import DataDriftTable, DatasetDriftMetric
from evidently.report import Report
import mlflow

def monitor_model_drift(reference_data, current_data, model_name):
    """Detect data drift between reference and current data"""
    
    # Create drift report
    report = Report(metrics=[
        DatasetDriftMetric(),
        DataDriftTable()
    ])
    
    report.run(
        reference_data=reference_data,
        current_data=current_data
    )
    
    # Extract drift metrics
    drift_results = report.as_dict()
    dataset_drift = drift_results['metrics'][0]['result']['dataset_drift']
    
    # Log to MLflow
    with mlflow.start_run(run_name="drift_monitoring"):
        mlflow.log_metric("dataset_drift_detected", int(dataset_drift))
        mlflow.log_dict(drift_results, "drift_report.json")
    
    # Alert if drift detected
    if dataset_drift:
        alert_message = f"""
        ⚠️ DATA DRIFT DETECTED
        Model: {model_name}
        Recommendation: Review data quality and consider model retraining
        """
        send_alert(alert_message, severity="warning")
        
    return drift_results

def monitor_prediction_quality(predictions, actuals, model_name):
    """Monitor model performance on recent predictions"""
    from sklearn.metrics import f1_score, accuracy_score
    
    # Calculate metrics
    f1 = f1_score(actuals, predictions, average='weighted')
    accuracy = accuracy_score(actuals, predictions)
    
    # Log to MLflow
    with mlflow.start_run(run_name="production_monitoring"):
        mlflow.log_metric("production_f1_score", f1)
        mlflow.log_metric("production_accuracy", accuracy)
    
    # Check for degradation
    baseline_f1 = 0.85
    if f1 < baseline_f1 * 0.95:  # 5% drop
        alert_message = f"""
        🚨 MODEL PERFORMANCE DEGRADATION
        Model: {model_name}
        Current F1: {f1:.3f}
        Baseline F1: {baseline_f1:.3f}
        Drop: {(baseline_f1 - f1) / baseline_f1 * 100:.1f}%
        
        Action Required: Investigate and consider rollback or retraining
        """
        send_alert(alert_message, severity="critical")
```

### 4.4 Model Rollback

**Rollback Strategies:**

```
[DIAGRAM PLACEHOLDER: Model Rollback Decision Tree]

Diagram Description (for external tool):
- Title: "Model Rollback Decision Flow"
- Decision tree:
  1. Performance Alert Triggered
  2. Is it critical? (F1 drop >10% OR errors >5%)
     - YES → Immediate automatic rollback (< 5 min)
     - NO → Create incident ticket, investigate
  3. Rollback execution:
     - Transition previous model version to Production
     - Update inference service to use previous version
     - Verify rollback success (smoke tests)
     - Notify team
  4. Post-rollback:
     - Root cause analysis
     - Data quality investigation
     - Plan retraining or hotfix
- Include timing: Detection (2 min), Decision (1 min), Rollback (2 min), Verification (2 min)
```

#### Automated Rollback Script

```bash
#!/bin/bash
# rollback-model.sh - Emergency model rollback

set -e

MODEL_NAME=$1
REASON=${2:-"Performance degradation"}

echo "🔄 Initiating model rollback for: $MODEL_NAME"
echo "Reason: $REASON"

# 1. Get current production version
CURRENT_VERSION=$(python -c "
import mlflow
client = mlflow.tracking.MlflowClient()
models = client.get_latest_versions('$MODEL_NAME', stages=['Production'])
print(models[0].version if models else 'None')
")

echo "Current production version: $CURRENT_VERSION"

# 2. Find previous version
PREVIOUS_VERSION=$(python -c "
import mlflow
client = mlflow.tracking.MlflowClient()
versions = client.search_model_versions(f\"name='$MODEL_NAME'\")
versions = sorted(versions, key=lambda x: int(x.version), reverse=True)
for v in versions:
    if v.version != '$CURRENT_VERSION' and v.current_stage == 'Archived':
        print(v.version)
        break
")

if [ -z "$PREVIOUS_VERSION" ]; then
    echo "❌ No previous version found for rollback"
    exit 1
fi

echo "Rolling back to version: $PREVIOUS_VERSION"

# 3. Archive current version
python -c "
import mlflow
client = mlflow.tracking.MlflowClient()
client.transition_model_version_stage(
    name='$MODEL_NAME',
    version='$CURRENT_VERSION',
    stage='Archived'
)
"

# 4. Promote previous version to production
python -c "
import mlflow
client = mlflow.tracking.MlflowClient()
client.transition_model_version_stage(
    name='$MODEL_NAME',
    version='$PREVIOUS_VERSION',
    stage='Production'
)
"

# 5. Update Kubernetes deployment
kubectl set env deployment/model-serving \
    MODEL_VERSION=$PREVIOUS_VERSION \
    -n platform-mlops

# 6. Wait for rollout
kubectl rollout status deployment/model-serving -n platform-mlops --timeout=300s

# 7. Run smoke tests
echo "Running smoke tests..."
python smoke_test.py --model-name $MODEL_NAME --version $PREVIOUS_VERSION

# 8. Notify team
SLACK_WEBHOOK=${SLACK_WEBHOOK:-""}
if [ -n "$SLACK_WEBHOOK" ]; then
    curl -X POST $SLACK_WEBHOOK -H 'Content-Type: application/json' -d "{
        \"text\": \"⚠️ Model Rollback Completed\",
        \"attachments\": [{
            \"color\": \"warning\",
            \"fields\": [
                {\"title\": \"Model\", \"value\": \"$MODEL_NAME\", \"short\": true},
                {\"title\": \"From Version\", \"value\": \"$CURRENT_VERSION\", \"short\": true},
                {\"title\": \"To Version\", \"value\": \"$PREVIOUS_VERSION\", \"short\": true},
                {\"title\": \"Reason\", \"value\": \"$REASON\", \"short\": false}
            ]
        }]
    }"
fi

echo "✅ Rollback completed successfully"
echo "Current production version: $PREVIOUS_VERSION"
echo ""
echo "Next steps:"
echo "  1. Investigate root cause"
echo "  2. Fix issue in version $CURRENT_VERSION"
echo "  3. Retrain and redeploy when ready"
```

#### Rollback Testing

```python
# test_rollback.py - Chaos engineering for rollback
import pytest
import mlflow
from mlflow.tracking import MlflowClient

def test_model_rollback():
    """Test model rollback mechanism"""
    client = MlflowClient()
    model_name = "commit-classifier-test"
    
    # 1. Register two model versions
    v1 = mlflow.register_model("runs:/abc123/model", model_name)
    v2 = mlflow.register_model("runs:/def456/model", model_name)
    
    # 2. Promote v2 to production
    client.transition_model_version_stage(
        name=model_name, version=v2.version, stage="Production"
    )
    
    # 3. Simulate performance degradation
    # (In real scenario, monitoring system would detect this)
    
    # 4. Execute rollback
    client.transition_model_version_stage(
        name=model_name, version=v2.version, stage="Archived"
    )
    client.transition_model_version_stage(
        name=model_name, version=v1.version, stage="Production"
    )
    
    # 5. Verify rollback
    prod_models = client.get_latest_versions(model_name, stages=["Production"])
    assert len(prod_models) == 1
    assert prod_models[0].version == v1.version
    
    print("✅ Rollback test passed")
```

---

## Appendix: Tooling & References

### Required Tools

| Tool | Purpose | Version | Installation |
|------|---------|---------|--------------|
| kubectl | Kubernetes CLI | 1.28+ | `brew install kubectl` |
| helm | Kubernetes package manager | 3.12+ | `brew install helm` |
| kubeseal | Sealed Secrets CLI | 0.24+ | `brew install kubeseal` |
| argocd | GitOps CD CLI | 2.9+ | `brew install argocd` |
| mlflow | ML experiment tracking | 2.9+ | `pip install mlflow` |
| yq | YAML processor | 4.35+ | `brew install yq` |

### Key Configuration Files

- `/helm/data-platform/` - Helm chart for all services
- `/gitops/environments/` - Environment-specific values
- `/.github/workflows/ci-cd.yml` - CI/CD pipeline
- `/k8s/rbac/` - RBAC policies
- `/k8s/network-policies/` - Network isolation
- `/scripts/rollback-model.sh` - Model rollback automation

### Compliance & Standards

- **Security:** CIS Kubernetes Benchmark, NIST Cybersecurity Framework
- **Data Privacy:** GDPR, CCPA (if handling PII)
- **Audit:** SOC 2 Type II readiness
- **Monitoring:** SLO/SLI based on SRE principles (99.9% uptime target)

---

**Document Control:**
- Last Review: February 1, 2026
- Next Review: May 1, 2026 (Quarterly)
- Owner: Platform Engineering Team
- Approval: CTO Signature Required for Production Changes

---

*End of Design Appendix*
