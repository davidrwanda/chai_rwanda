"""
ML Component: Feature Engineering and Model Training
Builds features suitable for ML and trains a simple model with MLflow tracking
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, Any
from loguru import logger
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import mlflow
import mlflow.sklearn
import joblib
import sys

# Configure logging
logger.remove()
logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}", level="INFO")


class MLPipeline:
    """ML pipeline for feature engineering and model training"""
    
    def __init__(self):
        # PostgreSQL configuration
        db_user = os.getenv('POSTGRES_USER', 'dataplatform')
        db_password = os.getenv('POSTGRES_PASSWORD', 'changeme123')
        db_host = os.getenv('POSTGRES_HOST', 'postgres')
        db_port = os.getenv('POSTGRES_PORT', '5432')
        db_name = os.getenv('POSTGRES_DB', 'analytics')
        
        self.db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        self.engine = create_engine(self.db_url)
        
        # MLflow configuration
        mlflow_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://mlflow:5000')
        mlflow.set_tracking_uri(mlflow_uri)
        mlflow.set_experiment("commit-analysis")
        
        logger.info(f"MLflow tracking URI: {mlflow_uri}")
    
    def load_data(self) -> pd.DataFrame:
        """Load data from analytics mart"""
        logger.info("Loading data from analytics mart...")
        
        try:
            # Try to load from analytics mart first, fallback to raw
            try:
                query = "SELECT * FROM analytics.commit_metrics"
                df = pd.read_sql(query, self.engine)
                logger.info(f"Loaded {len(df)} rows from analytics.commit_metrics")
            except:
                query = "SELECT * FROM raw.commits"
                df = pd.read_sql(query, self.engine)
                logger.info(f"Loaded {len(df)} rows from raw.commits (fallback)")
            
            return df
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            raise
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Feature Engineering: Create ML-ready features
        Task: Predict if a commit is a merge commit based on patterns
        """
        logger.info("Engineering features...")
        
        features_df = df.copy()
        
        # Text-based features
        if 'commit_message' in features_df.columns:
            features_df['message_length'] = features_df['commit_message'].str.len()
            features_df['message_word_count'] = features_df['commit_message'].str.split().str.len()
            features_df['has_issue_ref'] = features_df['commit_message'].str.contains(r'#\d+', na=False).astype(int)
            features_df['has_pr_ref'] = features_df['commit_message'].str.contains(r'PR|pull request', case=False, na=False).astype(int)
            
            # Target variable: is merge commit
            features_df['is_merge'] = features_df['commit_message'].str.lower().str.contains('merge', na=False).astype(int)
        
        # Temporal features
        if 'author_date' in features_df.columns:
            features_df['author_date'] = pd.to_datetime(features_df['author_date'])
            features_df['hour_of_day'] = features_df['author_date'].dt.hour
            features_df['day_of_week'] = features_df['author_date'].dt.dayofweek
            features_df['is_weekend'] = (features_df['day_of_week'] >= 5).astype(int)
            features_df['is_business_hours'] = ((features_df['hour_of_day'] >= 9) & 
                                               (features_df['hour_of_day'] <= 17)).astype(int)
        
        # Author features
        if 'author_email' in features_df.columns:
            # Author domain
            features_df['author_domain'] = features_df['author_email'].str.extract(r'@(.+)$')[0]
            features_df['is_company_email'] = features_df['author_domain'].str.contains(
                'python.org|github.com', na=False
            ).astype(int)
        
        # Comment engagement
        if 'comment_count' in features_df.columns:
            features_df['has_comments'] = (features_df['comment_count'] > 0).astype(int)
        
        # Aggregate author statistics
        if 'author_email' in features_df.columns:
            author_stats = features_df.groupby('author_email').agg({
                'commit_sha': 'count',
                'comment_count': 'mean'
            }).rename(columns={
                'commit_sha': 'author_commit_count',
                'comment_count': 'author_avg_comments'
            })
            features_df = features_df.merge(author_stats, on='author_email', how='left')
        
        logger.info(f"Feature engineering complete. Shape: {features_df.shape}")
        logger.info(f"Features: {list(features_df.columns)}")
        
        return features_df
    
    def save_feature_table(self, df: pd.DataFrame):
        """Save feature table to PostgreSQL for future use"""
        logger.info("Saving feature table to PostgreSQL...")
        
        try:
            df.to_sql(
                'ml_features',
                self.engine,
                schema='analytics',
                if_exists='replace',
                index=False
            )
            logger.info(f"Feature table saved: analytics.ml_features ({len(df)} rows)")
        except Exception as e:
            logger.error(f"Failed to save feature table: {e}")
            # Don't raise - this is optional
    
    def train_model(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train a classification model with MLflow tracking"""
        logger.info("Training ML model...")
        
        # Select features for training
        feature_columns = [
            'message_length', 'message_word_count', 'has_issue_ref', 'has_pr_ref',
            'hour_of_day', 'day_of_week', 'is_weekend', 'is_business_hours',
            'is_company_email', 'has_comments', 'comment_count',
            'author_commit_count', 'author_avg_comments'
        ]
        
        # Filter to available columns
        available_features = [col for col in feature_columns if col in df.columns]
        logger.info(f"Using features: {available_features}")
        
        if 'is_merge' not in df.columns:
            logger.warning("Target variable 'is_merge' not found. Skipping training.")
            return {}
        
        # Prepare data
        X = df[available_features].fillna(0)
        y = df['is_merge']
        
        # Check class balance
        class_dist = y.value_counts()
        logger.info(f"Class distribution:\n{class_dist}")
        
        if len(class_dist) < 2:
            logger.warning("Only one class present. Cannot train classification model.")
            return {}
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        logger.info(f"Training set: {len(X_train)} samples")
        logger.info(f"Test set: {len(X_test)} samples")
        
        # Start MLflow run
        with mlflow.start_run() as run:
            # Log parameters
            params = {
                'model_type': 'RandomForestClassifier',
                'n_estimators': 100,
                'max_depth': 10,
                'random_state': 42,
                'n_features': len(available_features),
                'train_size': len(X_train),
                'test_size': len(X_test)
            }
            mlflow.log_params(params)
            
            # Feature scaling
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            model = RandomForestClassifier(
                n_estimators=params['n_estimators'],
                max_depth=params['max_depth'],
                random_state=params['random_state'],
                n_jobs=-1
            )
            
            logger.info("Training RandomForest model...")
            model.fit(X_train_scaled, y_train)
            
            # Make predictions
            y_pred_train = model.predict(X_train_scaled)
            y_pred_test = model.predict(X_test_scaled)
            
            # Calculate metrics
            metrics = {
                'train_accuracy': accuracy_score(y_train, y_pred_train),
                'test_accuracy': accuracy_score(y_test, y_pred_test),
                'test_precision': precision_score(y_test, y_pred_test, average='weighted'),
                'test_recall': recall_score(y_test, y_pred_test, average='weighted'),
                'test_f1': f1_score(y_test, y_pred_test, average='weighted')
            }
            
            # Log metrics
            mlflow.log_metrics(metrics)
            
            # Log feature importance
            feature_importance = pd.DataFrame({
                'feature': available_features,
                'importance': model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            logger.info("Feature Importance:")
            logger.info(f"\n{feature_importance.to_string()}")
            
            # Log model
            mlflow.sklearn.log_model(model, "model")
            mlflow.sklearn.log_model(scaler, "scaler")
            
            # Save model locally
            model_path = '/models/commit_classifier.pkl'
            scaler_path = '/models/scaler.pkl'
            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)
            
            mlflow.log_artifact(model_path)
            mlflow.log_artifact(scaler_path)
            
            logger.info("=" * 60)
            logger.info("Model Training Results")
            logger.info("=" * 60)
            for metric, value in metrics.items():
                logger.info(f"{metric}: {value:.4f}")
            logger.info("=" * 60)
            logger.info(f"MLflow Run ID: {run.info.run_id}")
            logger.info(f"Model saved to: {model_path}")
            
            return {
                'run_id': run.info.run_id,
                'metrics': metrics,
                'feature_importance': feature_importance.to_dict('records')
            }
    
    def run(self):
        """Execute the complete ML pipeline"""
        logger.info("=" * 60)
        logger.info("Starting ML Pipeline")
        logger.info("=" * 60)
        
        try:
            # Load data
            df = self.load_data()
            
            # Engineer features
            features_df = self.engineer_features(df)
            
            # Save feature table
            self.save_feature_table(features_df)
            
            # Train model
            results = self.train_model(features_df)
            
            logger.info("=" * 60)
            logger.info("ML Pipeline Completed Successfully")
            logger.info("=" * 60)
            
            return results
        
        except Exception as e:
            logger.error(f"ML pipeline failed: {e}")
            raise


if __name__ == "__main__":
    ml_pipeline = MLPipeline()
    ml_pipeline.run()
