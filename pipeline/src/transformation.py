"""
Data Transformation Module
Reads raw data from MinIO, applies transformations, and loads into PostgreSQL
"""

import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
from loguru import logger
from minio import Minio
from sqlalchemy import create_engine, text
import sys
from io import BytesIO

# Configure logging
logger.remove()
logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}", level="INFO")


class DataTransformation:
    """Handles data transformation and loading to PostgreSQL"""
    
    def __init__(self):
        # MinIO configuration
        self.minio_endpoint = os.getenv('MINIO_ENDPOINT', 'minio:9000')
        self.minio_access_key = os.getenv('MINIO_ROOT_USER', 'minioadmin')
        self.minio_secret_key = os.getenv('MINIO_ROOT_PASSWORD', 'minioadmin')
        self.bucket_name = os.getenv('MINIO_BUCKET', 'raw-data')
        
        # PostgreSQL configuration
        db_user = os.getenv('POSTGRES_USER', 'dataplatform')
        db_password = os.getenv('POSTGRES_PASSWORD', 'changeme123')
        db_host = os.getenv('POSTGRES_HOST', 'postgres')
        db_port = os.getenv('POSTGRES_PORT', '5432')
        db_name = os.getenv('POSTGRES_DB', 'analytics')
        
        self.db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        # Initialize clients
        self.minio_client = Minio(
            self.minio_endpoint,
            access_key=self.minio_access_key,
            secret_key=self.minio_secret_key,
            secure=False
        )
        
        self.engine = create_engine(self.db_url)
    
    def get_latest_raw_data(self) -> pd.DataFrame:
        """Fetch the most recent raw data from MinIO"""
        logger.info(f"Fetching latest data from MinIO bucket: {self.bucket_name}")
        
        try:
            # List objects in the bucket
            objects = list(self.minio_client.list_objects(
                self.bucket_name,
                prefix="github-commits/",
                recursive=True
            ))
            
            if not objects:
                raise ValueError("No data found in MinIO bucket")
            
            # Sort by last modified and get the most recent
            latest_object = sorted(objects, key=lambda x: x.last_modified, reverse=True)[0]
            logger.info(f"Latest object: {latest_object.object_name}")
            
            # Download the object
            response = self.minio_client.get_object(self.bucket_name, latest_object.object_name)
            data = json.loads(response.read())
            
            logger.info(f"Loaded {len(data)} records from MinIO")
            return pd.DataFrame(data)
        
        except Exception as e:
            logger.error(f"Failed to fetch data from MinIO: {e}")
            raise
    
    def transform_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply transformations to the raw data"""
        logger.info("Starting data transformation")
        
        # Flatten nested JSON structure
        transformed = pd.json_normalize(df.to_dict('records'))
        
        # Select and rename key columns
        column_mapping = {
            'sha': 'commit_sha',
            'commit.author.name': 'author_name',
            'commit.author.email': 'author_email',
            'commit.author.date': 'author_date',
            'commit.committer.name': 'committer_name',
            'commit.committer.email': 'committer_email',
            'commit.committer.date': 'committer_date',
            'commit.message': 'commit_message',
            'commit.comment_count': 'comment_count'
        }
        
        # Select available columns
        available_cols = {k: v for k, v in column_mapping.items() if k in transformed.columns}
        df_clean = transformed[list(available_cols.keys())].copy()
        df_clean.rename(columns=available_cols, inplace=True)
        
        # Data cleaning
        # 1. Convert date columns to datetime
        date_columns = ['author_date', 'committer_date']
        for col in date_columns:
            if col in df_clean.columns:
                df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')
        
        # 2. Handle missing values
        df_clean['comment_count'] = df_clean.get('comment_count', 0).fillna(0).astype(int)
        
        # 3. Clean text fields - remove nulls and normalize
        text_columns = ['author_name', 'author_email', 'committer_name', 
                       'committer_email', 'commit_message']
        for col in text_columns:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].fillna('').astype(str).str.strip()
        
        # 4. Derive new fields
        if 'commit_message' in df_clean.columns:
            df_clean['message_length'] = df_clean['commit_message'].str.len()
            df_clean['is_merge_commit'] = df_clean['commit_message'].str.lower().str.contains('merge', na=False)
        
        if 'author_date' in df_clean.columns:
            df_clean['commit_date'] = df_clean['author_date'].dt.date
            df_clean['commit_hour'] = df_clean['author_date'].dt.hour
            df_clean['day_of_week'] = df_clean['author_date'].dt.dayofweek
        
        # Add metadata
        df_clean['loaded_at'] = datetime.now()
        df_clean['source'] = 'github_api'
        
        logger.info(f"Transformation complete. Output shape: {df_clean.shape}")
        logger.info(f"Columns: {list(df_clean.columns)}")
        
        return df_clean
    
    def load_to_postgres(self, df: pd.DataFrame, table_name: str = 'commits'):
        """Load transformed data to PostgreSQL"""
        logger.info(f"Loading data to PostgreSQL table: raw.{table_name}")
        
        try:
            # Ensure schema exists
            with self.engine.connect() as conn:
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
                conn.commit()
            
            # Truncate table instead of dropping (preserves dependent views)
            with self.engine.connect() as conn:
                # Check if table exists
                result = conn.execute(text(
                    f"SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                    f"WHERE table_schema = 'raw' AND table_name = '{table_name}')"
                ))
                table_exists = result.scalar()
                
                if table_exists:
                    logger.info(f"Table raw.{table_name} exists. Truncating...")
                    conn.execute(text(f"TRUNCATE TABLE raw.{table_name}"))
                    conn.commit()
            
            # Load data (append to empty table or create new)
            df.to_sql(
                table_name,
                self.engine,
                schema='raw',
                if_exists='append',
                index=False,
                method='multi',
                chunksize=1000
            )
            
            logger.info(f"Successfully loaded {len(df)} rows to raw.{table_name}")
            
            # Verify load
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM raw.{table_name}"))
                count = result.scalar()
                logger.info(f"Verification: Table contains {count} rows")
        
        except Exception as e:
            logger.error(f"Failed to load data to PostgreSQL: {e}")
            raise
    
    def run(self):
        """Execute the complete transformation pipeline"""
        logger.info("=" * 60)
        logger.info("Starting Data Transformation Pipeline")
        logger.info("=" * 60)
        
        try:
            # Fetch raw data
            raw_df = self.get_latest_raw_data()
            
            # Transform data
            transformed_df = self.transform_data(raw_df)
            
            # Load to PostgreSQL
            self.load_to_postgres(transformed_df)
            
            logger.info("=" * 60)
            logger.info("Data Transformation Completed Successfully")
            logger.info("=" * 60)
        
        except Exception as e:
            logger.error(f"Data transformation failed: {e}")
            raise


if __name__ == "__main__":
    transformation = DataTransformation()
    transformation.run()
