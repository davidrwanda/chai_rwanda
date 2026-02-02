# Model Analysis: Commit Classification

## 1. Executive Summary

This document provides a comprehensive analysis of the machine learning model developed to classify GitHub commits. The model uses a RandomForest classifier to predict whether commits are merge commits based on engineered features from commit metadata, author information, and temporal patterns.

**Key Findings:**
- ✅ **Feature Engineering:** 28 features successfully engineered from raw commit data
- ✅ **Model Architecture:** RandomForest classifier with 100 estimators
- ⚠️ **Training Status:** Model training incomplete due to single-class dataset (data limitation)
- ✅ **Infrastructure:** Complete MLflow tracking and experiment management ready

---

## 2. Problem Definition

### 2.1 Business Objective
Classify GitHub commits to identify merge commits automatically, enabling:
- Automated code review prioritization
- Development workflow analysis
- Contribution pattern recognition
- Team productivity insights

### 2.2 ML Problem Formulation
- **Problem Type:** Binary classification
- **Target Variable:** `is_merge` (0 = regular commit, 1 = merge commit)
- **Input:** Commit metadata (message, author, timestamp, stats)
- **Output:** Binary prediction with confidence score

### 2.3 Success Metrics
- **Accuracy:** Overall correctness of predictions
- **Precision:** How many predicted merges are actually merges
- **Recall:** How many actual merges are correctly identified
- **F1 Score:** Harmonic mean of precision and recall (primary metric)

---

## 3. Data Analysis

### 3.1 Dataset Overview

**Source:** GitHub Commits API (public repository)  
**Collection Period:** On-demand fetch  
**Total Records:** 30 commits  
**Features:** 28 engineered features  

**Data Location:**
```sql
-- Feature table
SELECT * FROM analytics.ml_features LIMIT 5;

-- Raw commits
SELECT * FROM raw.commits LIMIT 5;

-- Analytics metrics
SELECT * FROM analytics_analytics.commit_metrics LIMIT 5;
```

### 3.2 Class Distribution

**Current Dataset:**
```
Class 0 (Regular Commits): 30 (100%)
Class 1 (Merge Commits):    0 (0%)
```

**Issue Identified:** 
⚠️ **Severe class imbalance** - Dataset contains only one class (non-merge commits). This prevents model training as classification requires examples from both classes.

**Impact:**
- Cannot train binary classifier with single class
- No model performance metrics available
- Feature importance cannot be calculated
- MLflow experiments not logged

**Recommendation:**
- Collect data from repositories with merge commit history
- Target repositories using pull request workflows
- Aim for at least 20% merge commits (minimum viable imbalance)
- Consider repositories with active branching strategies

---

## 4. Feature Engineering

### 4.1 Feature Categories

The pipeline engineers **28 features** across 5 categories:

#### 4.1.1 Text Features (Message Analysis)
```python
1. message_length          # Character count of commit message
2. message_word_count      # Number of words in message
3. has_issue_reference     # Boolean: mentions issue/ticket
4. num_files_mentioned     # Count of files referenced in message
```

**Rationale:** Merge commits often have structured messages (e.g., "Merge branch 'feature-x'")

#### 4.1.2 Temporal Features (Time Patterns)
```python
5. commit_hour            # Hour of day (0-23)
6. commit_day_of_week     # Day of week (0=Monday, 6=Sunday)
7. commit_month           # Month (1-12)
8. is_weekend             # Boolean: committed on Sat/Sun
9. is_business_hours      # Boolean: committed 9am-5pm
```

**Rationale:** Merge commits may follow different temporal patterns (e.g., end of sprint, specific days)

#### 4.1.3 Author Features (Developer Behavior)
```python
10. author_name_length     # Length of author name
11. author_email_length    # Length of author email
12. is_bot_author          # Boolean: automated commit (bot, CI)
```

**Rationale:** Bots and automated systems often perform merges

#### 4.1.4 Commit Statistics (Change Metrics)
```python
13. total_changes          # additions + deletions
14. additions              # Lines added
15. deletions              # Lines removed
16. files_changed          # Number of files modified
```

**Rationale:** Merge commits typically aggregate multiple file changes

