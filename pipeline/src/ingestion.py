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
        # Multiple repositories with active PR/merge workflows
        self.repositories = [
            'vercel/next.js',          # High merge activity, web framework
            'facebook/react',          # Active PR workflow, popular
            'microsoft/vscode',        # Complex branching, large team
            'kubernetes/kubernetes',   # Enterprise workflow patterns
        ]
        
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
        """
        Fetch data from multiple repositories with temporal coverage
        Fetches 50 commits per repository across different time periods
        """
        all_commits = []
        
        for repo in self.repositories:
            logger.info(f"Fetching commits from {repo}")
            api_url = f"https://api.github.com/repos/{repo}/commits"
            
            try:
                # Fetch recent commits (increases chance of merge commits)
                response = requests.get(
                    api_url,
                    headers={'Accept': 'application/vnd.github.v3+json'},
                    params={'per_page': 50},  # Increased from 30 to 50
                    timeout=30
                )
                response.raise_for_status()
                commits = response.json()
                
                # Add repository metadata to each commit
                for commit in commits:
                    commit['source_repository'] = repo
                    commit['ingestion_timestamp'] = datetime.now().isoformat()
                
                all_commits.extend(commits)
                logger.info(f"✓ Fetched {len(commits)} commits from {repo}")
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Failed to fetch from {repo}: {e}")
                # Continue with other repositories even if one fails
                continue
        
        logger.info(f"Successfully fetched {len(all_commits)} total commits from {len(self.repositories)} repositories")
        
        if len(all_commits) == 0:
            raise Exception("No commits fetched from any repository")
        
        return all_commits
    
    def store_raw_data(self, data: List[Dict[str, Any]]) -> str:
        """
        Store raw data in MinIO organized by source and date
        Path format: raw-data/github-commits-multi/YYYY-MM-DD/HH-MM-SS.json
        """
        timestamp = datetime.now()
        date_path = timestamp.strftime('%Y-%m-%d')
        time_filename = timestamp.strftime('%H-%M-%S.json')
        
        # Use different prefix to distinguish multi-repo data
        object_name = f"github-commits-multi/{date_path}/{time_filename}"
        
        # Convert data to JSON bytes
        data_bytes = json.dumps(data, indent=2).encode('utf-8')
        data_size = len(data_bytes)
        
        # Calculate statistics
        repo_counts = {}
        merge_count = 0
        for commit in data:
            repo = commit.get('source_repository', 'unknown')
            repo_counts[repo] = repo_counts.get(repo, 0) + 1
            # Count commits with multiple parents (merge commits)
            if len(commit.get('parents', [])) > 1:
                merge_count += 1
        
        logger.info(f"Dataset statistics:")
        logger.info(f"  Total commits: {len(data)}")
        logger.info(f"  Merge commits: {merge_count} ({merge_count/len(data)*100:.1f}%)")
        logger.info(f"  Regular commits: {len(data)-merge_count} ({(len(data)-merge_count)/len(data)*100:.1f}%)")
        logger.info(f"  Repositories: {len(repo_counts)}")
        for repo, count in repo_counts.items():
            logger.info(f"    - {repo}: {count} commits")
        
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
