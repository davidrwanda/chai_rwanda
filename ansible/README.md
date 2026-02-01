# Ansible Orchestration for Data Platform

This directory contains Ansible playbooks for automating the data platform lifecycle.

## 📋 Prerequisites

```bash
# Install Ansible (macOS)
brew install ansible

# Or using pip
pip install ansible

# Verify installation
ansible --version
```

## 🚀 Quick Start

```bash
# Navigate to ansible directory
cd ansible

# Run complete setup and pipeline
ansible-playbook platform.yml --tags setup,start,pipeline

# Or use from project root via Makefile
cd ..
make ansible-pipeline
```

## 📖 Available Tags

### Setup & Configuration
- `setup` - Initial setup (check dependencies, configure environment, build images)
- `check` - Check Docker and dependencies
- `config` - Configure environment (.env file)
- `build` - Build Docker images

### Service Management
- `start` - Start all services
- `services` - Manage services
- `health` - Health check all services
- `info` - Display service information
- `stop` - Stop all services

### Pipeline Execution
- `pipeline` - Run complete data pipeline (all 5 steps)
- `ingest` - Step 1: Data ingestion
- `transform` - Step 2: Data transformation
- `validate` - Step 3: Data validation
- `dbt` - Step 4: dbt transformations
- `ml` - Step 5: ML model training

### Data Management
- `verify` - Verify data in database
- `check` - Check row counts
- `backup` - Create database backup

### Cleanup
- `cleanup` - Stop services and cleanup (use with caution)
- `never` - Tag for dangerous operations (requires explicit specification)

## 🎯 Common Use Cases

### 1. Complete Setup and Pipeline

```bash
# Full workflow: setup → start → pipeline
ansible-playbook platform.yml --tags setup,start,pipeline
```

### 2. Start Services Only

```bash
# Start and health check
ansible-playbook platform.yml --tags start,health
```

### 3. Run Pipeline Only (assumes services are running)

```bash
# Run all pipeline steps
ansible-playbook platform.yml --tags pipeline

# Or individual steps
ansible-playbook platform.yml --tags ingest
ansible-playbook platform.yml --tags transform
ansible-playbook platform.yml --tags validate
ansible-playbook platform.yml --tags dbt
ansible-playbook platform.yml --tags ml
```

### 4. Verify Data

```bash
# Check database tables and row counts
ansible-playbook platform.yml --tags verify
```

### 5. Create Backup

```bash
# Backup database
ansible-playbook platform.yml --tags backup
```

### 6. Stop Services

```bash
# Graceful shutdown
ansible-playbook platform.yml --tags stop
```

### 7. Health Check

```bash
# Check all services
ansible-playbook platform.yml --tags health
```

## 🔧 Configuration

### Inventory (`inventory.ini`)
Defines target hosts. Currently configured for local execution:
```ini
[localhost]
127.0.0.1 ansible_connection=local
```

### Configuration (`ansible.cfg`)
Ansible behavior settings:
- Uses `inventory.ini` by default
- YAML output for better readability
- No host key checking for localhost

### Playbook Variables (`platform.yml`)
Key variables you can override:
```yaml
vars:
  project_dir: "{{ playbook_dir }}/.."
  services: [postgres, minio, mlflow, grafana, loki, promtail, pipeline, dbt]
  service_ports: { postgres: 5432, minio: 9000, ... }
```

## 📊 Example: Full Workflow

```bash
# 1. Initial setup
ansible-playbook platform.yml --tags setup

# 2. Start services
ansible-playbook platform.yml --tags start

# 3. Verify health
ansible-playbook platform.yml --tags health

# 4. Run pipeline
ansible-playbook platform.yml --tags pipeline

# 5. Verify data
ansible-playbook platform.yml --tags verify

# 6. Create backup
ansible-playbook platform.yml --tags backup

# 7. Stop services
ansible-playbook platform.yml --tags stop
```

## 🎨 Output Example

```yaml
TASK [Services - Display health check results] ********************************
ok: [127.0.0.1] => 
  msg:
  - '🏥 Health Check Results:'
  - '  PostgreSQL: ✓ Healthy'
  - '  MinIO:      ✓ Healthy'
  - '  MLflow:     ✓ Healthy'
  - '  Grafana:    ✓ Healthy'
  - '  Loki:       ✓ Healthy'

TASK [Pipeline - Display completion summary] **********************************
ok: [127.0.0.1] => 
  msg:
  - ╔════════════════════════════════════════════════════╗
  - ║    ✓ Pipeline Completed Successfully!             ║
  - ╚════════════════════════════════════════════════════╝
```

## 🔄 Comparison: Ansible vs Makefile

| Feature | Makefile | Ansible |
|---------|----------|---------|
| **Complexity** | Simple | Moderate |
| **Idempotency** | Manual | Built-in |
| **Error Handling** | Basic | Advanced |
| **Readability** | Good | Excellent |
| **Remote Execution** | No | Yes |
| **Conditional Logic** | Limited | Rich |
| **Best For** | Local dev | Multi-host/Production |

## 💡 Idempotency Features

Ansible playbook includes idempotent operations:

1. **Environment Setup**
   - Only creates `.env` if it doesn't exist (`force: no`)
   - Checks existing state before copying

2. **Service Health**
   - Retries with delay until services are healthy
   - Doesn't fail on first attempt

3. **Changed Detection**
   - Tasks marked `changed_when: false` for read operations
   - Accurate change reporting

4. **Error Recovery**
   - `block`/`rescue` for error handling
   - Continue or fail gracefully

## 🚨 Safety Features

### Protected Operations
```bash
# Dangerous operations require explicit tag
ansible-playbook platform.yml --tags cleanup,never
```

### Always Tags
```bash
# Some tasks always run (banners, info)
ansible-playbook platform.yml --tags setup
# Will also show "always" tagged tasks
```

## 🐛 Troubleshooting

### Ansible not found
```bash
# Install Ansible
pip install ansible

# Or on macOS
brew install ansible
```

### Playbook fails on health check
```bash
# Start services first
ansible-playbook platform.yml --tags start

# Wait a bit, then retry health check
ansible-playbook platform.yml --tags health
```

### Docker connection issues
```bash
# Ensure Docker is running
docker info

# Check project_dir variable
ansible-playbook platform.yml --tags check -v
```

### Permission issues
```bash
# Ansible runs locally, no sudo needed
# If backup fails, check directory permissions
mkdir -p ../backups
chmod 755 ../backups
```

## 📚 Learn More

- **Ansible Documentation**: https://docs.ansible.com/
- **Ansible Docker Modules**: https://docs.ansible.com/ansible/latest/collections/community/docker/
- **Best Practices**: https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html

## 🔗 Integration with Makefile

From project root:
```bash
# Makefile wraps Ansible commands
make ansible-setup
make ansible-start
make ansible-pipeline
make ansible-verify
make ansible-backup
make ansible-stop
```

See `../Makefile` for details.

---

**Remember**: Ansible provides powerful orchestration with idempotency and error handling, perfect for production deployments!