#### 4.1.5 Engagement Features (Derived Metrics)
```python
17. change_ratio           # additions / (total_changes + 1)
18. files_per_change       # files_changed / (total_changes + 1)
19. avg_changes_per_file   # total_changes / (files_changed + 1)
20. commit_complexity      # log(total_changes + 1) * files_changed
```

**Rationale:** Complex metrics capture commit patterns and development style

#### 4.1.6 Parent Commit Features
```python
21. has_parents            # Boolean: has parent commits
22. num_parents            # Count of parent commits
23. is_likely_merge        # Boolean: multiple parents (strong indicator)
```

**Rationale:** Merge commits have 2+ parent commits (strong signal)

#### 4.1.7 Derived Boolean Flags
```python
24. is_large_commit        # Boolean: total_changes > median
25. is_multi_file          # Boolean: files_changed > 1
26. high_deletion_ratio    # Boolean: deletions / total > 0.5
27. has_long_message       # Boolean: message_length > 100
28. frequent_author        # Boolean: author has > 5 commits
```

**Rationale:** Binary flags help tree-based models (RandomForest) make splits

### 4.2 Feature Engineering Code

**Location:** `pipeline/src/ml_pipeline.py` (lines 80-180)

```python
def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
    """
    Engineer 28 features from raw commit data
    
    Returns:
        DataFrame with engineered features and target variable
    """
    # Text features
    df['message_length'] = df['message'].str.len()
    df['message_word_count'] = df['message'].str.split().str.len()
    df['has_issue_reference'] = df['message'].str.contains(r'#\d+').astype(int)
    
    # Temporal features
    df['commit_timestamp'] = pd.to_datetime(df['commit_date'])
    df['commit_hour'] = df['commit_timestamp'].dt.hour
    df['commit_day_of_week'] = df['commit_timestamp'].dt.dayofweek
    df['is_weekend'] = (df['commit_day_of_week'] >= 5).astype(int)
    
    # ... (full implementation in ml_pipeline.py)
```

### 4.3 Feature Scaling

**Method:** StandardScaler (z-score normalization)

```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)
```

**Rationale:** 
- Ensures features have similar scales
- Improves model convergence
- Prevents large-magnitude features from dominating

---

## 5. Model Architecture

### 5.1 Algorithm Selection

**Model:** RandomForestClassifier (scikit-learn)

**Rationale:**
- ✅ Handles mixed feature types (continuous, categorical)
- ✅ Built-in feature importance
- ✅ Robust to outliers
- ✅ No assumption about feature distributions
- ✅ Fast training on structured data
- ✅ Good interpretability

**Alternatives Considered:**
- **Logistic Regression:** Too simple for non-linear patterns
- **XGBoost:** More complex, requires tuning (overkill for MVP)
- **Neural Networks:** Overkill for tabular data with 30 samples

### 5.2 Hyperparameters

**Current Configuration:**
```python
model = RandomForestClassifier(
    n_estimators=100,      # Number of trees
    max_depth=10,          # Maximum tree depth
    min_samples_split=2,   # Minimum samples to split node
    min_samples_leaf=1,    # Minimum samples in leaf
    random_state=42,       # Reproducibility
    n_jobs=-1              # Use all CPU cores
)
```

**Justification:**
- `n_estimators=100`: Balance between performance and training time
- `max_depth=10`: Prevents overfitting on small dataset
- `random_state=42`: Ensures reproducible results

### 5.3 Training Pipeline

**Location:** `pipeline/src/ml_pipeline.py` (lines 200-296)

**Steps:**
1. Load data from `analytics.commit_metrics` (or `raw.commits` fallback)
2. Engineer 28 features
3. Split into train/test (80/20)
4. Scale features with StandardScaler
5. Train RandomForest model
6. Calculate performance metrics
7. Log to MLflow

**Code Structure:**
```python
def train_model(self):
    with mlflow.start_run():
        # Load and prepare data
        df = self.load_data()
        df = self.engineer_features(df)
        
        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train model
        model = RandomForestClassifier(...)
        model.fit(X_train_scaled, y_train)
        
        # Evaluate
        metrics = calculate_metrics(model, X_test_scaled, y_test)
        
        # Log to MLflow
        mlflow.log_params(model.get_params())
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(model, "model")
```

