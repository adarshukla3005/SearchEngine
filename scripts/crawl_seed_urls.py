"""
Pre-crawl seed URLs to build a cache for faster search results
"""
import os
import sys
import time
import logging
import argparse

# Add parent directory to path to import from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import from config
from config import GOOGLE_SEARCH_CONFIG
from scripts.blog_crawler import BlogCrawler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("google_search.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("crawl_seed_urls")

def crawl_urls(config, max_depth=2, timeout=15):
    """
    Crawl all seed URLs and their linked blogs
    
    Args:
        config: Configuration dictionary
        max_depth: Maximum crawl depth (default: 2)
        timeout: Request timeout in seconds (default: 15)
        
    Returns:
        bool: True if crawl was successful, False otherwise
    """
    try:
        # Update config for better crawling
        config["request_timeout"] = timeout
        config["max_crawl_depth"] = max_depth
        
        # Initialize crawler
        crawler = BlogCrawler(config)
        
        # Get seed URLs from config
        seed_urls = config.get("seed_urls", [])
        if not seed_urls:
            logger.error("No seed URLs found in config. Exiting.")
            return False
        
        # Start crawling
        logger.info(f"Starting crawl of {len(seed_urls)} seed URLs with depth {max_depth}")
        start_time = time.time()
        
        # Crawl seed URLs
        discovered_blogs = crawler.crawl_seed_urls(seed_urls)
        
        # Log results
        crawl_time = time.time() - start_time
        logger.info(f"Crawl completed in {crawl_time:.2f} seconds")
        logger.info(f"Discovered {len(discovered_blogs)} blogs")
        
        return True
    except KeyboardInterrupt:
        logger.warning("Crawl interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Error during crawl: {e}")
        return False

def main():
    """
    Main function
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
    config["max_retries"] = args.max_retries
    config["pool_connections"] = args.pool_connections
    config["pool_maxsize"] = args.pool_maxsize
    
    # Display crawl settings
    logger.info(f"Starting crawl with depth={args.depth}, timeout={args.timeout}, workers={args.workers}")
    logger.info(f"Connection pool settings: max_retries={args.max_retries}, pool_connections={args.pool_connections}, pool_maxsize={args.pool_maxsize}")
    
    # Track time
    start_time = time.time()
    
    try:
        # Crawl URLs
        success = crawl_urls(config, max_depth=args.depth, timeout=args.timeout)
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        
        if success:
            logger.info(f"Crawl completed successfully in {elapsed_time:.2f} seconds")
        else:
            logger.error(f"Crawl failed after {elapsed_time:.2f} seconds")
            sys.exit(1)
    except KeyboardInterrupt:
        elapsed_time = time.time() - start_time
        logger.warning(f"Crawl interrupted by user after {elapsed_time:.2f} seconds")
        sys.exit(2)
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Crawl failed with error after {elapsed_time:.2f} seconds: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 