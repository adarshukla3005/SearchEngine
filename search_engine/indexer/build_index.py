"""
Script to build the search index
"""
import os
import sys
import argparse

# Add parent directory to path to import from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from search_engine.indexer.indexer import SearchIndexer
from utils.config import INDEXER_CONFIG, CRAWLER_CONFIG

def main():
    """
    Main function to build the search index
    """
    parser = argparse.ArgumentParser(description='Build the search index')
    parser.add_argument('--input-dir', type=str, default=CRAWLER_CONFIG["data_dir"],
                        help='Directory containing crawled pages')
    parser.add_argument('--index-dir', type=str, default=INDEXER_CONFIG["index_dir"],
                        help='Directory to save the index')
    parser.add_argument('--chunk-size', type=int, default=INDEXER_CONFIG["chunk_size"],
                        help='Chunk size for processing')
    args = parser.parse_args()
    
    # Update config with command-line arguments
    config = INDEXER_CONFIG.copy()
    config["index_dir"] = args.index_dir
    config["chunk_size"] = args.chunk_size
    
    # Create index directory if it doesn't exist
    os.makedirs(config["index_dir"], exist_ok=True)
    
    # Create stopwords file if it doesn't exist
    if not os.path.exists(config["stopwords_file"]):
        os.makedirs(os.path.dirname(config["stopwords_file"]), exist_ok=True)
        with open(config["stopwords_file"], 'w', encoding='utf-8') as f:
            # Common English stopwords
            stopwords = [
                "a", "an", "the", "and", "or", "but", "if", "because", "as", "what",
                "when", "where", "how", "who", "which", "this", "that", "these", "those",
                "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
                "do", "does", "did", "for", "of", "on", "in", "to", "from", "with"
            ]
            f.write("\n".join(stopwords))
    
    # Build index
    indexer = SearchIndexer(config)
    indexer.build_index_from_crawled(args.input_dir)

if __name__ == "__main__":
    main() 