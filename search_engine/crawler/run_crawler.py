"""
Script to run the web crawler
"""
import os
import sys
import argparse
import logging
from tqdm import tqdm

# Add parent directory to path to import from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from search_engine.crawler.crawler import Crawler
from utils.config import CRAWLER_CONFIG

# Set up logging with more visible format
logging.basicConfig(
    level=logging.INFO,
    format='\033[1;36m%(asctime)s - %(name)s - %(levelname)s - %(message)s\033[0m',
    handlers=[
        logging.FileHandler("crawler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("run_crawler")

def main():
    """
    Main function to run the crawler
    """
    parser = argparse.ArgumentParser(description='Run the web crawler')
    parser.add_argument('--max-pages', type=int, default=CRAWLER_CONFIG["max_pages"],
                        help='Maximum number of pages to crawl')
    parser.add_argument('--max-depth', type=int, default=CRAWLER_CONFIG["max_depth"],
                        help='Maximum depth to crawl from seed URLs')
    parser.add_argument('--rate-limit', type=float, default=CRAWLER_CONFIG["rate_limit"],
                        help='Time to wait between requests (seconds)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show verbose output during crawling')
    args = parser.parse_args()
    
    # Update config with command-line arguments
    config = CRAWLER_CONFIG.copy()
    config["max_pages"] = args.max_pages
    config["max_depth"] = args.max_depth
    config["rate_limit"] = args.rate_limit
    config["verbose"] = args.verbose
    
    # Create data directory if it doesn't exist
    os.makedirs(config["data_dir"], exist_ok=True)
    
    # Show seed URLs
    logger.info(f"Starting crawler with {len(config['seed_urls'])} seed URLs")
    for i, url in enumerate(config['seed_urls']):
        logger.info(f"Seed URL {i+1}: {url}")
    
    # Run crawler
    logger.info(f"Will crawl up to {config['max_pages']} pages with max depth {config['max_depth']}")
    logger.info(f"Rate limit: {config['rate_limit']} seconds between requests")
    
    print("\n" + "="*80)
    print(" "*30 + "STARTING CRAWLER")
    print("="*80 + "\n")
    
    crawler = Crawler(config)
    crawler.crawl()
    
    print("\n" + "="*80)
    print(" "*30 + "CRAWLING COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    main() 