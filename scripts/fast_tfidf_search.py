"""
Fast Google search integration with TF-IDF validation for the search engine
"""
import os
import json
import logging
import time
import concurrent.futures
from typing import Dict, List, Optional
import requests
from googlesearch import search
from dotenv import load_dotenv

# Import TF-IDF validator
from scripts.tfidf_validator import TFIDFValidator

# Import Blog Crawler
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
logger = logging.getLogger("fast_tfidf_search")

# Load environment variables
load_dotenv()

class FastTFIDFSearchIntegration:
    """
    Fast Google search integration with TF-IDF validation
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the Google search integration with TF-IDF validation
        """
        self.config = config
        self.cache_dir = os.path.join(config.get("cache_dir", "data/google_cache"))
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Load cache if exists
        self.cache = {}
        cache_file = os.path.join(self.cache_dir, "search_cache.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except Exception as e:
                logger.error(f"Error loading cache: {e}")
        
        # Initialize TF-IDF validator
        self.validator = TFIDFValidator()
        
        # Initialize Blog Crawler
        self.crawler = BlogCrawler(config)
        
        # Load seed URLs
        self.seed_urls = self._load_seed_urls()
            
        # Performance settings
        self.request_timeout = config.get("request_timeout", 3)
        self.max_workers = config.get("max_workers", 10)
        self.skip_validation = config.get("skip_validation", False)
        self.results_per_query = config.get("results_per_query", 30)
        
        # Crawl seed URLs in the background if not already crawled
        self._ensure_blogs_crawled()
    
    def _load_seed_urls(self) -> List[str]:
        """
        Load seed URLs from seed_urls.txt
        """
        seed_urls = []
        try:
            # Try to load from seed_urls.txt
            with open("seed_urls.txt", 'r', encoding='utf-8') as f:
                content = f.read()
                # Parse the JSON-like format
                import re
                urls = re.findall(r'"(https?://[^"]+)"', content)
                seed_urls.extend(urls)
            logger.info(f"Loaded {len(seed_urls)} seed URLs from seed_urls.txt")
        except Exception as e:
            logger.error(f"Error loading seed URLs: {e}")
        
        return seed_urls
    
    def _ensure_blogs_crawled(self):
        """
        Ensure blogs are crawled from seed URLs
        """
        discovered_blogs = self.crawler.get_discovered_blogs()
        
        # If no discovered blogs, start a background crawl
        if not discovered_blogs and self.seed_urls:
            logger.info("Starting background crawl of seed URLs")
            import threading
            thread = threading.Thread(target=self.crawler.crawl_seed_urls, args=(self.seed_urls,))
            thread.daemon = True
            thread.start()
    
    def _save_cache(self):
        """
        Save cache to disk
        """
        cache_file = os.path.join(self.cache_dir, "search_cache.json")
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def _fetch_metadata(self, url):
        """
        Fetch metadata for a URL (title and description) in one function for parallel processing
        """
        try:
            # Make a request with a reduced timeout
            response = requests.get(url, timeout=self.request_timeout, headers={
                "User-Agent": self.config.get("user_agent", "Mozilla/5.0")
            })
            
            title = url.split('//')[1].split('/')[0]  # Default title is domain
            description = ""
            
            # Check if successful
            if response.status_code == 200:
                # Extract content using simple regex
                import re
                
                # Get title
                title_match = re.search(r'<title[^>]*>(.*?)</title>', response.text, re.IGNORECASE | re.DOTALL)
                if title_match:
                    title = title_match.group(1).strip()
                    # Clean up title (remove special chars, etc.)
                    title = re.sub(r'\s+', ' ', title)
                
                # Try to get meta description
                meta_match = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', 
                                    response.text, re.IGNORECASE)
                if not meta_match:
                    meta_match = re.search(r'<meta[^>]*content="([^"]*)"[^>]*name="description"', 
                                        response.text, re.IGNORECASE)
                
                if meta_match:
                    description = meta_match.group(1).strip()
                else:
                    # Try to get first paragraph for snippet
                    body_content = re.search(r'<body[^>]*>(.*?)</body>', response.text, re.IGNORECASE | re.DOTALL)
                    if body_content:
                        # Remove script and style tags
                        content = re.sub(r'<script[^>]*>.*?</script>', '', body_content.group(1), flags=re.DOTALL)
                        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
                        
                        # Get first paragraph
                        paragraph = re.search(r'<p[^>]*>(.*?)</p>', content, re.IGNORECASE | re.DOTALL)
                        if paragraph:
                            # Remove HTML tags
                            text = re.sub(r'<[^>]+>', ' ', paragraph.group(1))
                            # Remove extra whitespace
                            text = re.sub(r'\s+', ' ', text).strip()
                            description = text[:200] + "..." if len(text) > 200 else text
            
            return {
                "url": url,
                "title": title,
                "description": description
            }
            
        except Exception as e:
            logger.error(f"Error fetching metadata for {url}: {e}")
            return {
                "url": url,
                "title": url.split('//')[1].split('/')[0],
                "description": ""
            }
    
    def _get_discovered_blog_results(self, query: str, num_results: int) -> List[Dict]:
        """
        Get results from discovered blogs that match the query
        """
        discovered_blogs = self.crawler.get_discovered_blogs()
        if not discovered_blogs:
            return []
        
        # Create results from discovered blogs
        results = []
        for url, blog_data in discovered_blogs.items():
            title = blog_data.get("title", url.split('//')[1].split('/')[0])
            description = blog_data.get("description", "")
            
            # Create result object
            result = {
                "url": url,
                "title": title,
                "description": description,
                "content_snippet": description,
                "is_blog_article": True,
                "score": 0.7,  # Default score for discovered blogs
                "source": "Discovered Blog"
            }
            
            results.append(result)
        
        # Validate results with TF-IDF to calculate relevance to query
        if not self.skip_validation:
            results = self.validator.validate_results(results, query)
            
            # Sort by score
            results.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top results
        return results[:num_results]
    
    def search_google(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        Search Google for the given query and validate with TF-IDF
        Also includes results from discovered blogs
        """
        # Check cache first
        cache_key = f"{query}_{num_results}"
        if cache_key in self.cache:
            logger.info(f"Using cached results for query: {query}")
            return self.cache[cache_key]
        
        logger.info(f"Searching Google for: {query}")
        
        try:
            # Enhance query with keywords for blogs and articles
            enhanced_query = f"{query} blogs articles"
            logger.info(f"Enhanced query: '{query}' -> '{enhanced_query}'")
            
            # Use googlesearch-python to search
            search_results = list(search(enhanced_query, num_results=num_results * 2))  # Get more results for filtering
            
            # Fetch metadata in parallel for faster processing
            google_results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all URLs for metadata fetching
                future_to_url = {executor.submit(self._fetch_metadata, url): url for url in search_results[:num_results * 2]}
                
                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_url):
                    metadata = future.result()
                    
                    # Create result object
                    result = {
                        "url": metadata["url"],
                        "title": metadata["title"],
                        "description": metadata["description"],
                        "content_snippet": metadata["description"],
                        "is_blog_article": True,  # Default to True if validation is skipped
                        "score": 0.8,  # Default score if validation is skipped
                        "source": "Google Search"
                    }
                    
                    google_results.append(result)
            
            # Get results from discovered blogs
            discovered_results = self._get_discovered_blog_results(query, num_results)
            
            # Combine results
            all_results = google_results + discovered_results
            
            # Skip validation if configured to do so
            if self.skip_validation:
                logger.info("Skipping validation for faster response")
                # Just sort by source (Google first, then discovered)
                all_results.sort(key=lambda x: 0 if x["source"] == "Google Search" else 1)
                final_results = all_results[:num_results]
            else:
                # Validate results with TF-IDF
                start_time = time.time()
                validated_results = self.validator.validate_results(all_results, query)
                validation_time = time.time() - start_time
                logger.info(f"TF-IDF validation completed in {validation_time:.2f} seconds")
                
                # Filter to only blog/article results and limit to requested number
                blog_results = [r for r in validated_results if r["is_blog_article"]]
                
                # Sort by score
                blog_results.sort(key=lambda x: x["score"], reverse=True)
                
                # If we don't have enough blog results, include some non-blog results
                if len(blog_results) < num_results:
                    non_blog_results = [r for r in validated_results if not r["is_blog_article"]]
                    non_blog_results.sort(key=lambda x: x["score"], reverse=True)
                    blog_results.extend(non_blog_results[:num_results - len(blog_results)])
                
                # Limit to requested number
                final_results = blog_results[:num_results]
            
            # Cache results
            self.cache[cache_key] = final_results
            self._save_cache()
            
            return final_results
            
        except Exception as e:
            logger.error(f"Error searching Google: {e}")
            return [] 