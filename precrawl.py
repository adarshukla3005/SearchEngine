"""
Pre-crawl seed URLs to build a cache for faster search results
"""
import os
import sys
import argparse
import logging
import time
from scripts.crawl_seed_urls import crawl_urls
from config import GOOGLE_SEARCH_CONFIG, SEED_URLS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("google_search.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("precrawl")

def main():
    """
    Main function to run the pre-crawl process
    """
    parser = argparse.ArgumentParser(description='Pre-crawl seed URLs to build a cache for faster search results')
    parser.add_argument('--depth', type=int, default=2, help='Maximum crawl depth (default: 2)')
    parser.add_argument('--timeout', type=int, default=15, help='Request timeout in seconds (default: 15)')
    parser.add_argument('--workers', type=int, default=10, help='Number of parallel workers (default: 10)')
    parser.add_argument('--max-retries', type=int, default=3, help='Maximum number of retries for failed requests (default: 3)')
    parser.add_argument('--pool-connections', type=int, default=50, help='Maximum number of connections in the pool (default: 50)')
    parser.add_argument('--pool-maxsize', type=int, default=50, help='Maximum number of connections in the pool (default: 50)')
    args = parser.parse_args()
    
    # Create necessary directories
    os.makedirs("data/google_cache", exist_ok=True)
    
    # Update config for better crawling
    config = GOOGLE_SEARCH_CONFIG.copy()
    config["max_workers"] = args.workers
    config["request_timeout"] = args.timeout
    config["max_retries"] = args.max_retries
    config["pool_connections"] = args.pool_connections
    config["pool_maxsize"] = args.pool_maxsize
    
    # Ensure seed URLs are in config
    if "seed_urls" not in config:
        config["seed_urls"] = SEED_URLS
    
    print(f"Starting pre-crawl with depth={args.depth}, timeout={args.timeout}, workers={args.workers}")
    print(f"Connection pool settings: max_retries={args.max_retries}, pool_connections={args.pool_connections}, pool_maxsize={args.pool_maxsize}")
    print(f"Using {len(config['seed_urls'])} seed URLs from config")
    
    # Track time
    start_time = time.time()
    
    try:
        # Crawl URLs
        success = crawl_urls(config, max_depth=args.depth, timeout=args.timeout)
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        
        if success:
            logger.info(f"Pre-crawl completed successfully in {elapsed_time:.2f} seconds. Cache is ready for faster searches.")
            print(f"Pre-crawl completed successfully in {elapsed_time:.2f} seconds. Cache is ready for faster searches.")
        else:
            logger.error(f"Pre-crawl failed after {elapsed_time:.2f} seconds.")
            print(f"Pre-crawl failed after {elapsed_time:.2f} seconds.")
            sys.exit(1)
    except KeyboardInterrupt:
        elapsed_time = time.time() - start_time
        logger.warning(f"Pre-crawl interrupted by user after {elapsed_time:.2f} seconds.")
        print(f"Pre-crawl interrupted by user after {elapsed_time:.2f} seconds.")
        sys.exit(2)
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Pre-crawl failed with error after {elapsed_time:.2f} seconds: {e}")
        print(f"Pre-crawl failed with error after {elapsed_time:.2f} seconds: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 