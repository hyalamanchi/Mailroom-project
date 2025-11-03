#!/bin/bash

# Run the essential pipeline with retries and proper logging
MAX_RETRIES=3
RETRY_DELAY=5

echo "🚀 Starting CP2000 Pipeline..."

# Create log directory
mkdir -p logs

# Get timestamp for log files
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="logs/pipeline_${TIMESTAMP}.log"

# Run with retries
for ((i=1; i<=$MAX_RETRIES; i++)); do
    echo "📄 Log file: $LOG_FILE"
    echo "🔄 Attempt $i of $MAX_RETRIES"
    
    python3 automated_pipeline.py 2>&1 | tee -a "$LOG_FILE"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo "✅ Pipeline completed successfully!"
        exit 0
    fi
    
    if [ $i -lt $MAX_RETRIES ]; then
        echo "⚠️ Pipeline failed, retrying in $RETRY_DELAY seconds..."
        sleep $RETRY_DELAY
    fi
done

echo "❌ Pipeline failed after $MAX_RETRIES attempts"
echo "📋 Check logs at: $LOG_FILE"
exit 1