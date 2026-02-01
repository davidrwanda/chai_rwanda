#!/bin/bash
set -e

echo "============================================================"
echo "Starting Complete Data Pipeline"
echo "============================================================"

echo ""
echo "Stage 1: Data Ingestion"
python /app/src/ingestion.py

echo ""
echo "Stage 2: Data Transformation"
python /app/src/transformation.py

echo ""
echo "Stage 3: Data Validation"
python /app/src/validation.py

echo ""
echo "Stage 4: ML Pipeline"
python /app/src/ml_pipeline.py

echo ""
echo "============================================================"
echo "Complete Pipeline Finished Successfully"
echo "============================================================"
