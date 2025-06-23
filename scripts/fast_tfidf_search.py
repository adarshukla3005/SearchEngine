"""
Fast Google search integration with Enhanced BM25 validation for the search engine
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
import threading
import re
from bs4 import BeautifulSoup

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
    Fast Google search integration with BM25 and semantic validation
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the Google search integration with enhanced validation
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
        
        # Get seed URLs from config
        self.seed_urls = config.get("seed_urls", [])
        logger.info(f"Loaded {len(self.seed_urls)} seed URLs from config")
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.get("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        })
            
        # Performance settings
        self.request_timeout = config.get("request_timeout", 10)
        self.max_workers = config.get("max_workers", 15)
        self.skip_validation = config.get("skip_validation", False)
        self.results_per_query = config.get("results_per_query", 30)
        
        # Cache locks to prevent race conditions
        self.cache_lock = threading.RLock()
        
        # Pre-load discovered blogs
        self.discovered_blogs = self.crawler.get_discovered_blogs()
        if not self.discovered_blogs:
            # Start background crawl only if no blogs are discovered yet
            self._ensure_blogs_crawled()

        # Initialize query expansion terms
        self._init_query_expansion_terms()
    
    def _init_query_expansion_terms(self):
        """
        Initialize query expansion terms categorized by topic domains
        """
        # Technology related terms
        self.tech_terms = {
            "programming": ["code", "developer", "software", "engineering", "algorithm"],
            "web": ["website", "frontend", "backend", "ui", "ux", "design"],
            "data": ["database", "analytics", "big data", "machine learning", "ai"],
            "mobile": ["app", "android", "ios", "mobile development"],
            "devops": ["cloud", "kubernetes", "docker", "deployment", "ci/cd"]
        }
        
        # Business related terms
        self.business_terms = {
            "marketing": ["strategy", "campaign", "branding", "audience"],
            "startup": ["venture", "funding", "growth", "entrepreneur"],
            "management": ["leadership", "team", "organization", "strategy"],
            "finance": ["investment", "market", "analysis", "financial"]
        }
        
        # Personal development terms
        self.personal_terms = {
            "productivity": ["habits", "efficiency", "workflow", "tips"],
            "learning": ["skills", "education", "growth", "study"],
            "wellness": ["health", "mental", "balance", "mindfulness"]
        }
        
        # Content type qualifiers
        self.content_qualifiers = [
            "blog", "article", "guide", "tutorial", "explained", 
            "review", "analysis", "deep dive", "comparison",
            "best practices", "tips", "techniques", "strategies"
        ]
    
    def _ensure_blogs_crawled(self):
        """
        Ensure blogs are crawled from seed URLs
        """
        discovered_blogs = self.crawler.get_discovered_blogs()
        
        # If no discovered blogs, start a background crawl
        if not discovered_blogs and self.seed_urls:
            logger.info("Starting background crawl of seed URLs")
            thread = threading.Thread(target=self.crawler.crawl_seed_urls, args=(self.seed_urls,))
            thread.daemon = True
            thread.start()
    
    def _save_cache(self):
        """
        Save cache to disk
        """
        cache_file = os.path.join(self.cache_dir, "search_cache.json")
        try:
            with self.cache_lock:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(self.cache, f)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def _fetch_metadata(self, url):
        """
        Fetch metadata for a URL (title and description) in one function for parallel processing
        """
        try:
            # Validate URL format first
            if not url.startswith(('http://', 'https://')):
                logger.error(f"Invalid URL format: {url}")
                return {
                    "url": url,
                    "title": url,
                    "description": "",
                    "is_likely_blog": False
                }
                
            # Make a request with a timeout using the session with retry logic
            try:
                response = self.session.get(url, timeout=self.request_timeout)
                response.raise_for_status()  # Raise exception for 4XX/5XX status codes
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error fetching {url}: {e}")
                return {
                    "url": url,
                    "title": url.split('//')[1].split('/')[0] if '//' in url else url,
                    "description": "",
                    "is_likely_blog": False
                }
            
            title = url.split('//')[1].split('/')[0] if '//' in url else url  # Default title is domain
            description = ""
            
            # Check if successful
            if response.status_code == 200:
                # Try to parse with BeautifulSoup for better extraction
                try:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Get title
                    if soup.title and soup.title.string:
                        title = soup.title.string.strip()
                    
                    # Try to get meta description
                    meta_desc = soup.find("meta", {"name": "description"})
                    if meta_desc and meta_desc.get("content"):
                        description = meta_desc["content"].strip()
                    else:
                        # Try Open Graph description
                        og_desc = soup.find("meta", {"property": "og:description"})
                        if og_desc and og_desc.get("content"):
                            description = og_desc["content"].strip()
                    
                    # If no description yet, try to get first paragraph
                    if not description:
                        first_p = soup.find("p")
                        if first_p:
                            description = first_p.get_text().strip()
                            # Limit description length
                            description = description[:300] + "..." if len(description) > 300 else description
                    
                    # Clean up title and description
                    title = re.sub(r'\s+', ' ', title) if title else url.split('//')[1].split('/')[0]
                    description = re.sub(r'\s+', ' ', description) if description else ""
                    
                    # Extract publication date if available - for freshness scoring
                    pub_date = None
                    date_meta = soup.find("meta", {"property": "article:published_time"}) or \
                               soup.find("meta", {"name": "article:published_time"}) or \
                               soup.find("meta", {"name": "date"}) or \
                               soup.find("meta", {"property": "og:published_time"})
                    
                    if date_meta and date_meta.get("content"):
                        pub_date = date_meta.get("content")
                    
                except Exception as e:
                    logger.debug(f"BeautifulSoup parsing error for {url}: {e}")
                    # Fallback to regex-based extraction
                    try:
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
                                    description = text[:300] + "..." if len(text) > 300 else text
                    except Exception as regex_error:
                        logger.debug(f"Regex parsing error for {url}: {regex_error}")
            
            # Determine if URL is likely a blog from the URL itself
            is_likely_blog = False
            url_lower = url.lower()
            
            # Check for blog URL patterns
            blog_patterns = [
                "/blog/", "/article/", "/post/", "/posts/", "/essays/", "/writing/", 
                "/insights/", "/news/", "/opinion/", "/views/", "/stories/"
            ]
            
            for pattern in blog_patterns:
                if pattern in url_lower:
                    is_likely_blog = True
                    break
            
            # Check for common blog domains
            blog_domains = [
                "wordpress", "blogspot", "medium", "substack", "tumblr", 
                "blogger", "ghost", "wix", "squarespace", "typepad",
                "hashnode", "dev.to", "mirror.xyz", "beehiiv"
            ]
            
            for domain in blog_domains:
                if domain in url_lower:
                    is_likely_blog = True
                    break
            
            return {
                "url": url,
                "title": title or url.split('//')[1].split('/')[0] if '//' in url else url,
                "description": description,
                "is_likely_blog": is_likely_blog,
                "pub_date": pub_date
            }
            
        except Exception as e:
            logger.error(f"Error fetching metadata for {url}: {e}")
            # Return minimal information
            domain = url.split('//')[1].split('/')[0] if '//' in url else url
            return {
                "url": url,
                "title": domain,
                "description": "",
                "is_likely_blog": False
            }
    
    def _get_discovered_blog_results(self, query: str, num_results: int) -> List[Dict]:
        """
        Get results from discovered blogs that match the query
        """
        # Refresh discovered blogs
        self.discovered_blogs = self.crawler.get_discovered_blogs()
        
        if not self.discovered_blogs:
            return []
        
        # Create results from discovered blogs
        results = []
        for url, blog_data in self.discovered_blogs.items():
            title = blog_data.get("title", url.split('//')[1].split('/')[0])
            description = blog_data.get("description", "")
            
            # Create result object
            result = {
                "url": url,
                "title": title,
                "description": description,
                "content_snippet": description,
                "is_blog_article": True,
                "score": 0.75,
                "source": "Discovered Blog"
            }
            
            results.append(result)
        
        # Validate results with BM25 to calculate relevance to query
        if not self.skip_validation:
            results = self.validator.validate_results(results, query)
            
            # Sort by score
            results.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top results
        return results[:num_results]
    
    def _expand_query(self, query: str) -> str:
        """
        Expand query with relevant terms based on content analysis
        """
        query_lower = query.lower()
        expansion_terms = []
        
        # Basic detection of query domain/category to add relevant expansion terms
        for category, terms in self.tech_terms.items():
            if any(term in query_lower for term in terms):
                # Add 2 random terms from this category
                import random
                expansion_terms.extend(random.sample(terms, min(2, len(terms))))
                break
        
        for category, terms in self.business_terms.items():
            if any(term in query_lower for term in terms):
                # Add 1 random term from this category
                import random
                expansion_terms.extend(random.sample(terms, min(1, len(terms))))
                break
                
        for category, terms in self.personal_terms.items():
            if any(term in query_lower for term in terms):
                # Add 1 random term from this category
                import random
                expansion_terms.extend(random.sample(terms, min(1, len(terms))))
                break
        
        # Always add content qualifiers for better blog/article targeting
        import random
        qualifiers = random.sample(self.content_qualifiers, min(2, len(self.content_qualifiers)))
        expansion_terms.extend(qualifiers)
        
        # Filter out terms that are already in the query
        expansion_terms = [term for term in expansion_terms if term not in query_lower]
        
        # Limit to max 3 expansion terms to avoid diluting the query too much
        expansion_terms = expansion_terms[:3]
        
        if expansion_terms:
            expanded_query = f"{query} {' '.join(expansion_terms)}"
            logger.info(f"Expanded query: '{query}' -> '{expanded_query}'")
            return expanded_query
        
        return query
    
    def _apply_result_diversity(self, results: List[Dict], top_n: int) -> List[Dict]:
        """
        Apply result diversity to avoid similar results from same domains
        """
        # If we have fewer results than top_n, return all results
        if len(results) <= top_n:
            return results
        
        # Extract domains
        for result in results:
            url = result["url"]
            try:
                domain = url.split("//")[1].split("/")[0] if "//" in url else url.split("/")[0]
                result["domain"] = domain
            except Exception:
                result["domain"] = url
        
        # Group by domain
        from collections import defaultdict
        domain_results = defaultdict(list)
        for result in results:
            domain_results[result["domain"]].append(result)
        
        # Apply diversity algorithm
        diverse_results = []
        domains_used = set()
        
        # First pass: include top result from each domain
        for domain, domain_list in domain_results.items():
            # Sort by score within domain
            domain_list.sort(key=lambda x: x["score"], reverse=True)
            
            # Include top result from domain
            diverse_results.append(domain_list[0])
            domains_used.add(domain)
            
            # If we have enough results, stop
            if len(diverse_results) >= top_n:
                break
        
        # Second pass: fill in remaining slots with best results not yet included
        if len(diverse_results) < top_n:
            # Create flat list of results not yet included
            remaining = [
                result for domain_list in domain_results.values() 
                for result in domain_list 
                if result not in diverse_results
            ]
            
            # Sort by score
            remaining.sort(key=lambda x: x["score"], reverse=True)
            
            # Add top results up to top_n
            for result in remaining:
                if len(diverse_results) < top_n:
                    diverse_results.append(result)
                else:
                    break
        
        # Sort final list by score
        diverse_results.sort(key=lambda x: x["score"], reverse=True)
        
        # Cleanup: remove domain field as it was just for internal use
        for result in diverse_results:
            if "domain" in result:
                del result["domain"]
        
        return diverse_results
    
    def search_google(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        Search Google for the given query and validate with BM25
        Also includes results from discovered blogs with improved ranking
        """
        # Check cache first
        cache_key = f"{query}_{num_results}"
        with self.cache_lock:
            if cache_key in self.cache:
                logger.info(f"Using cached results for query: {query}")
                return self.cache[cache_key]
        
        logger.info(f"Searching Google for: {query}")
        
        try:
            # Expand query with keywords for blogs and articles
            enhanced_query = self._expand_query(query)
            
            # Use googlesearch-python to search with error handling
            try:
                # Wrap the search call in a try-except block to catch any errors
                try:
                    # Get more results for better filtering and diversity
                    search_results = list(search(enhanced_query, num_results=num_results * 3))
                except IndexError:
                    logger.error("IndexError in googlesearch-python. Using alternative approach.")
                    # Try with a different number of results
                    search_results = list(search(enhanced_query, num_results=10))
                
                if not search_results:
                    logger.warning(f"No search results found for query: {enhanced_query}")
                    # Return discovered blog results as fallback
                    return self._get_discovered_blog_results(query, num_results)
            except Exception as e:
                logger.error(f"Error during Google search: {e}")
                # Return discovered blog results as fallback
                return self._get_discovered_blog_results(query, num_results)
            
            # Fetch metadata in parallel for faster processing
            google_results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all URLs for metadata fetching, with safety checks
                if search_results and len(search_results) > 0:
                    max_urls = min(num_results * 3, len(search_results))
                    future_to_url = {
                        executor.submit(self._fetch_metadata, url): url 
                        for url in search_results[:max_urls] 
                        if url and isinstance(url, str)
                    }
                    
                    # Process results as they complete
                    for future in concurrent.futures.as_completed(future_to_url):
                        metadata = future.result()
                        
                        # Set initial score based on URL pattern
                        initial_score = 0.85 if metadata.get("is_likely_blog", False) else 0.7
                        
                        # Create result object
                        result = {
                            "url": metadata["url"],
                            "title": metadata["title"],
                            "description": metadata["description"],
                            "content_snippet": metadata["description"],
                            "is_blog_article": True,  # Default to True if validation is skipped
                            "score": initial_score,
                            "source": "Google Search"
                        }
                        
                        # Add publication date if available for freshness scoring
                        if "pub_date" in metadata and metadata["pub_date"]:
                            result["pub_date"] = metadata["pub_date"]
                        
                        google_results.append(result)
            
            # Get results from discovered blogs
            discovered_results = self._get_discovered_blog_results(query, num_results)
            
            # Combine results
            all_results = google_results + discovered_results
            
            # If no results found, return empty list
            if not all_results:
                logger.warning(f"No results found for query: {query}")
                return []
            
            # Skip validation if configured to do so
            if self.skip_validation:
                logger.info("Skipping validation for faster response")
                # Just sort by source (Google first, then discovered)
                all_results.sort(key=lambda x: 0 if x["source"] == "Google Search" else 1)
                final_results = all_results[:num_results]
            else:
                # Validate results with enhanced algorithms
                start_time = time.time()
                validated_results = self.validator.validate_results(all_results, query)
                validation_time = time.time() - start_time
                logger.info(f"BM25 validation completed in {validation_time:.2f} seconds")
                
                # Filter to only blog/article results
                blog_results = [r for r in validated_results if r["is_blog_article"]]
                
                # Sort by score
                blog_results.sort(key=lambda x: x["score"], reverse=True)
                
                # Apply diversity for better result quality
                diverse_results = self._apply_result_diversity(blog_results, num_results)
                
                # If we don't have enough blog results, include some non-blog results
                if len(diverse_results) < num_results:
                    non_blog_results = [r for r in validated_results if not r["is_blog_article"]]
                    non_blog_results.sort(key=lambda x: x["score"], reverse=True)
                    diverse_results.extend(non_blog_results[:num_results - len(diverse_results)])
                
                # Limit to requested number
                final_results = diverse_results[:num_results] if diverse_results else []
            
            # Cache results
            with self.cache_lock:
                self.cache[cache_key] = final_results
                # Save cache in a background thread to avoid blocking
                threading.Thread(target=self._save_cache).start()
            
            return final_results
            
        except Exception as e:
            logger.error(f"Error searching Google: {e}")
            # Return discovered blog results as fallback
            return self._get_discovered_blog_results(query, num_results) 