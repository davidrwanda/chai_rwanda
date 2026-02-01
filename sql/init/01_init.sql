-- Create MLflow database for experiment tracking
CREATE DATABASE mlflow;

-- Create schemas for data organization
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE analytics TO dataplatform;
GRANT ALL PRIVILEGES ON DATABASE mlflow TO dataplatform;
GRANT ALL PRIVILEGES ON SCHEMA raw TO dataplatform;
GRANT ALL PRIVILEGES ON SCHEMA staging TO dataplatform;
GRANT ALL PRIVILEGES ON SCHEMA analytics TO dataplatform;
