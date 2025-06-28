#!/usr/bin/env python
"""
Script to verify the optimized index files on Render
"""
import os
import sys
import gzip
import json
import pickle
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("verify_index")

def verify_index():
    """Verify the optimized index files"""
    # Set the optimized index directory
    optimized_index_dir = "data/optimized_index"
    
    # Check if the directory exists
    if not os.path.exists(optimized_index_dir):
        logger.error(f"Optimized index directory not found: {optimized_index_dir}")
        return False
    
    # List all files in the directory without printing each one
    files = list(Path(optimized_index_dir).rglob('*'))
    file_count = sum(1 for f in files if f.is_file())
    total_size = sum(f.stat().st_size for f in files if f.is_file())
    logger.info(f"Found {file_count} files in {optimized_index_dir} ({total_size / 1024 / 1024:.2f} MB total)")
    
    # Check required files
    required_files = [
        "document_map.json",
        "inverted_index.pkl.gz",
        "document_lengths.pkl.gz",
        "average_doc_length.txt",
        "stopwords.txt"
    ]
    
    missing_files = []
    for file_name in required_files:
        file_path = os.path.join(optimized_index_dir, file_name)
        if not os.path.exists(file_path):
            missing_files.append(file_name)
    
    if missing_files:
        logger.error("Missing required optimized index files:")
        for file_name in missing_files:
            logger.error(f"  - {file_name}")
        return False
    
    # Try to load each file
    try:
        # Load document map
        with open(os.path.join(optimized_index_dir, "document_map.json"), 'r', encoding='utf-8') as f:
            document_map = json.load(f)
            logger.info(f"Document map loaded with {len(document_map)} documents")
        
        # Load inverted index
        with gzip.open(os.path.join(optimized_index_dir, "inverted_index.pkl.gz"), 'rb') as f:
            inverted_index = pickle.load(f)
            logger.info(f"Inverted index loaded with {len(inverted_index)} terms")
        
        # Load document lengths
        with gzip.open(os.path.join(optimized_index_dir, "document_lengths.pkl.gz"), 'rb') as f:
            document_lengths = pickle.load(f)
            logger.info(f"Document lengths loaded with {len(document_lengths)} entries")
        
        # Load average document length
        with open(os.path.join(optimized_index_dir, "average_doc_length.txt"), 'r') as f:
            average_doc_length = float(f.read().strip())
            logger.info(f"Average document length: {average_doc_length}")
        
        logger.info("All optimized index files loaded successfully!")
        return True
    
    except Exception as e:
        logger.error(f"Error loading optimized index files: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def check_embeddings():
    """Check BERT embeddings files"""
    embeddings_dir = "data/embeddings"
    
    if not os.path.exists(embeddings_dir):
        logger.warning(f"Embeddings directory not found: {embeddings_dir}")
        return False
    
    # List all files in the directory without printing each one
    files = list(Path(embeddings_dir).rglob('*'))
    file_count = sum(1 for f in files if f.is_file())
    total_size = sum(f.stat().st_size for f in files if f.is_file())
    logger.info(f"Found {file_count} files in {embeddings_dir} ({total_size / 1024 / 1024:.2f} MB total)")
    
    # Check required files
    required_files = [
        "faiss_index.bin",
        "doc_ids.json"
    ]
    
    missing_files = []
    for file_name in required_files:
        file_path = os.path.join(embeddings_dir, file_name)
        if not os.path.exists(file_path):
            missing_files.append(file_name)
    
    if missing_files:
        logger.warning("Missing required embeddings files:")
        for file_name in missing_files:
            logger.warning(f"  - {file_name}")
        return False
    
    logger.info("Embeddings files found!")
    return True

if __name__ == "__main__":
    logger.info("Verifying optimized index files...")
    index_ok = verify_index()
    embeddings_ok = check_embeddings()
    
    if index_ok:
        logger.info("Optimized index verification passed!")
    else:
        logger.error("Optimized index verification failed!")
    
    if embeddings_ok:
        logger.info("Embeddings verification passed!")
    else:
        logger.warning("Embeddings verification failed or not found!")
    
    sys.exit(0 if index_ok else 1) 