"""
Data Ingestion Module
Fetches data from public API and stores raw data in MinIO object storage
"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, Any, List
from loguru import logger
from minio import Minio
from minio.error import S3Error
import sys

# Configure logging to stdout for container environments
logger.remove()
logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}", level="INFO")


class DataIngestion:
    """Handles data ingestion from external APIs to object storage"""
    
    def __init__(self):
        self.api_url = os.getenv('DATA_SOURCE_API_URL', 'https://api.github.com/repos/python/cpython/commits')
        self.minio_endpoint = os.getenv('MINIO_ENDPOINT', 'minio:9000')
        self.minio_access_key = os.getenv('MINIO_ROOT_USER', 'minioadmin')
        self.minio_secret_key = os.getenv('MINIO_ROOT_PASSWORD', 'minioadmin')
        self.bucket_name = os.getenv('MINIO_BUCKET', 'raw-data')
        
        # Initialize MinIO client
        self.minio_client = Minio(
            self.minio_endpoint,
            access_key=self.minio_access_key,
            secret_key=self.minio_secret_key,
            secure=False
        )
        
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            if not self.minio_client.bucket_exists(self.bucket_name):
                self.minio_client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.info(f"Bucket {self.bucket_name} already exists")
        except S3Error as e:
            logger.error(f"Error creating bucket: {e}")
            raise
    
    def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch data from the API"""
        logger.info(f"Fetching data from {self.api_url}")
        
        try:
            response = requests.get(
                self.api_url,
                headers={'Accept': 'application/vnd.github.v3+json'},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Successfully fetched {len(data)} records")
            return data
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch data: {e}")
            raise
    
    def store_raw_data(self, data: List[Dict[str, Any]]) -> str:
        """
        Store raw data in MinIO organized by source and date
        Path format: raw-data/github-commits/YYYY-MM-DD/HH-MM-SS.json
        """
        timestamp = datetime.now()
        date_path = timestamp.strftime('%Y-%m-%d')
        time_filename = timestamp.strftime('%H-%M-%S.json')
        
        object_name = f"github-commits/{date_path}/{time_filename}"
        
        # Convert data to JSON bytes
        data_bytes = json.dumps(data, indent=2).encode('utf-8')
        data_size = len(data_bytes)
        
        try:
            # Upload to MinIO
            from io import BytesIO
            self.minio_client.put_object(
                self.bucket_name,
                object_name,
                BytesIO(data_bytes),
                length=data_size,
                content_type='application/json'
            )
            
            logger.info(f"Stored raw data at: s3://{self.bucket_name}/{object_name}")
            logger.info(f"Data size: {data_size} bytes")
            
            return object_name
        
        except S3Error as e:
            logger.error(f"Failed to store data in MinIO: {e}")
            raise
    
    def run(self) -> str:
        """Execute the complete ingestion pipeline"""
        logger.info("=" * 60)
        logger.info("Starting Data Ingestion Pipeline")
        logger.info("=" * 60)
        
        try:
            # Fetch data from API
            data = self.fetch_data()
            
            # Store in MinIO
            object_path = self.store_raw_data(data)
            
            logger.info("=" * 60)
            logger.info("Data Ingestion Completed Successfully")
            logger.info("=" * 60)
            
            return object_path
        
        except Exception as e:
            logger.error(f"Data ingestion failed: {e}")
            raise


if __name__ == "__main__":
    ingestion = DataIngestion()
    ingestion.run()
