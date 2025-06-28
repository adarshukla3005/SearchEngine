"""
Script to generate BERT embeddings for all documents in the index
"""
import os
import sys
import json
import logging
import time

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from search_engine.indexer.bert_embeddings import BertEmbeddings
from utils.config import BERT_CONFIG, DEPLOYMENT_CONFIG

def main():
    """
    Generate BERT embeddings for all documents in the index
    """
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("generate_bert_embeddings.log"),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger("generate_bert_embeddings")
    
    # Start timer
    start_time = time.time()
    
    try:
        # Load document map from optimized index
        index_dir = DEPLOYMENT_CONFIG["optimized_index_dir"]
        document_map_file = os.path.join(index_dir, "document_map.json")
        
        if not os.path.exists(document_map_file):
            logger.error(f"Document map file not found: {document_map_file}")
            logger.error("Make sure to run optimize_index.py first!")
            sys.exit(1)
        
        logger.info(f"Loading document map from {document_map_file}")
        with open(document_map_file, 'r', encoding='utf-8') as f:
            document_map = json.load(f)
        
        logger.info(f"Loaded {len(document_map)} documents")
        
        # Initialize BERT embeddings generator
        bert_embeddings = BertEmbeddings(BERT_CONFIG)
        
        # Generate embeddings
        bert_embeddings.generate_embeddings(document_map)
        
        # End timer
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        logger.info(f"BERT embeddings generation completed in {elapsed_time:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Error generating BERT embeddings: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 