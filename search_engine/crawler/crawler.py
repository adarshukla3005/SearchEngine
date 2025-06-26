"""
Web crawler implementation for the Personal Blog Search Engine
"""
import os
import json
import time
import hashlib
import requests
from urllib.parse import urljoin, urlparse
from typing import Set, Dict, List, Optional
import logging
from bs4 import BeautifulSoup
from tqdm import tqdm
from collections import Counter

from utils.text_processing import clean_text, extract_title_from_html, extract_meta_description

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("crawler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("crawler")

class Crawler:
    """
    Web crawler for collecting blog content
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the crawler with configuration
        """
        self.config = config
        self.visited_urls: Set[str] = set()
        self.url_queue: List[Dict] = []
        self.robots_cache: Dict[str, Set[str]] = {}
        self.domain_stats: Counter = Counter()
        self.verbose = config.get("verbose", False)
        
        # Create data directory if it doesn't exist
        os.makedirs(self.config["data_dir"], exist_ok=True)
        
        # Load previously visited URLs if available
        self._load_visited_urls()
    
    def _load_visited_urls(self):
        """
        Load previously visited URLs from file
        """
        visited_file = os.path.join(self.config["data_dir"], "visited_urls.json")
        if os.path.exists(visited_file):
            try:
                with open(visited_file, 'r', encoding='utf-8') as f:
                    self.visited_urls = set(json.load(f))
                logger.info(f"Loaded {len(self.visited_urls)} previously visited URLs")
            except Exception as e:
                logger.error(f"Error loading visited URLs: {e}")
    
    def _save_visited_urls(self):
        """
        Save visited URLs to file
        """
        visited_file = os.path.join(self.config["data_dir"], "visited_urls.json")
        try:
            with open(visited_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.visited_urls), f)
        except Exception as e:
            logger.error(f"Error saving visited URLs: {e}")
    
    def _get_url_hash(self, url: str) -> str:
        """
        Get a hash of the URL to use as a filename
        """
        return hashlib.md5(url.encode()).hexdigest()
    
    def _should_respect_robots(self, url: str) -> bool:
        """
        Check if URL should be crawled according to robots.txt
        """
        if not self.config["respect_robots"]:
            return True
        
        parsed_url = urlparse(url)
        domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        path = parsed_url.path
        
        # Check if robots.txt for this domain is already cached
        if domain not in self.robots_cache:
            try:
                robots_url = f"{domain}/robots.txt"
                response = requests.get(robots_url, timeout=self.config["timeout"])
                disallowed_paths = set()
                
                if response.status_code == 200:
                    lines = response.text.split('\n')
                    user_agent_matched = False
                    
                    for line in lines:
                        line = line.strip().lower()
                        if line.startswith('user-agent:'):
                            agent = line[11:].strip()
                            user_agent_matched = (agent == '*' or 
                                                 self.config["user_agent"].lower() in agent)
                        elif user_agent_matched and line.startswith('disallow:'):
                            disallow_path = line[9:].strip()
                            if disallow_path:
                                disallowed_paths.add(disallow_path)
                
                self.robots_cache[domain] = disallowed_paths
            except Exception as e:
                logger.warning(f"Error fetching robots.txt for {domain}: {e}")
                # If we can't fetch robots.txt, assume we can crawl
                self.robots_cache[domain] = set()
        
        # Check if path is disallowed
        for disallowed in self.robots_cache[domain]:
            if path.startswith(disallowed):
                return False
        
        return True
    
    def _extract_links(self, url: str, html_content: str) -> List[str]:
        """
        Extract links from HTML content
        """
        soup = BeautifulSoup(html_content, 'lxml')
        base_url = url
        
        links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(base_url, href)
            
            # Filter out non-HTTP URLs and fragments
            parsed = urlparse(full_url)
            if parsed.scheme in ('http', 'https') and parsed.netloc:
                # Remove fragments
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if parsed.query:
                    clean_url += f"?{parsed.query}"
                links.append(clean_url)
        
        return links
    
    def _get_domain(self, url: str) -> str:
        """
        Extract domain from URL
        """
        return urlparse(url).netloc
    
    def _print_domain_stats(self):
        """
        Print statistics about crawled domains
        """
        print("\nDomain Statistics:")
        print("-" * 60)
        for domain, count in self.domain_stats.most_common(10):
            print(f"{domain:<40} {count:>5} pages")
        print("-" * 60)
        print(f"Total domains: {len(self.domain_stats)}")
    
    def crawl(self):
        """
        Start the crawling process
        """
        # Initialize queue with seed URLs
        for url in self.config["seed_urls"]:
            self.url_queue.append({"url": url, "depth": 0})
        
        pages_crawled = 0
        start_time = time.time()
        
        with tqdm(total=self.config["max_pages"], desc="Crawling") as pbar:
            while self.url_queue and pages_crawled < self.config["max_pages"]:
                # Get next URL from queue
                item = self.url_queue.pop(0)
                url = item["url"]
                depth = item["depth"]
                
                # Update progress bar description with current URL
                if self.verbose:
                    domain = self._get_domain(url)
                    pbar.set_description(f"Crawling {domain}")
                    pbar.set_postfix_str(f"Depth: {depth}, Queue: {len(self.url_queue)}")
                
                # Skip if already visited
                if url in self.visited_urls:
                    continue
                
                # Check robots.txt
                if not self._should_respect_robots(url):
                    if self.verbose:
                        logger.info(f"Skipping {url} due to robots.txt")
                    self.visited_urls.add(url)
                    continue
                
                try:
                    # Fetch page
                    headers = {"User-Agent": self.config["user_agent"]}
                    response = requests.get(url, headers=headers, timeout=self.config["timeout"])
                    
                    # Skip non-HTML content
                    content_type = response.headers.get('Content-Type', '')
                    if 'text/html' not in content_type.lower():
                        if self.verbose:
                            logger.info(f"Skipping non-HTML content: {url}")
                        self.visited_urls.add(url)
                        continue
                    
                    # Process the page
                    html_content = response.text
                    
                    # Extract title and meta description
                    title = extract_title_from_html(html_content)
                    meta_desc = extract_meta_description(html_content)
                    
                    # Extract main content (simplified)
                    soup = BeautifulSoup(html_content, 'lxml')
                    
                    # Remove script, style, and other non-content elements
                    for element in soup(["script", "style", "nav", "footer", "header"]):
                        element.decompose()
                    
                    main_content = clean_text(soup.get_text())
                    
                    # Save page data
                    url_hash = self._get_url_hash(url)
                    page_data = {
                        "url": url,
                        "title": title,
                        "meta_description": meta_desc,
                        "content": main_content,
                        "html": html_content,
                        "crawl_time": time.time()
                    }
                    
                    with open(os.path.join(self.config["data_dir"], f"{url_hash}.json"), 'w', encoding='utf-8') as f:
                        json.dump(page_data, f, ensure_ascii=False)
                    
                    # Update domain statistics
                    domain = self._get_domain(url)
                    self.domain_stats[domain] += 1
                    
                    # Log crawled page if verbose
                    if self.verbose:
                        logger.info(f"Crawled: {url} - {title}")
                    
                    # Extract links if not at max depth
                    if depth < self.config["max_depth"]:
                        links = self._extract_links(url, html_content)
                        for link in links:
                            if link not in self.visited_urls:
                                self.url_queue.append({"url": link, "depth": depth + 1})
                    
                    # Mark URL as visited
                    self.visited_urls.add(url)
                    pages_crawled += 1
                    pbar.update(1)
                    
                    # Save visited URLs periodically
                    if pages_crawled % 10 == 0:
                        self._save_visited_urls()
                        
                        # Show domain statistics periodically if verbose
                        if self.verbose and pages_crawled % 20 == 0:
                            self._print_domain_stats()
                    
                    # Rate limiting
                    time.sleep(self.config["rate_limit"])
                    
                except Exception as e:
                    if self.verbose:
                        logger.error(f"Error crawling {url}: {e}")
                    self.visited_urls.add(url)
        
        # Save visited URLs at the end
        self._save_visited_urls()
        
        # Print final statistics
        elapsed_time = time.time() - start_time
        logger.info(f"Crawling completed. Crawled {pages_crawled} pages in {elapsed_time:.2f} seconds.")
        
        # Print domain statistics
        self._print_domain_stats() 