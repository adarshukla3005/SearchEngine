"""
Fast Google search integration with optional Gemini validation for the search engine
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
import google.generativeai as genai

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("google_search.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("google_search")

# Load environment variables
load_dotenv()

# Initialize Gemini API
gemini_api_key = os.getenv("GEMINI_API_KEY")
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
else:
    logger.warning("GEMINI_API_KEY not found in environment variables")

class FastGoogleSearchIntegration:
    """
    Fast Google search integration with optional Gemini validation
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the Google search integration
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
        
        # Initialize Gemini model
        try:
            if gemini_api_key:
                self.model = genai.GenerativeModel('gemini-2.0-flash')
            else:
                self.model = None
        except Exception as e:
            logger.error(f"Error initializing Gemini model: {e}")
            self.model = None
            
        # Performance settings
        self.request_timeout = config.get("request_timeout", 3)  # Reduced timeout for faster responses
        self.max_workers = config.get("max_workers", 5)         # Number of parallel workers for fetching metadata
        self.skip_validation = config.get("skip_validation", True)  # Skip validation by default for speed
    
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
    
    def search_google(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        Search Google for the given query
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
            results = []
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
                    
                    results.append(result)
            
            # Limit to requested number
            final_results = results[:num_results]
            
            # Cache results
            self.cache[cache_key] = final_results
            self._save_cache()
            
            return final_results
            
        except Exception as e:
            logger.error(f"Error searching Google: {e}")
            return [] 