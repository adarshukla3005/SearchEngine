"""
Google search integration with Gemini validation for the search engine
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

class GoogleSearchIntegration:
    """
    Google search integration with Gemini validation
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
            
        # Rate limit tracking
        self.last_api_call = 0
        self.rate_limited = False
        self.rate_limit_start_time = 0
        self.rate_limit_cooldown = 60  # 60 seconds cooldown after hitting rate limit
        
        # Performance settings
        self.request_timeout = config.get("request_timeout", 3)  # Reduced timeout for faster responses
        self.max_workers = config.get("max_workers", 5)         # Number of parallel workers for fetching metadata
        self.skip_validation = config.get("skip_validation", False)  # Option to skip validation entirely
        
        # Performance settings
        self.request_timeout = 3  # Reduced timeout for faster responses
        self.max_workers = 5      # Number of parallel workers for fetching metadata
        self.skip_validation = config.get("skip_validation", False)  # Option to skip validation entirely
    
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
            
    def _check_rate_limit(self):
        """
        Check if we're currently rate limited
        """
        if self.rate_limited:
            current_time = time.time()
            if current_time - self.rate_limit_start_time > self.rate_limit_cooldown:
                logger.info("Rate limit cooldown period ended, resetting rate limit status")
                self.rate_limited = False
            else:
                return True
        return False
    
    def enhance_query(self, query: str) -> str:
        """
        Enhance the query using Gemini to make it more specific to blogs and articles
        """
        # For faster responses, skip Gemini enhancement and just append keywords
        if self.skip_validation or not self.model or self._check_rate_limit():
            return f"{query} blogs articles"
        
        try:
            # Enforce minimum delay between API calls
            current_time = time.time()
            elapsed = current_time - self.last_api_call
            if elapsed < 1.0:  # At least 1 second between calls
                time.sleep(1.0 - elapsed)
                
            # Prepare prompt for Gemini
            prompt = f"""
            I have a search query: "{query}"
            
            I want to find blog posts and articles about this topic. Please rewrite this query to make it more specific 
            for finding high-quality blog posts and articles. Keep it concise (under 10 words if possible).
            
            Enhanced query:
            """
            
            # Call Gemini API
            response = self.model.generate_content(prompt)
            self.last_api_call = time.time()
            
            # Extract enhanced query
            enhanced_query = response.text.strip()
            
            # If the response is too long or empty, fall back to original with blog/article
            if not enhanced_query or len(enhanced_query.split()) > 15:
                return f"{query} blogs articles"
            
            # Make sure 'blogs' and 'articles' are included in the query
            if "blog" not in enhanced_query.lower() and "article" not in enhanced_query.lower():
                enhanced_query = f"{enhanced_query} blogs articles"
            
            logger.info(f"Enhanced query: '{query}' -> '{enhanced_query}'")
            return enhanced_query
            
        except Exception as e:
            logger.error(f"Error enhancing query with Gemini: {e}")
            
            # Check if it's a rate limit error
            if "429" in str(e) or "quota" in str(e).lower():
                logger.warning("Hit rate limit, cooling down for 60 seconds")
                self.rate_limited = True
                self.rate_limit_start_time = time.time()
                
            return f"{query} blogs articles"
    
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
            # Enhance query with Gemini or just append keywords
            enhanced_query = self.enhance_query(query)
            
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
                        "score": 0.8  # Default score if validation is skipped
                    }
                    
                    results.append(result)
            
            # Skip validation if configured to do so or if rate limited
            if self.skip_validation or self._check_rate_limit() or not self.model:
                logger.info("Skipping validation for faster response")
                final_results = results[:num_results]
            else:
                # Validate results with Gemini
                validated_results = self._validate_with_gemini(results, query)
                
                # Filter to only blog/article results and limit to requested number
                blog_results = [r for r in validated_results if r["is_blog_article"]]
                
                # Sort by score
                blog_results.sort(key=lambda x: x["score"], reverse=True)
                
                # Limit to requested number
                final_results = blog_results[:num_results]
            
            # Cache results
            self.cache[cache_key] = final_results
            self._save_cache()
            
            return final_results
            
        except Exception as e:
            logger.error(f"Error searching Google: {e}")
            return []
    
    def _validate_with_gemini(self, results: List[Dict], query: str) -> List[Dict]:
        """
        Validate search results with Gemini to check if they are blogs/articles
        and how relevant they are to the query
        """
        if not self.model or self._check_rate_limit():
            logger.warning("Gemini model not available or rate limited, skipping validation")
            # Just mark all as blogs/articles without validation
            for result in results:
                result["is_blog_article"] = True
                result["score"] = 0.8
            return results
        
        validated_results = []
        validation_count = 0
        max_validations = min(3, len(results))  # Reduced from 5 to 3 for faster responses
        
        for result in results:
            try:
                # Only validate a limited number of results to avoid rate limits and speed up response
                if validation_count < max_validations:
                    # Enforce minimum delay between API calls
                    current_time = time.time()
                    elapsed = current_time - self.last_api_call
                    if elapsed < 1.0:  # At least 1 second between calls
                        time.sleep(1.0 - elapsed)
                    
                    # Prepare prompt for Gemini
                    url = result["url"]
                    title = result["title"]
                    description = result["description"]
                    
                    # Simplified prompt for faster processing
                    prompt = f"""
                    URL: {url}
                    Title: {title}
                    Query: {query}
                    
                    Is this a blog post or article? Answer with just:
                    Is blog/article: [Yes/No]
                    Relevance score (0-1): [score]
                    """
                    
                    # Call Gemini API
                    response = self.model.generate_content(prompt)
                    self.last_api_call = time.time()
                    response_text = response.text.strip().lower()
                    
                    # Parse response
                    is_blog_article = "yes" in response_text.split("is blog/article:")[1].split("\n")[0] if "is blog/article:" in response_text else True
                    
                    # Extract relevance score
                    score = 0.8  # Default
                    import re
                    score_match = re.search(r'relevance score \(0-1\): *([\d\.]+)', response_text)
                    if score_match:
                        try:
                            score = float(score_match.group(1))
                            # Ensure score is between 0 and 1
                            score = max(0.0, min(1.0, score))
                        except:
                            pass
                    
                    # Update result
                    result["is_blog_article"] = is_blog_article
                    result["score"] = score
                    
                    validation_count += 1
                else:
                    # For results beyond our validation limit, just mark as blogs/articles
                    result["is_blog_article"] = True
                    result["score"] = 0.7  # Slightly lower default score for non-validated results
                
                # Add to validated results
                validated_results.append(result)
                
            except Exception as e:
                logger.error(f"Error validating with Gemini: {e}")
                # Check if it's a rate limit error
                if "429" in str(e) or "quota" in str(e).lower():
                    logger.warning("Hit rate limit, cooling down for 60 seconds")
                    self.rate_limited = True
                    self.rate_limit_start_time = time.time()
                    
                    # Stop validation for remaining results
                    for remaining in results[results.index(result):]:
                        remaining["is_blog_article"] = True
                        remaining["score"] = 0.7
                        validated_results.append(remaining)
                    
                    break
                else:
                    # Add without validation for other errors
                    result["is_blog_article"] = True
                    result["score"] = 0.7
                    validated_results.append(result)
        
        return validated_results 