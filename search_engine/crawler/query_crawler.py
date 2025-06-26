"""
Query-based crawler for the Personal Blog Search Engine
This crawler searches for specific topics and crawls relevant pages
"""
import os
import sys
import argparse
import requests
import json
import time
import hashlib
from urllib.parse import urljoin, urlparse, quote_plus
from bs4 import BeautifulSoup
from tqdm import tqdm

# Add parent directory to path to import from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from search_engine.crawler.crawler import Crawler
from utils.config import CRAWLER_CONFIG

class QueryCrawler(Crawler):
    """
    Query-based crawler that searches for specific topics
    """
    
    def __init__(self, config):
        """
        Initialize the query crawler
        """
        super().__init__(config)
        self.search_engines = [
            {
                "name": "DuckDuckGo",
                "url": "https://html.duckduckgo.com/html/?q={query}",
                "result_selector": "div.result",
                "link_selector": "a.result__a",
                "description_selector": "a.result__snippet"
            },
            {
                "name": "Bing",
                "url": "https://www.bing.com/search?q={query}+site%3Ablog+OR+site%3Asubstack+OR+site%3Amedium",
                "result_selector": "li.b_algo",
                "link_selector": "h2 a",
                "description_selector": "div.b_caption p"
            }
        ]
    
    def search_and_queue_urls(self, query, max_results=20):
        """
        Search for the query and queue the result URLs for crawling
        """
        print(f"Searching for: {query}")
        queued_urls = set()
        
        for engine in self.search_engines:
            try:
                print(f"Using search engine: {engine['name']}")
                search_url = engine['url'].format(query=quote_plus(query))
                
                headers = {
                    "User-Agent": self.config["user_agent"],
                    "Accept": "text/html,application/xhtml+xml,application/xml",
                    "Accept-Language": "en-US,en;q=0.9"
                }
                
                response = requests.get(search_url, headers=headers, timeout=self.config["timeout"])
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'lxml')
                    results = soup.select(engine['result_selector'])
                    
                    for i, result in enumerate(results[:max_results]):
                        try:
                            link_element = result.select_one(engine['link_selector'])
                            if link_element and link_element.has_attr('href'):
                                url = link_element['href']
                                
                                # Handle relative URLs
                                if not url.startswith('http'):
                                    base_url = search_url.split('?')[0]
                                    url = urljoin(base_url, url)
                                
                                # Skip if already queued or visited
                                if url in queued_urls or url in self.visited_urls:
                                    continue
                                
                                # Extract domain and check if it's a blog-like domain
                                parsed_url = urlparse(url)
                                domain = parsed_url.netloc.lower()
                                
                                # Skip certain domains that aren't blogs
                                if any(skip in domain for skip in ['youtube.com', 'facebook.com', 'twitter.com', 'instagram.com', 'amazon.com']):
                                    continue
                                
                                # Add to queue
                                self.url_queue.append({"url": url, "depth": 0})
                                queued_urls.add(url)
                                print(f"  Queued: {url}")
                        except Exception as e:
                            print(f"Error processing search result: {e}")
                    
                    print(f"Found {len(queued_urls)} unique URLs from {engine['name']}")
                    
                    # Wait between search engines to avoid rate limiting
                    time.sleep(2)
                else:
                    print(f"Failed to search {engine['name']}: Status code {response.status_code}")
            
            except Exception as e:
                print(f"Error searching with {engine['name']}: {e}")
        
        return len(queued_urls)
    
    def crawl_query(self, query):
        """
        Crawl pages related to a specific query
        """
        # Search and queue URLs
        num_queued = self.search_and_queue_urls(query)
        
        if num_queued == 0:
            print("No URLs found for the query. Try a different query.")
            return
        
        # Start crawling
        pages_crawled = 0
        
        with tqdm(total=self.config["max_pages"], desc="Crawling") as pbar:
            while self.url_queue and pages_crawled < self.config["max_pages"]:
                # Get next URL from queue
                item = self.url_queue.pop(0)
                url = item["url"]
                depth = item["depth"]
                
                # Skip if already visited
                if url in self.visited_urls:
                    continue
                
                # Check robots.txt
                if not self._should_respect_robots(url):
                    print(f"Skipping {url} due to robots.txt")
                    self.visited_urls.add(url)
                    continue
                
                try:
                    # Fetch page
                    headers = {"User-Agent": self.config["user_agent"]}
                    response = requests.get(url, headers=headers, timeout=self.config["timeout"])
                    
                    # Skip non-HTML content
                    content_type = response.headers.get('Content-Type', '')
                    if 'text/html' not in content_type.lower():
                        print(f"Skipping non-HTML content: {url}")
                        self.visited_urls.add(url)
                        continue
                    
                    # Process the page
                    html_content = response.text
                    
                    # Save page data
                    url_hash = self._get_url_hash(url)
                    page_data = self._process_page(url, html_content)
                    
                    with open(os.path.join(self.config["data_dir"], f"{url_hash}.json"), 'w', encoding='utf-8') as f:
                        json.dump(page_data, f, ensure_ascii=False)
                    
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
                    
                    # Rate limiting
                    time.sleep(self.config["rate_limit"])
                    
                except Exception as e:
                    print(f"Error crawling {url}: {e}")
                    self.visited_urls.add(url)
        
        # Save visited URLs at the end
        self._save_visited_urls()
        print(f"Crawling completed. Crawled {pages_crawled} pages related to '{query}'.")
    
    def _process_page(self, url, html_content):
        """
        Process a page and extract relevant data
        """
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Extract title
        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
        
        # Extract meta description
        meta_desc = ""
        meta_tag = soup.find('meta', attrs={'name': 'description'})
        if meta_tag and meta_tag.has_attr('content'):
            meta_desc = meta_tag['content'].strip()
        
        # Extract main content (simplified)
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
        
        main_content = soup.get_text()
        main_content = ' '.join(main_content.split())
        
        return {
            "url": url,
            "title": title,
            "meta_description": meta_desc,
            "content": main_content,
            "html": html_content,
            "crawl_time": time.time()
        }

def main():
    """
    Main function to run the query crawler
    """
    parser = argparse.ArgumentParser(description='Run the query-based crawler')
    parser.add_argument('--query', type=str, required=True,
                        help='Search query to find and crawl relevant pages')
    parser.add_argument('--max-pages', type=int, default=CRAWLER_CONFIG["max_pages"],
                        help='Maximum number of pages to crawl')
    parser.add_argument('--max-depth', type=int, default=CRAWLER_CONFIG["max_depth"],
                        help='Maximum depth to crawl from seed URLs')
    parser.add_argument('--rate-limit', type=float, default=CRAWLER_CONFIG["rate_limit"],
                        help='Time to wait between requests (seconds)')
    args = parser.parse_args()
    
    # Update config with command-line arguments
    config = CRAWLER_CONFIG.copy()
    config["max_pages"] = args.max_pages
    config["max_depth"] = args.max_depth
    config["rate_limit"] = args.rate_limit
    
    # Create data directory if it doesn't exist
    os.makedirs(config["data_dir"], exist_ok=True)
    
    # Run query crawler
    crawler = QueryCrawler(config)
    crawler.crawl_query(args.query)

if __name__ == "__main__":
    main() 