#!/usr/bin/env python
"""
Script to check if all required files for deployment are present
"""
import os
import sys
import logging
from pathlib import Path

# Add the current directory to the path to find modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from utils.config import DEPLOYMENT_CONFIG

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("deployment_check")

def check_files():
    """Check if all required files for deployment are present"""
    required_files = [
        "app.py",
        "gunicorn.conf.py",
        "requirements.txt",
        "runtime.txt",
        "web/templates/index.html",
        "web/templates/search_results.html",
        "web/static/css/style.css",
        "web/static/js/main.js",
        "search_engine/indexer/optimized_indexer.py",
        "utils/config.py",
        "utils/text_processing.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        logger.error("Missing required files for deployment:")
        for file_path in missing_files:
            logger.error(f"  - {file_path}")
        return False
    
    logger.info("All required files for deployment are present.")
    return True

def check_optimized_index():
    """Check if the optimized index files are present"""
    optimized_index_dir = DEPLOYMENT_CONFIG["optimized_index_dir"]
    required_index_files = [
        "document_map.json",
        "inverted_index.pkl.gz",
        "document_lengths.pkl.gz",
        "average_doc_length.txt",
        "stopwords.txt"
    ]
    
    missing_files = []
    for file_name in required_index_files:
        file_path = os.path.join(optimized_index_dir, file_name)
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        logger.error("Missing required optimized index files:")
        for file_path in missing_files:
            logger.error(f"  - {file_path}")
        logger.error("Run prepare_for_deployment.py to create the optimized index.")
        return False
    
    # Check the size of the optimized index
    total_size = 0
    for path in Path(optimized_index_dir).rglob('*'):
        if path.is_file():
            file_size = path.stat().st_size
            total_size += file_size
            logger.info(f"File: {path.name}, Size: {file_size / (1024 * 1024):.2f} MB")
    
    logger.info(f"Total optimized index size: {total_size / (1024 * 1024):.2f} MB")
    logger.info("Optimized index files are present and ready for deployment.")
    return True

def check_gitignore():
    """Check if .gitignore is properly configured for deployment"""
    if not os.path.exists(".gitignore"):
        logger.warning("No .gitignore file found.")
        return False
    
    with open(".gitignore", "r") as f:
        gitignore_content = f.read()
    
    required_patterns = [
        "!data/optimized_index/",
        "!data/optimized_index/*",
        "!data/stopwords.txt"
    ]
    
    missing_patterns = []
    for pattern in required_patterns:
        if pattern not in gitignore_content:
            missing_patterns.append(pattern)
    
    if missing_patterns:
        logger.error("Missing required patterns in .gitignore:")
        for pattern in missing_patterns:
            logger.error(f"  - {pattern}")
        return False
    
    logger.info(".gitignore is properly configured for deployment.")
    return True

def main():
    """Main function to check deployment readiness"""
    logger.info("Checking deployment readiness...")
    
    files_ok = check_files()
    index_ok = check_optimized_index()
    gitignore_ok = check_gitignore()
    
    if files_ok and index_ok and gitignore_ok:
        logger.info("All checks passed! Your project is ready for deployment.")
        return True
    else:
        logger.error("Some checks failed. Please fix the issues before deployment.")
        return False

if __name__ == "__main__":
    main() 