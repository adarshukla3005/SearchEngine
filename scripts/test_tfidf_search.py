"""
Test script for TF-IDF search integration
"""
import os
import sys
import time
import logging
from typing import List, Dict

# Add parent directory to path to import from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import from config
from config import GOOGLE_SEARCH_CONFIG

# Import the search integrations
from scripts.fast_tfidf_search import FastTFIDFSearchIntegration
from scripts.fast_google_search import FastGoogleSearchIntegration

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("google_search.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_tfidf_search")

def format_result(result: Dict) -> str:
    """
    Format a search result for display
    """
    return (
        f"URL: {result['url']}\n"
        f"Title: {result['title']}\n"
        f"Is Blog/Article: {result['is_blog_article']}\n"
        f"Score: {result['score']:.2f}\n"
        f"Description: {result['description'][:100]}...\n"
    )

def run_test(query: str) -> None:
    """
    Run a test search with both TF-IDF and regular search
    """
    print(f"\n{'='*80}\nTesting search for: '{query}'\n{'='*80}")
    
    # Initialize search integrations
    tfidf_search = FastTFIDFSearchIntegration(GOOGLE_SEARCH_CONFIG)
    regular_search = FastGoogleSearchIntegration(GOOGLE_SEARCH_CONFIG)
    
    # Test TF-IDF search
    print("\n--- TF-IDF Search Results ---\n")
    start_time = time.time()
    tfidf_results = tfidf_search.search_google(query, num_results=5)
    tfidf_time = time.time() - start_time
    
    for i, result in enumerate(tfidf_results):
        print(f"\nResult {i+1}:")
        print(format_result(result))
    
    print(f"\nTF-IDF Search completed in {tfidf_time:.2f} seconds")
    
    # Test regular search
    print("\n--- Regular Fast Search Results ---\n")
    start_time = time.time()
    regular_results = regular_search.search_google(query, num_results=5)
    regular_time = time.time() - start_time
    
    for i, result in enumerate(regular_results):
        print(f"\nResult {i+1}:")
        print(format_result(result))
    
    print(f"\nRegular Search completed in {regular_time:.2f} seconds")
    
    # Print comparison
    print("\n--- Performance Comparison ---\n")
    print(f"TF-IDF Search: {tfidf_time:.2f} seconds")
    print(f"Regular Search: {regular_time:.2f} seconds")
    print(f"Difference: {regular_time - tfidf_time:.2f} seconds")

def main() -> None:
    """
    Main function to run the test
    """
    # Create necessary directories
    os.makedirs("data/google_cache", exist_ok=True)
    
    # Test queries
    queries = [
        "productivity tips",
        "best programming blogs",
        "data science tutorials",
        "machine learning articles"
    ]
    
    # Run tests
    for query in queries:
        run_test(query)
        print("\nWaiting 2 seconds before next query...\n")
        time.sleep(2)

if __name__ == "__main__":
    main() 