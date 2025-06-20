"""
Blog crawler to discover more blogs from seed URLs
"""
import os
import json
import logging
import time
import re
import concurrent.futures
from typing import Dict, List, Set
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# Filter warnings about XML parsed as HTML
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("google_search.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("blog_crawler")

class BlogCrawler:
    """
    Crawler to discover more blogs from seed URLs
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the blog crawler
        """
        self.config = config
        self.cache_dir = os.path.join(config.get("cache_dir", "data/google_cache"))
        self.discovered_blogs_file = os.path.join(self.cache_dir, "discovered_blogs.json")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Load discovered blogs if exists
        self.discovered_blogs = {}
        if os.path.exists(self.discovered_blogs_file):
            try:
                with open(self.discovered_blogs_file, 'r', encoding='utf-8') as f:
                    self.discovered_blogs = json.load(f)
            except Exception as e:
                logger.error(f"Error loading discovered blogs: {e}")
        
        # Performance settings
        self.request_timeout = config.get("request_timeout", 15)  # Increased timeout for reliability
        self.max_workers = config.get("max_workers", 10)  # Reduced workers to avoid overwhelming
        self.max_depth = config.get("max_crawl_depth", 2)
        self.max_blogs_per_seed = config.get("max_blogs_per_seed", 30)
        
        # Connection pool settings
        self.max_retries = config.get("max_retries", 3)
        self.pool_connections = config.get("pool_connections", 50)
        self.pool_maxsize = config.get("pool_maxsize", 50)
        
        # Blog indicators
        self.blog_indicators = [
            "blog", "article", "post", "author", "published", "written", 
            "opinion", "review", "guide", "tutorial", "how-to", "tips",
            "newsletter", "weekly", "monthly", "daily", "journal", "digest",
            "roundup", "collection", "curated", "personal", "experience"
        ]
        
        # Session for connection pooling with retry strategy
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"]
        )
        
        # Configure adapter with retry strategy and connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=self.pool_connections,
            pool_maxsize=self.pool_maxsize
        )
        
        # Mount adapter to session
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set user agent
        self.session.headers.update({
            "User-Agent": config.get("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        })
        
        # Set of visited URLs to avoid duplicates
        self.visited_urls = set()
    
    def _save_discovered_blogs(self):
        """
        Save discovered blogs to disk
        """
        try:
            with open(self.discovered_blogs_file, 'w', encoding='utf-8') as f:
                json.dump(self.discovered_blogs, f)
        except Exception as e:
            logger.error(f"Error saving discovered blogs: {e}")
    
    def _is_valid_url(self, url: str) -> bool:
        """
        Check if URL is valid
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def _is_same_domain(self, url1: str, url2: str) -> bool:
        """
        Check if two URLs are from the same domain
        """
        try:
            domain1 = urlparse(url1).netloc
            domain2 = urlparse(url2).netloc
            return domain1 == domain2
        except:
            return False
    
    def _extract_links(self, url: str, html_content: str) -> List[str]:
        """
        Extract links from HTML content
        """
        try:
            # Try parsing as HTML first
            try:
                soup = BeautifulSoup(html_content, 'html.parser')
            except:
                # If that fails, try XML
                try:
                    soup = BeautifulSoup(html_content, 'xml')
                except:
                    # If both fail, use the default parser with error handling
                    soup = BeautifulSoup(html_content, 'html.parser')
            
            links = []
            
            for a_tag in soup.find_all('a', href=True):
                link = a_tag['href']
                
                # Convert relative URLs to absolute
                if not link.startswith(('http://', 'https://')):
                    link = urljoin(url, link)
                
                # Only include valid URLs
                if self._is_valid_url(link):
                    links.append(link)
            
            return links
        except Exception as e:
            logger.error(f"Error extracting links from {url}: {e}")
            return []
    
    def _is_blog_link(self, url: str, text: str = "") -> bool:
        """
        Check if a link is likely to be a blog
        """
        url_lower = url.lower()
        text_lower = text.lower()
        
        # Check URL for blog indicators
        if "/blog/" in url_lower or "/article/" in url_lower or "/post/" in url_lower:
            return True
        elif "/posts/" in url_lower or "/essays/" in url_lower or "/writing/" in url_lower:
            return True
        
        # Check text for blog indicators
        for indicator in self.blog_indicators:
            if indicator in url_lower or indicator in text_lower:
                return True
        
        return False
    
    def _fetch_url(self, url: str) -> Dict:
        """
        Fetch URL and extract metadata
        """
        # Skip if already visited
        if url in self.visited_urls:
            return {"url": url, "success": False, "reason": "already_visited"}
        
        # Validate URL format first
        if not self._is_valid_url(url):
            return {"url": url, "success": False, "reason": "invalid_url_format"}
        
        # Add to visited URLs
        self.visited_urls.add(url)
        
        try:
            # Make a request with a timeout using the session with retry
            try:
                response = self.session.get(url, timeout=self.request_timeout, allow_redirects=True)
                response.raise_for_status()  # Raise exception for 4XX/5XX status codes
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error fetching {url}: {e}")
                return {"url": url, "success": False, "reason": str(e)}
            
            if response.status_code != 200:
                return {"url": url, "success": False, "reason": f"status_code_{response.status_code}"}
            
            # Check if content type is HTML
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
                return {"url": url, "success": False, "reason": f"not_html_content_{content_type}"}
            
            # Parse HTML with error handling
            try:
                soup = BeautifulSoup(response.text, 'html.parser')
            except Exception as parse_error:
                logger.error(f"HTML parsing error for {url}: {parse_error}")
                # If HTML parsing fails, try XML
                try:
                    soup = BeautifulSoup(response.text, 'xml')
                except Exception as xml_error:
                    logger.error(f"XML parsing error for {url}: {xml_error}")
                    # Return minimal information on parsing failure
                    domain = url.split('//')[1].split('/')[0] if '//' in url else url
                    return {
                        "url": url,
                        "title": domain,
                        "description": "",
                        "blog_links": [],
                        "success": True  # Still mark as success to save the URL
                    }
            
            # Get title with error handling
            try:
                title = soup.title.string.strip() if soup.title and soup.title.string else ""
            except Exception:
                title = ""
                
            if not title:
                title = url.split('//')[1].split('/')[0] if '//' in url else url
            
            # Get meta description with error handling
            description = ""
            try:
                meta_desc = soup.find("meta", {"name": "description"})
                if meta_desc and "content" in meta_desc.attrs:
                    description = meta_desc["content"].strip()
                
                # Try Open Graph description if no meta description
                if not description:
                    og_desc = soup.find("meta", {"property": "og:description"})
                    if og_desc and "content" in og_desc.attrs:
                        description = og_desc["content"].strip()
            except Exception as desc_error:
                logger.error(f"Error extracting description for {url}: {desc_error}")
            
            # Extract links with error handling
            try:
                links = self._extract_links(url, response.text)
            except Exception as link_error:
                logger.error(f"Error extracting links from {url}: {link_error}")
                links = []
            
            # Filter to potential blog links
            blog_links = []
            try:
                for link in links:
                    # Skip invalid URLs
                    if not self._is_valid_url(link):
                        continue
                        
                    link_text = ""
                    try:
                        for a_tag in soup.find_all('a', href=True):
                            if a_tag['href'] == link or link.endswith(a_tag['href']):
                                link_text = a_tag.get_text()
                                break
                    except Exception:
                        pass
                    
                    if self._is_blog_link(link, link_text):
                        blog_links.append({
                            "url": link,
                            "text": link_text.strip()
                        })
            except Exception as blog_link_error:
                logger.error(f"Error processing blog links for {url}: {blog_link_error}")
            
            return {
                "url": url,
                "title": title,
                "description": description,
                "blog_links": blog_links[:self.max_blogs_per_seed],
                "success": True
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching {url}: {e}")
            return {"url": url, "success": False, "reason": str(e)}
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return {"url": url, "success": False, "reason": str(e)}
    
    def crawl_seed_urls(self, seed_urls: List[str]) -> Dict[str, Dict]:
        """
        Crawl seed URLs to discover more blogs
        """
        logger.info(f"Starting crawl of {len(seed_urls)} seed URLs")
        start_time = time.time()
        
        # Reset visited URLs
        self.visited_urls = set()
        
        # Process seed URLs in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit seed URLs for processing
            future_to_url = {executor.submit(self._fetch_url, url): url for url in seed_urls if url not in self.visited_urls}
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_url):
                result = future.result()
                url = result["url"]
                
                if result["success"]:
                    # Save to discovered blogs
                    self.discovered_blogs[url] = {
                        "title": result.get("title", ""),
                        "description": result.get("description", ""),
                        "discovered_at": time.time()
                    }
                    
                    # Process blog links (depth 1)
                    blog_links = [link["url"] for link in result.get("blog_links", [])]
                    
                    if blog_links and self.max_depth > 1:
                        # Submit blog links for processing (depth 1)
                        blog_futures = {}
                        for blog_url in blog_links:
                            if blog_url not in self.visited_urls:
                                blog_futures[executor.submit(self._fetch_url, blog_url)] = blog_url
                        
                        # Process blog results as they complete
                        for blog_future in concurrent.futures.as_completed(blog_futures):
                            blog_result = blog_future.result()
                            blog_url = blog_result["url"]
                            
                            if blog_result["success"]:
                                # Save to discovered blogs
                                self.discovered_blogs[blog_url] = {
                                    "title": blog_result.get("title", ""),
                                    "description": blog_result.get("description", ""),
                                    "discovered_at": time.time()
                                }
                                
                                # Process sub-blog links (depth 2)
                                if self.max_depth > 2:
                                    sub_blog_links = [link["url"] for link in blog_result.get("blog_links", [])]
                                    
                                    for sub_blog_url in sub_blog_links:
                                        if sub_blog_url not in self.visited_urls:
                                            sub_blog_future = executor.submit(self._fetch_url, sub_blog_url)
                                            sub_blog_result = sub_blog_future.result()
                                            
                                            if sub_blog_result["success"]:
                                                # Save to discovered blogs
                                                self.discovered_blogs[sub_blog_url] = {
                                                    "title": sub_blog_result.get("title", ""),
                                                    "description": sub_blog_result.get("description", ""),
                                                    "discovered_at": time.time()
                                                }
                
                # Save discovered blogs periodically
                if len(self.discovered_blogs) % 10 == 0:
                    self._save_discovered_blogs()
        
        # Save final discovered blogs
        self._save_discovered_blogs()
        
        # Log results
        crawl_time = time.time() - start_time
        logger.info(f"Crawl completed in {crawl_time:.2f} seconds")
        logger.info(f"Discovered {len(self.discovered_blogs)} blogs")
        logger.info(f"Visited {len(self.visited_urls)} URLs")
        
        return self.discovered_blogs
    
    def get_discovered_blogs(self) -> Dict[str, Dict]:
        """
        Get discovered blogs
        """
        return self.discovered_blogs 