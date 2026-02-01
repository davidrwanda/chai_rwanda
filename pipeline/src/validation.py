"""
Data Quality Validation Module
Implements schema validation, null checks, duplicate detection, and row count checks
"""

import os
import pandas as pd
from typing import Dict, Any, List, Tuple
from loguru import logger
from sqlalchemy import create_engine, text, inspect
from pydantic import BaseModel, Field, validator
from datetime import datetime
import sys

# Configure logging
logger.remove()
logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}", level="INFO")


class CommitSchema(BaseModel):
    """Pydantic schema for commit data validation"""
    commit_sha: str = Field(..., min_length=40, max_length=40)
    author_name: str = Field(..., min_length=1)
    author_email: str = Field(..., min_length=1)
    author_date: datetime
    committer_name: str = Field(..., min_length=1)
    committer_email: str = Field(..., min_length=1)
    committer_date: datetime
    commit_message: str = Field(..., min_length=1)
    comment_count: int = Field(..., ge=0)
    
    class Config:
        str_strip_whitespace = True


class DataQualityValidator:
    """Implements comprehensive data quality checks"""
    
    def __init__(self):
        # PostgreSQL configuration
        db_user = os.getenv('POSTGRES_USER', 'dataplatform')
        db_password = os.getenv('POSTGRES_PASSWORD', 'changeme123')
        db_host = os.getenv('POSTGRES_HOST', 'postgres')
        db_port = os.getenv('POSTGRES_PORT', '5432')
        db_name = os.getenv('POSTGRES_DB', 'analytics')
        
        self.db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        self.engine = create_engine(self.db_url)
        
        self.validation_results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
    
    def load_data(self, schema: str = 'raw', table: str = 'commits') -> pd.DataFrame:
        """Load data from PostgreSQL"""
        logger.info(f"Loading data from {schema}.{table}")
        
        try:
            query = f"SELECT * FROM {schema}.{table}"
            df = pd.read_sql(query, self.engine)
            logger.info(f"Loaded {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            raise
    
    def validate_schema(self, df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """
        Schema Validation: Verify data conforms to expected schema
        """
        logger.info("Running schema validation...")
        
        required_columns = [
            'commit_sha', 'author_name', 'author_email', 'author_date',
            'committer_name', 'committer_email', 'committer_date',
            'commit_message', 'comment_count'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            result = {
                'check': 'schema_validation',
                'status': 'FAILED',
                'message': f"Missing required columns: {missing_columns}",
                'details': {
                    'expected_columns': required_columns,
                    'actual_columns': list(df.columns),
                    'missing': missing_columns
                }
            }
            logger.error(f"Schema validation failed: {missing_columns}")
            self.validation_results['failed'].append(result)
            return False, result
        
        # Validate data types
        type_errors = []
        
        # Check SHA format
        invalid_shas = df[~df['commit_sha'].str.match(r'^[a-f0-9]{40}$', na=False)]
        if len(invalid_shas) > 0:
            type_errors.append(f"{len(invalid_shas)} invalid SHA hashes")
        
        # Check date columns
        for date_col in ['author_date', 'committer_date']:
            if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
                type_errors.append(f"{date_col} is not datetime type")
        
        # Check numeric columns
        if not pd.api.types.is_numeric_dtype(df['comment_count']):
            type_errors.append("comment_count is not numeric type")
        
        if type_errors:
            result = {
                'check': 'schema_validation',
                'status': 'FAILED',
                'message': f"Data type validation errors: {type_errors}",
                'details': {'type_errors': type_errors}
            }
            logger.error(f"Schema validation failed: {type_errors}")
            self.validation_results['failed'].append(result)
            return False, result
        
        result = {
            'check': 'schema_validation',
            'status': 'PASSED',
            'message': 'All required columns present with correct types',
            'details': {'validated_columns': required_columns}
        }
        logger.info("✓ Schema validation passed")
        self.validation_results['passed'].append(result)
        return True, result
    
    def validate_nulls(self, df: pd.DataFrame, threshold: float = 0.05) -> Tuple[bool, Dict[str, Any]]:
        """
        Null Check: Ensure critical columns have no or minimal null values
        """
        logger.info("Running null value validation...")
        
        critical_columns = [
            'commit_sha', 'author_name', 'author_email', 'author_date',
            'committer_name', 'committer_email', 'committer_date', 'commit_message'
        ]
        
        null_report = {}
        has_critical_nulls = False
        
        for col in critical_columns:
            if col in df.columns:
                null_count = df[col].isna().sum()
                null_percentage = (null_count / len(df)) * 100
                
                null_report[col] = {
                    'null_count': int(null_count),
                    'null_percentage': round(null_percentage, 2),
                    'total_rows': len(df)
                }
                
                if null_percentage > threshold * 100:
                    has_critical_nulls = True
        
        if has_critical_nulls:
            result = {
                'check': 'null_validation',
                'status': 'FAILED',
                'message': f"Critical columns have >={threshold * 100}% null values",
                'details': null_report
            }
            logger.error(f"Null validation failed: {null_report}")
            self.validation_results['failed'].append(result)
            return False, result
        
        result = {
            'check': 'null_validation',
            'status': 'PASSED',
            'message': 'Null values within acceptable threshold',
            'details': null_report
        }
        logger.info("✓ Null validation passed")
        self.validation_results['passed'].append(result)
        return True, result
    
    def validate_duplicates(self, df: pd.DataFrame, primary_key: str = 'commit_sha') -> Tuple[bool, Dict[str, Any]]:
        """
        Duplicate Detection: Check for duplicate records based on primary key
        """
        logger.info("Running duplicate detection...")
        
        if primary_key not in df.columns:
            result = {
                'check': 'duplicate_detection',
                'status': 'FAILED',
                'message': f"Primary key column '{primary_key}' not found",
                'details': {}
            }
            logger.error(result['message'])
            self.validation_results['failed'].append(result)
            return False, result
        
        duplicate_count = df[primary_key].duplicated().sum()
        duplicate_percentage = (duplicate_count / len(df)) * 100
        
        if duplicate_count > 0:
            # Get sample duplicates
            duplicate_values = df[df[primary_key].duplicated(keep=False)][primary_key].unique()[:5]
            
            result = {
                'check': 'duplicate_detection',
                'status': 'WARNING',
                'message': f"Found {duplicate_count} duplicate records ({duplicate_percentage:.2f}%)",
                'details': {
                    'duplicate_count': int(duplicate_count),
                    'duplicate_percentage': round(duplicate_percentage, 2),
                    'total_rows': len(df),
                    'sample_duplicates': list(duplicate_values)
                }
            }
            logger.warning(f"⚠ Duplicate detection: {duplicate_count} duplicates found")
            self.validation_results['warnings'].append(result)
            return True, result  # Warning, not failure
        
        result = {
            'check': 'duplicate_detection',
            'status': 'PASSED',
            'message': 'No duplicate records found',
            'details': {
                'duplicate_count': 0,
                'total_rows': len(df)
            }
        }
        logger.info("✓ Duplicate detection passed")
        self.validation_results['passed'].append(result)
        return True, result
    
    def validate_row_count(self, df: pd.DataFrame, min_rows: int = 10) -> Tuple[bool, Dict[str, Any]]:
        """
        Row Count Check: Ensure minimum number of rows are present
        """
        logger.info("Running row count validation...")
        
        row_count = len(df)
        
        if row_count < min_rows:
            result = {
                'check': 'row_count_validation',
                'status': 'FAILED',
                'message': f"Insufficient rows: {row_count} < {min_rows} (minimum)",
                'details': {
                    'actual_rows': row_count,
                    'minimum_required': min_rows
                }
            }
            logger.error(result['message'])
            self.validation_results['failed'].append(result)
            return False, result
        
        result = {
            'check': 'row_count_validation',
            'status': 'PASSED',
            'message': f"Row count meets minimum requirement: {row_count} >= {min_rows}",
            'details': {
                'actual_rows': row_count,
                'minimum_required': min_rows
            }
        }
        logger.info("✓ Row count validation passed")
        self.validation_results['passed'].append(result)
        return True, result
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        total_checks = (
            len(self.validation_results['passed']) +
            len(self.validation_results['failed']) +
            len(self.validation_results['warnings'])
        )
        
        report = {
            'summary': {
                'total_checks': total_checks,
                'passed': len(self.validation_results['passed']),
                'failed': len(self.validation_results['failed']),
                'warnings': len(self.validation_results['warnings']),
                'success_rate': round(
                    (len(self.validation_results['passed']) / total_checks * 100) if total_checks > 0 else 0,
                    2
                )
            },
            'results': self.validation_results,
            'timestamp': datetime.now().isoformat()
        }
        
        return report
    
    def run(self, fail_on_error: bool = True) -> bool:
        """Execute all data quality validations"""
        logger.info("=" * 60)
        logger.info("Starting Data Quality Validation")
        logger.info("=" * 60)
        
        try:
            # Load data
            df = self.load_data()
            
            # Run all validations
            self.validate_schema(df)
            self.validate_nulls(df)
            self.validate_duplicates(df)
            self.validate_row_count(df)
            
            # Generate report
            report = self.generate_report()
            
            logger.info("=" * 60)
            logger.info("Data Quality Validation Summary")
            logger.info("=" * 60)
            logger.info(f"Total Checks: {report['summary']['total_checks']}")
            logger.info(f"Passed: {report['summary']['passed']}")
            logger.info(f"Failed: {report['summary']['failed']}")
            logger.info(f"Warnings: {report['summary']['warnings']}")
            logger.info(f"Success Rate: {report['summary']['success_rate']}%")
            logger.info("=" * 60)
            
            # Determine overall status
            has_failures = len(self.validation_results['failed']) > 0
            
            if has_failures and fail_on_error:
                logger.error("❌ Data quality validation FAILED")
                logger.error("Failed checks:")
                for failure in self.validation_results['failed']:
                    logger.error(f"  - {failure['check']}: {failure['message']}")
                raise ValueError("Data quality validation failed - pipeline stopped")
            
            if has_failures:
                logger.warning("⚠ Data quality validation completed with failures")
                return False
            
            logger.info("✓ Data Quality Validation Passed")
            return True
        
        except Exception as e:
            logger.error(f"Data quality validation error: {e}")
            raise


if __name__ == "__main__":
    validator = DataQualityValidator()
    validator.run(fail_on_error=True)
