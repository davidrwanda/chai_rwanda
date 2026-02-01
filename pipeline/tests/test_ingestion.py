"""
Unit Tests for Data Ingestion Module
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.ingestion import DataIngestion
import json


class TestDataIngestion:
    """Test suite for DataIngestion class"""
    
    @pytest.fixture
    def ingestion(self):
        """Create a DataIngestion instance for testing"""
        with patch('src.ingestion.Minio'):
            ingestion = DataIngestion()
            return ingestion
    
    @pytest.fixture
    def sample_commit_data(self):
        """Sample commit data for testing"""
        return [
            {
                "sha": "abc123",
                "commit": {
                    "author": {
                        "name": "Test User",
                        "email": "test@example.com",
                        "date": "2024-01-01T10:00:00Z"
                    },
                    "message": "Test commit",
                    "comment_count": 0
                }
            }
        ]
    
    def test_ensure_bucket_exists_creates_bucket(self, ingestion):
        """Test that bucket is created if it doesn't exist"""
        ingestion.minio_client.bucket_exists = Mock(return_value=False)
        ingestion.minio_client.make_bucket = Mock()
        
        ingestion._ensure_bucket_exists()
        
        ingestion.minio_client.make_bucket.assert_called_once_with(ingestion.bucket_name)
    
    def test_ensure_bucket_exists_skips_if_exists(self, ingestion):
        """Test that bucket creation is skipped if bucket exists"""
        ingestion.minio_client.bucket_exists = Mock(return_value=True)
        ingestion.minio_client.make_bucket = Mock()
        
        ingestion._ensure_bucket_exists()
        
        ingestion.minio_client.make_bucket.assert_not_called()
    
    @patch('src.ingestion.requests.get')
    def test_fetch_data_success(self, mock_get, ingestion, sample_commit_data):
        """Test successful data fetching from API"""
        mock_response = Mock()
        mock_response.json.return_value = sample_commit_data
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        data = ingestion.fetch_data()
        
        assert data == sample_commit_data
        assert len(data) == 1
        mock_get.assert_called_once()
    
    @patch('src.ingestion.requests.get')
    def test_fetch_data_failure(self, mock_get, ingestion):
        """Test handling of API failure"""
        mock_get.side_effect = Exception("API Error")
        
        with pytest.raises(Exception):
            ingestion.fetch_data()
    
    def test_store_raw_data_success(self, ingestion, sample_commit_data):
        """Test successful data storage to MinIO"""
        ingestion.minio_client.put_object = Mock()
        
        object_path = ingestion.store_raw_data(sample_commit_data)
        
        assert "github-commits/" in object_path
        assert object_path.endswith(".json")
        ingestion.minio_client.put_object.assert_called_once()
    
    def test_store_raw_data_organizes_by_date(self, ingestion, sample_commit_data):
        """Test that data is organized by date"""
        ingestion.minio_client.put_object = Mock()
        
        object_path = ingestion.store_raw_data(sample_commit_data)
        
        # Should contain date in format YYYY-MM-DD
        import re
        date_pattern = r'\d{4}-\d{2}-\d{2}'
        assert re.search(date_pattern, object_path) is not None


class TestDataValidation:
    """Test data validation logic"""
    
    def test_commit_data_structure(self):
        """Test that commit data has expected structure"""
        commit = {
            "sha": "a" * 40,
            "commit": {
                "author": {
                    "name": "Test",
                    "email": "test@test.com",
                    "date": "2024-01-01T00:00:00Z"
                },
                "message": "Test message",
                "comment_count": 0
            }
        }
        
        assert len(commit["sha"]) == 40
        assert "author" in commit["commit"]
        assert "message" in commit["commit"]
    
    def test_sha_format_validation(self):
        """Test SHA hash format validation"""
        valid_sha = "a" * 40
        invalid_sha = "xyz123"
        
        import re
        sha_pattern = r'^[a-f0-9]{40}$'
        
        assert re.match(sha_pattern, valid_sha) is not None
        assert re.match(sha_pattern, invalid_sha) is None
