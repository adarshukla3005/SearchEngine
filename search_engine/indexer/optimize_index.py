"""
Script to create an optimized search index for deployment
"""
import os
import sys
import logging
from typing import Dict, List, Set

# Add the current directory to the path to find modules
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from search_engine.indexer.optimized_indexer import OptimizedSearchIndexer
from utils.config import INDEXER_CONFIG, DEPLOYMENT_CONFIG

def truncate_content_snippet(snippet: str, max_chars: int = 200) -> str:
    """
    Truncate content snippet to a reasonable size (2-3 lines or max_chars)
    """
    if not snippet:
        return ""
    
    # Count up to 3 newlines or max_chars characters
    end_pos = 0
    newline_count = 0
    
    for i, char in enumerate(snippet):
        if char == '\n':
            newline_count += 1
            if newline_count >= 3:  # Limit to 3 lines
                end_pos = i
                break
        if i >= max_chars:  # Maximum characters
            end_pos = i
            break
    
    # If we found a cutoff point, truncate the snippet
    if end_pos > 0:
        return snippet[:end_pos] + "..."
    elif len(snippet) > max_chars:
        return snippet[:max_chars] + "..."
    
    return snippet

def optimize_index():
    """
    Optimize the index for deployment
    """
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
    
    # Create optimized indexer
    optimized_config = INDEXER_CONFIG.copy()
    optimized_config["index_dir"] = DEPLOYMENT_CONFIG["optimized_index_dir"]
    
    indexer = OptimizedSearchIndexer(optimized_config)
    
    try:
        # Load existing index and optimize it
        source_index_dir = INDEXER_CONFIG["index_dir"]
        
        logger.info(f"Optimizing index from {source_index_dir} to {optimized_config['index_dir']}")
        
        # Custom optimization: truncate content snippets before optimization
        logger.info("Loading source index for custom optimization...")
        
        # Load document map from source index
        import json
        with open(os.path.join(source_index_dir, "document_map.json"), 'r', encoding='utf-8') as f:
            document_map = json.load(f)
        
        # Truncate content snippets
        logger.info(f"Truncating content snippets for {len(document_map)} documents...")
        for doc_id in document_map:
            if "content_snippet" in document_map[doc_id]:
                document_map[doc_id]["content_snippet"] = truncate_content_snippet(
                    document_map[doc_id]["content_snippet"]
                )
        
        # Save modified document map back to source index
        with open(os.path.join(source_index_dir, "document_map.json"), 'w', encoding='utf-8') as f:
            json.dump(document_map, f, ensure_ascii=False)
        
        logger.info("Content snippets truncated successfully")
        
        # Now optimize the index
        indexer.optimize_from_existing(source_index_dir)
        
        logger.info("Index optimization completed successfully")
        
    except Exception as e:
        logger.error(f"Error optimizing index: {e}")
        raise

if __name__ == "__main__":
    optimize_index() 