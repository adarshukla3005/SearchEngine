#!/bin/bash
set -e

echo "Checking directory structure..."
ls -la
echo "Checking data directory..."
ls -la data/
echo "Checking optimized index directory..."
ls -la data/optimized_index/

echo "Running verification script..."
python verify_index.py

if [ $? -ne 0 ]; then
    echo "Index verification failed! Please check the logs."
    exit 1
fi

echo "Starting search engine in production mode..."
export PRODUCTION=true
gunicorn -c gunicorn.conf.py app:app 