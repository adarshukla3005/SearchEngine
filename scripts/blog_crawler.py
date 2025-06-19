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
from bs4 import BeautifulSoup

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
        self.request_timeout = config.get("request_timeout", 3)
        self.max_workers = config.get("max_workers", 10)
        self.max_depth = config.get("max_crawl_depth", 2)
        self.max_blogs_per_seed = config.get("max_blogs_per_seed", 20)
        
        # Blog indicators
        self.blog_indicators = [
            "blog", "article", "post", "author", "published", "written", 
            "opinion", "review", "guide", "tutorial", "how-to", "tips"
        ]
    
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
        
        # Check text for blog indicators
        for indicator in self.blog_indicators:
            if indicator in url_lower or indicator in text_lower:
                return True
        
        return False
    
    def _fetch_url(self, url: str) -> Dict:
        """
        Fetch URL and extract metadata
        """
        try:
            # Make a request with a timeout
            response = requests.get(url, timeout=self.request_timeout, headers={
                "User-Agent": self.config.get("user_agent", "Mozilla/5.0")
            })
            
            if response.status_code != 200:
                return {"url": url, "success": False}
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get title
            title = soup.title.string if soup.title else url.split('//')[1].split('/')[0]
            title = title.strip() if title else ""
            
            # Get meta description
            description = ""
            meta_desc = soup.find("meta", {"name": "description"})
            if meta_desc and "content" in meta_desc.attrs:
                description = meta_desc["content"].strip()
            
            # Extract links
            links = self._extract_links(url, response.text)
            
            # Filter to potential blog links
            blog_links = []
            for link in links:
                link_text = ""
                for a_tag in soup.find_all('a', href=True):
                    if a_tag['href'] == link or link.endswith(a_tag['href']):
                        link_text = a_tag.get_text()
                        break
                
                if self._is_blog_link(link, link_text):
                    blog_links.append({
                        "url": link,
                        "text": link_text.strip()
                    })
            
            return {
                "url": url,
                "title": title,
                "description": description,
                "blog_links": blog_links[:self.max_blogs_per_seed],
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return {"url": url, "success": False}
    
    def crawl_seed_urls(self, seed_urls: List[str]) -> Dict[str, Dict]:
        """
        Crawl seed URLs to discover more blogs
        """
        logger.info(f"Starting crawl of {len(seed_urls)} seed URLs")
        start_time = time.time()
        
        # Track visited URLs to avoid duplicates
        visited_urls = set()
        
        # Process seed URLs in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit seed URLs for processing
            future_to_url = {executor.submit(self._fetch_url, url): url for url in seed_urls if url not in visited_urls}
            visited_urls.update(seed_urls)
            
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
                    
                    # Submit blog links for processing if not already visited
                    for blog_url in blog_links:
                        if blog_url not in visited_urls:
                            visited_urls.add(blog_url)
                            future_to_url[executor.submit(self._fetch_url, blog_url)] = blog_url
        
        # Save discovered blogs
        self._save_discovered_blogs()
        
        crawl_time = time.time() - start_time
        logger.info(f"Crawl completed in {crawl_time:.2f} seconds, discovered {len(self.discovered_blogs)} blogs")
        
        return self.discovered_blogs
    
    def get_discovered_blogs(self) -> Dict[str, Dict]:
        """
        Get all discovered blogs
        """
        return self.discovered_blogs 