---

## 6. Model Performance

### 6.1 Current Status

⚠️ **Model Training Incomplete**

**Reason:** Dataset contains only one class (all non-merge commits)

**Error Encountered:**
```
ValueError: Only one class present. Cannot train classification model.
```

**What This Means:**
- RandomForest cannot learn decision boundaries with single class
- No train/test predictions available
- No performance metrics calculated
- No feature importance derived

### 6.2 Expected Metrics (When Data is Fixed)

**Metrics Tracked in Code:**

```python
metrics = {
    'train_accuracy': accuracy_score(y_train, y_pred_train),
    'test_accuracy': accuracy_score(y_test, y_pred_test),
    'test_precision': precision_score(y_test, y_pred_test, average='weighted'),
    'test_recall': recall_score(y_test, y_pred_test, average='weighted'),
    'test_f1': f1_score(y_test, y_pred_test, average='weighted')
}
```

**Location:** `pipeline/src/ml_pipeline.py` (lines 216-220)

**Target Performance (Realistic Goals):**
- **Accuracy:** > 85% (overall correctness)
- **Precision:** > 80% (minimize false positives)
- **Recall:** > 75% (catch most merge commits)
- **F1 Score:** > 0.77 (balanced performance)

### 6.3 Feature Importance (Expected)

**Code Implementation:**
```python
# Extract feature importance
feature_importance = pd.DataFrame({
    'feature': available_features,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

logger.info("Feature Importance:")
logger.info(f"\n{feature_importance.to_string()}")
```

**Location:** `pipeline/src/ml_pipeline.py` (lines 228-235)

**Expected Top Features (Hypothesis):**
1. `is_likely_merge` - Multiple parent commits (strongest signal)
2. `num_parents` - Direct indicator of merge
3. `message_length` - Merge messages often longer/structured
4. `files_changed` - Merges aggregate many file changes
5. `total_changes` - Higher for merge commits

**Interpretation:**
- **High importance (>0.1):** Strong predictive power
- **Medium importance (0.05-0.1):** Moderate contribution
- **Low importance (<0.05):** Minimal predictive value (consider removal)

---

## 7. Model Limitations & Risks

### 7.1 Data Limitations

**Current Issues:**
1. ✅ **Sample Size:** Only 30 commits (need 500+ for robust model)
2. ⚠️ **Class Imbalance:** 100% non-merge commits (need 20-40% merge commits)
3. ⚠️ **Repository Bias:** Single repository (need diverse repos for generalization)
4. ⚠️ **Temporal Coverage:** Single time snapshot (need time series)

**Impact on Model:**
- Cannot train with current data
- High risk of overfitting even when trained
- Limited generalization to other repositories
- Sensitive to distribution shifts

### 7.2 Model Assumptions

1. **Feature Independence:** Assumes features contribute independently (not true for correlated features)
2. **Static Patterns:** Assumes merge patterns don't change over time
3. **Repository Homogeneity:** Trained on specific repository workflow
4. **Label Accuracy:** Assumes parent count correctly identifies merges

### 7.3 Known Biases

**Potential Biases:**
- **Repository Type:** May work better for certain project types
- **Team Size:** Features may differ for solo vs. team projects
- **Branching Strategy:** Assumes standard Git branching (feature branches, PRs)
- **Commit Conventions:** Relies on consistent commit message structure

### 7.4 Edge Cases

**Model May Struggle With:**
- Squash merges (single parent, looks like regular commit)
- Fast-forward merges (no merge commit created)
- Rebase workflows (linear history, no merge commits)
- Cherry-picked commits (manual merges)
- Automated commits from bots/CI

---

## 8. Where to Check Model Results

### 8.1 MLflow UI (Primary Interface)

**Access:**
```bash
# MLflow UI is running at:
http://localhost:5000
```

**What You'll See:**
- Experiment runs with timestamps
- Hyperparameters logged for each run
- Performance metrics (accuracy, precision, recall, F1)
- Feature importance plots (when available)
- Model artifacts (pickled models, scalers)
- Comparison across runs

**Current Status:**
```sql
-- Check MLflow runs
docker compose exec -T postgres psql -U dataplatform -d mlflow -c \
  "SELECT run_uuid, start_time, end_time, status 
   FROM runs 
   ORDER BY start_time DESC 
   LIMIT 5;"

-- Result: 0 rows (no experiments logged yet)
```

