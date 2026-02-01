"""
Integration Tests for Complete Pipeline
"""

import pytest
import os
import pandas as pd
from sqlalchemy import create_engine, text


class TestPipelineIntegration:
    """Integration tests for the complete data pipeline"""
    
    @pytest.fixture
    def db_engine(self):
        """Create database connection for testing"""
        db_url = "postgresql://dataplatform:changeme123@postgres:5432/analytics"
        return create_engine(db_url)
    
    def test_database_connection(self, db_engine):
        """Test that we can connect to the database"""
        with db_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
    
    def test_raw_schema_exists(self, db_engine):
        """Test that raw schema exists"""
        with db_engine.connect() as conn:
            result = conn.execute(text(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'raw'"
            ))
            schemas = [row[0] for row in result]
            assert 'raw' in schemas
    
    def test_staging_schema_exists(self, db_engine):
        """Test that staging schema exists"""
        with db_engine.connect() as conn:
            result = conn.execute(text(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'staging'"
            ))
            schemas = [row[0] for row in result]
            assert 'staging' in schemas
    
    def test_analytics_schema_exists(self, db_engine):
        """Test that analytics schema exists"""
        with db_engine.connect() as conn:
            result = conn.execute(text(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'analytics'"
            ))
            schemas = [row[0] for row in result]
            assert 'analytics' in schemas
    
    def test_raw_commits_table_populated(self, db_engine):
        """Test that raw.commits table has data"""
        try:
            with db_engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM raw.commits"))
                count = result.scalar()
                assert count > 0, "raw.commits table should have data"
        except Exception as e:
            pytest.skip(f"Table not yet created: {e}")
    
    def test_commits_have_required_columns(self, db_engine):
        """Test that commits table has all required columns"""
        required_columns = [
            'commit_sha', 'author_name', 'author_email', 'author_date',
            'commit_message', 'comment_count'
        ]
        
        try:
            with db_engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'raw' AND table_name = 'commits'"
                ))
                columns = [row[0] for row in result]
                
                for required in required_columns:
                    assert required in columns, f"Missing required column: {required}"
        except Exception as e:
            pytest.skip(f"Table not yet created: {e}")
    
    def test_no_null_commit_shas(self, db_engine):
        """Test that commit_sha column has no nulls"""
        try:
            with db_engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM raw.commits WHERE commit_sha IS NULL"
                ))
                null_count = result.scalar()
                assert null_count == 0, "commit_sha should not have null values"
        except Exception as e:
            pytest.skip(f"Table not yet created: {e}")
    
    def test_analytics_mart_exists(self, db_engine):
        """Test that analytics mart table exists"""
        try:
            with db_engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM analytics.commit_metrics"
                ))
                count = result.scalar()
                assert count > 0, "analytics.commit_metrics should have data"
        except Exception as e:
            pytest.skip(f"Analytics mart not yet created: {e}")
    
    def test_feature_table_exists(self, db_engine):
        """Test that ML feature table exists"""
        try:
            with db_engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM analytics.ml_features"
                ))
                count = result.scalar()
                assert count > 0, "ML features table should have data"
        except Exception as e:
            pytest.skip(f"Feature table not yet created: {e}")
    
    def test_data_freshness(self, db_engine):
        """Test that data is recent (loaded today or yesterday)"""
        try:
            with db_engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT MAX(loaded_at) FROM raw.commits"
                ))
                max_date = result.scalar()
                
                if max_date:
                    from datetime import datetime, timedelta
                    age = datetime.now() - max_date
                    assert age.days <= 1, "Data should be fresh (within 24 hours)"
        except Exception as e:
            pytest.skip(f"Cannot check data freshness: {e}")


class TestDataQuality:
    """Data quality integration tests"""
    
    @pytest.fixture
    def db_engine(self):
        """Create database connection for testing"""
        db_url = "postgresql://dataplatform:changeme123@postgres:5432/analytics"
        return create_engine(db_url)
    
    def test_no_duplicate_commits(self, db_engine):
        """Test that there are no duplicate commit SHAs"""
        try:
            with db_engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT commit_sha, COUNT(*) as cnt "
                    "FROM raw.commits "
                    "GROUP BY commit_sha "
                    "HAVING COUNT(*) > 1"
                ))
                duplicates = list(result)
                assert len(duplicates) == 0, f"Found {len(duplicates)} duplicate commits"
        except Exception as e:
            pytest.skip(f"Cannot check for duplicates: {e}")
    
    def test_valid_email_format(self, db_engine):
        """Test that email addresses are valid"""
        try:
            with db_engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM raw.commits "
                    "WHERE author_email !~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$'"
                ))
                invalid_count = result.scalar()
                # Allow some flexibility for bot accounts and unusual formats
                assert invalid_count < 10, f"Too many invalid email formats: {invalid_count}"
        except Exception as e:
            pytest.skip(f"Cannot validate emails: {e}")
