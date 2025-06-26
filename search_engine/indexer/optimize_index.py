"""
Script to create an optimized search index for deployment
"""
import os
import sys
import logging

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from search_engine.indexer.optimized_indexer import OptimizedSearchIndexer
from utils.config import INDEXER_CONFIG

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("optimize_index.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("optimize_index")

def main():
    """
    Main function to optimize the index
    """
    # Source index directory (original index)
    source_index_dir = INDEXER_CONFIG["index_dir"]
    
    # Target index directory (optimized index)
    target_index_dir = os.path.join(os.path.dirname(INDEXER_CONFIG["index_dir"]), "optimized_index")
    
    # Create optimized indexer with modified config
    optimized_config = INDEXER_CONFIG.copy()
    optimized_config["index_dir"] = target_index_dir
    
    # Create optimized indexer
    indexer = OptimizedSearchIndexer(optimized_config)
    
    try:
        # Optimize from existing index
        logger.info(f"Optimizing index from {source_index_dir} to {target_index_dir}")
        indexer.optimize_from_existing(source_index_dir)
        
        logger.info("Index optimization completed successfully")
        
    except Exception as e:
        logger.error(f"Error optimizing index: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 