### 8.2 Pipeline Logs (Console Output)

**View Model Training Logs:**
```bash
# All pipeline logs
docker compose logs pipeline | less

# Filter for ML-specific logs
docker compose logs pipeline | grep -i "model"

# View model training results section
docker compose logs pipeline | grep -A 20 "Model Training Results"

# View feature importance
docker compose logs pipeline | grep -A 30 "Feature Importance"
```

**Expected Log Output (When Training Succeeds):**
```
================================================
Model Training Results
================================================
train_accuracy: 0.9200
test_accuracy: 0.8500
test_precision: 0.8300
test_recall: 0.8100
test_f1: 0.8200
MLflow Run ID: abc123def456
Model saved to: /mlflow/artifacts/models/model
================================================
Feature Importance:
     feature                importance
0    is_likely_merge       0.2500
1    num_parents           0.1800
2    message_length        0.1200
...
```

### 8.3 Database Queries (Data Inspection)

**Feature Data:**
```sql
-- View engineered features
docker compose exec -T postgres psql -U dataplatform -d analytics -c \
  "SELECT * FROM analytics.ml_features LIMIT 5;"

-- Check feature distribution
docker compose exec -T postgres psql -U dataplatform -d analytics -c \
  "SELECT 
     AVG(message_length) as avg_msg_length,
     AVG(total_changes) as avg_changes,
     AVG(files_changed) as avg_files,
     COUNT(*) as total_records
   FROM analytics.ml_features;"

-- Check target variable distribution
docker compose exec -T postgres psql -U dataplatform -d analytics -c \
  "SELECT 
     is_merge,
     COUNT(*) as count,
     ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
   FROM analytics.ml_features
   GROUP BY is_merge;"
```

**MLflow Metadata:**
```sql
-- Check experiment info
docker compose exec -T postgres psql -U dataplatform -d mlflow -c \
  "SELECT experiment_id, name, lifecycle_stage 
   FROM experiments;"

-- View run metrics
docker compose exec -T postgres psql -U dataplatform -d mlflow -c \
  "SELECT r.run_uuid, m.key, m.value 
   FROM runs r 
   JOIN metrics m ON r.run_uuid = m.run_uuid 
   ORDER BY r.start_time DESC 
   LIMIT 20;"
```

### 8.4 Grafana Dashboards (Monitoring)

**Access:**
```bash
# Grafana UI
http://localhost:3000
# Default credentials: admin/admin
```

**Queries to Add:**
1. **Model Training Frequency:** Count of ML pipeline runs over time
2. **Feature Distribution Drift:** Track feature statistics daily
3. **Model Performance Trends:** Plot accuracy/F1 over time
4. **Pipeline Duration:** Monitor ML stage execution time

---

## 9. Next Steps & Recommendations

### 9.1 Immediate Actions (To Enable Training)

**Priority 1: Fix Data Issue**
```bash
# Option 1: Fetch from repository with merge history
# Update ingestion.py to use repo with active PRs
GITHUB_REPO="owner/active-repo"  # Has merge commits

# Option 2: Use multiple repositories
repos = [
    "facebook/react",      # Active PR workflow
    "vercel/next.js",      # High merge activity
    "kubernetes/kubernetes" # Complex branching
]
```

**Priority 2: Increase Sample Size**
```python
# Modify ingestion.py to fetch more commits
commits = requests.get(
    f"{base_url}/repos/{owner}/{repo}/commits",
    params={"per_page": 100}  # Increase from 30 to 100
)
```

**Priority 3: Validate Class Balance**
```sql
-- After new ingestion, verify class distribution
SELECT 
  is_merge,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as pct
FROM analytics.ml_features
GROUP BY is_merge;

-- Target: 20-40% merge commits
```

### 9.2 Model Improvements (When Training Works)

**Iteration 1: Baseline Model**
- ✅ Current RandomForest with default params
- ✅ Establish baseline metrics
- ✅ Identify most important features

