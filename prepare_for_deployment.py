#!/usr/bin/env python
"""
Script to prepare the search engine for deployment by creating an optimized index
"""
import os
import sys
import shutil
import logging
from pathlib import Path

# Add the current directory to the path to find modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from search_engine.indexer.optimized_indexer import OptimizedSearchIndexer
from utils.config import INDEXER_CONFIG, DEPLOYMENT_CONFIG

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("deployment_prep.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("deployment_prep")

def main():
    """
    Main function to prepare for deployment
    """
    # Check if the original index exists
    source_index_dir = INDEXER_CONFIG["index_dir"]
    if not os.path.exists(os.path.join(source_index_dir, "document_map.json")):
        logger.error(f"Original index not found at {source_index_dir}")
        logger.error("Please run the indexer first to create the index.")
        sys.exit(1)
    
    # Create optimized index directory
    optimized_index_dir = DEPLOYMENT_CONFIG["optimized_index_dir"]
    os.makedirs(optimized_index_dir, exist_ok=True)
    
    # Create optimized indexer with modified config
    optimized_config = INDEXER_CONFIG.copy()
    optimized_config["index_dir"] = optimized_index_dir
    
    # Create optimized indexer
    indexer = OptimizedSearchIndexer(optimized_config)
    
    try:
        # Optimize from existing index
        logger.info(f"Creating optimized index from {source_index_dir} to {optimized_index_dir}")
        indexer.optimize_from_existing(source_index_dir)
        
        # Check the size of the optimized index
        total_size = 0
        for path in Path(optimized_index_dir).rglob('*'):
            if path.is_file():
                file_size = path.stat().st_size
                total_size += file_size
                logger.info(f"File: {path.name}, Size: {file_size / (1024 * 1024):.2f} MB")
        
        logger.info(f"Total optimized index size: {total_size / (1024 * 1024):.2f} MB")
        
        # Ensure stopwords file is available
        stopwords_file = INDEXER_CONFIG["stopwords_file"]
        if os.path.exists(stopwords_file):
            # Copy stopwords file to optimized index directory for deployment
            shutil.copy(stopwords_file, os.path.join(optimized_index_dir, "stopwords.txt"))
            logger.info(f"Copied stopwords file to {optimized_index_dir}")
        else:
            logger.warning(f"Stopwords file not found at {stopwords_file}")
            # Create an empty stopwords file if it doesn't exist
            with open(os.path.join(optimized_index_dir, "stopwords.txt"), 'w') as f:
                logger.info("Created empty stopwords file in optimized index directory")
        
        logger.info("Deployment preparation completed successfully!")
        logger.info("Your optimized index is ready for deployment.")
        logger.info(f"Make sure to set the PRODUCTION environment variable to 'true' in your deployment environment.")
        
        # Test loading the optimized index
        try:
            logger.info("Testing optimized index loading...")
            test_indexer = OptimizedSearchIndexer(optimized_config)
            test_indexer.load_optimized_index()
            logger.info(f"Successfully loaded optimized index with {len(test_indexer.document_map)} documents")
        except Exception as e:
            logger.error(f"Error testing optimized index: {e}")
            logger.error("The optimized index may not load correctly in production.")
            
    except Exception as e:
        logger.error(f"Error preparing for deployment: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 