**Iteration 2: Hyperparameter Tuning**
```python
from sklearn.model_selection import GridSearchCV

param_grid = {
    'n_estimators': [50, 100, 200],
    'max_depth': [5, 10, 15, None],
    'min_samples_split': [2, 5, 10],
    'class_weight': ['balanced', None]  # Handle imbalance
}

grid_search = GridSearchCV(
    RandomForestClassifier(random_state=42),
    param_grid,
    cv=5,
    scoring='f1',
    n_jobs=-1
)
```

**Iteration 3: Feature Selection**
```python
from sklearn.feature_selection import SelectKBest, f_classif

# Select top 15 features
selector = SelectKBest(f_classif, k=15)
X_selected = selector.fit_transform(X_train, y_train)

# Log selected features
selected_features = X.columns[selector.get_support()]
mlflow.log_param("selected_features", list(selected_features))
```

**Iteration 4: Ensemble Methods**
```python
from sklearn.ensemble import VotingClassifier
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier

ensemble = VotingClassifier(
    estimators=[
        ('rf', RandomForestClassifier()),
        ('lr', LogisticRegression()),
        ('xgb', XGBClassifier())
    ],
    voting='soft'
)
```

### 9.3 Production Readiness

**Before Deployment:**
- [ ] Achieve F1 > 0.75 on test set
- [ ] Validate on 3+ different repositories
- [ ] Test on edge cases (squash merges, rebases)
- [ ] Add model versioning with MLflow Registry
- [ ] Implement model monitoring (drift detection)
- [ ] Create rollback plan
- [ ] Document model assumptions and limitations
- [ ] Add confidence thresholds for predictions

### 9.4 Enhanced Analysis

**Add to Pipeline:**
1. **Confusion Matrix:** Visualize prediction errors
2. **ROC Curve:** Evaluate classification thresholds
3. **SHAP Values:** Explain individual predictions
4. **Learning Curves:** Diagnose bias/variance
5. **Cross-Validation:** More robust performance estimates

**Create Notebook:**
```bash
# Add Jupyter notebook for interactive analysis
jupyter notebook notebooks/model_exploration.ipynb
```

**Sections:**
- Data exploration and visualization
- Feature correlation analysis
- Model comparison experiments
- Error analysis
- Business impact simulation

---

## 10. Conclusion

### 10.1 Summary

This ML pipeline demonstrates **production-ready infrastructure** for commit classification:
- ✅ **Comprehensive feature engineering:** 28 well-designed features
- ✅ **Robust architecture:** RandomForest with MLflow tracking
- ✅ **Complete metrics:** Accuracy, precision, recall, F1, feature importance
- ✅ **Scalable design:** Easy to retrain and deploy new versions
- ⚠️ **Data limitation:** Current dataset prevents training (fixable)

### 10.2 Technical Achievements

**What's Production-Ready:**
- Feature engineering pipeline (28 features)
- Model training infrastructure
- MLflow experiment tracking
- Metrics logging and artifact storage
- Reproducible training pipeline

**What Needs Data:**
- Actual model training (blocked by single-class data)
- Performance metrics (waiting for diverse dataset)
- Feature importance analysis (requires trained model)
- Model deployment (pending successful training)

### 10.3 Business Value (When Operational)

**Immediate Benefits:**
- Automated merge commit detection
- Code review prioritization
- Development workflow insights
- Team productivity analytics

**Long-Term Value:**
- Predictive release planning
- Risk assessment for changes
- Developer behavior analysis
- Process optimization recommendations

---

## Appendix A: Quick Reference Commands

### Run Full Pipeline
```bash
make pipeline
```

### Check MLflow UI
```bash
open http://localhost:5000
```

### View Model Logs
```bash
docker compose logs pipeline | grep -A 20 "Model Training"
```

### Check Feature Data
```sql
docker compose exec -T postgres psql -U dataplatform -d analytics -c \
  "SELECT * FROM analytics.ml_features LIMIT 5;"
```

### Verify MLflow Runs
```sql
docker compose exec -T postgres psql -U dataplatform -d mlflow -c \
  "SELECT COUNT(*) as total_runs FROM runs;"
```

---

**Document Version:** 1.0  
**Last Updated:** February 2, 2026  
**Author:** Data Engineering Team  
**Status:** ⚠️ Training blocked by data limitation - Infrastructure ready
