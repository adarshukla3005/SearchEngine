"""
Content classifier for the Personal Blog Search Engine
Uses a rule-based approach to classify content efficiently
"""
import os
import json
import logging
from typing import Dict, List, Tuple, Optional
from tqdm import tqdm
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("classifier.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("classifier")

class ContentClassifier:
    """
    Rule-based content classifier for identifying personal blogs
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the classifier with configuration
        """
        self.config = config
        
        # Create output directory if it doesn't exist
        os.makedirs(self.config["output_dir"], exist_ok=True)
        os.makedirs(self.config["cache_dir"], exist_ok=True)
        
        # Define domain patterns that are likely personal blogs
        self.personal_domain_patterns = [
            r'\.substack\.com$',
            r'\.medium\.com$',
            r'\.wordpress\.com$',
            r'\.blogspot\.com$',
            r'\.tumblr\.com$',
            r'\.ghost\.io$',
            r'\.github\.io$',
            r'\.netlify\.app$',
            r'\.vercel\.app$',
            r'blog\.',
            r'\.blog$',
        ]
        
        # Define domain patterns that are likely NOT personal blogs
        self.non_personal_domain_patterns = [
            r'\.gov$',
            r'\.edu$',
            r'news\.',
            r'\.com/news',
            r'wikipedia\.org$',
            r'amazon\.com$',
            r'facebook\.com$',
            r'twitter\.com$',
            r'instagram\.com$',
            r'linkedin\.com$',
            r'youtube\.com$',
        ]
        
        # Define content patterns that suggest personal blogs
        self.personal_content_patterns = [
            r'my (thoughts|journey|experience|story)',
            r'i (believe|think|feel)',
            r'about me',
            r'my blog',
            r'written by',
            r'author',
            r'personal',
            r'opinion',
        ]
    
    def _check_domain_patterns(self, url: str) -> Optional[bool]:
        """
        Check if domain matches known patterns
        Returns: True if personal blog, False if not, None if uncertain
        """
        domain = urlparse(url).netloc.lower()
        
        # Check personal blog patterns
        for pattern in self.personal_domain_patterns:
            if re.search(pattern, domain):
                return True
        
        # Check non-personal patterns
        for pattern in self.non_personal_domain_patterns:
            if re.search(pattern, domain):
                return False
        
        # If no patterns match, return None (uncertain)
        return None
    
    def _extract_header_footer(self, html_content: str) -> str:
        """
        Extract header and footer content from HTML
        """
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Extract header content
        header_content = ""
        header_tags = soup.find_all(['header', 'nav'])
        for tag in header_tags:
            header_content += tag.get_text() + " "
        
        # Extract footer content
        footer_content = ""
        footer_tags = soup.find_all(['footer'])
        for tag in footer_tags:
            footer_content += tag.get_text() + " "
        
        # Clean up the text
        combined = (header_content + " " + footer_content).strip()
        combined = re.sub(r'\s+', ' ', combined)
        
        return combined
    
    def _check_content_patterns(self, text: str) -> Tuple[float, bool]:
        """
        Check if content matches patterns suggesting personal blog
        Returns: (confidence, is_personal_blog)
        """
        text = text.lower()
        matches = 0
        
        for pattern in self.personal_content_patterns:
            if re.search(pattern, text):
                matches += 1
        
        # Calculate confidence based on number of matches
        confidence = min(0.5 + (matches * 0.1), 0.9)
        is_personal_blog = confidence >= 0.6
        
        return confidence, is_personal_blog
    
    def classify_page(self, page_data: Dict) -> Dict:
        """
        Classify a page using hierarchical approach
        """
        url = page_data["url"]
        html = page_data["html"]
        title = page_data.get("title", "")
        
        # Step 1: Check domain patterns (fastest)
        domain_result = self._check_domain_patterns(url)
        if domain_result is not None:
            confidence = 0.9  # High confidence for pattern-based classification
            return {
                "url": url,
                "title": title,
                "is_personal_blog": domain_result,
                "confidence": confidence,
                "method": "domain_pattern"
            }
        
        # Step 2: Check header/footer content
        header_footer = self._extract_header_footer(html)
        if header_footer:
            confidence, is_personal = self._check_content_patterns(header_footer)
            if confidence > self.config["threshold_header"]:
                return {
                    "url": url,
                    "title": title,
                    "is_personal_blog": is_personal,
                    "confidence": confidence,
                    "method": "header_footer"
                }
        
        # Step 3: Check full content
        meta_desc = page_data.get("meta_description", "")
        content_sample = page_data.get("content", "")[:2000]  # First 2000 chars
        
        # Combine metadata and content sample
        combined_text = f"{title} {meta_desc} {content_sample}"
        confidence, is_personal = self._check_content_patterns(combined_text)
        
        # Default to considering it a personal blog with medium confidence
        if confidence < 0.6:
            confidence = 0.65
            is_personal = True
        
        return {
            "url": url,
            "title": title,
            "is_personal_blog": is_personal,
            "confidence": confidence,
            "method": "content"
        }
    
    def classify_batch(self, crawled_data_dir: str):
        """
        Classify all pages in the crawled data directory
        """
        # Get list of all JSON files in the crawled data directory
        json_files = [f for f in os.listdir(crawled_data_dir) if f.endswith('.json') and f != 'visited_urls.json' and f != 'visited_urls.json.bak']
        
        results = []
        personal_blogs = 0
        non_blogs = 0
        
        with tqdm(total=len(json_files), desc="Classifying") as pbar:
            for batch_start in range(0, len(json_files), self.config["batch_size"]):
                batch_files = json_files[batch_start:batch_start + self.config["batch_size"]]
                
                for json_file in batch_files:
                    try:
                        # Load page data
                        with open(os.path.join(crawled_data_dir, json_file), 'r', encoding='utf-8') as f:
                            page_data = json.load(f)
                        
                        # Classify page
                        result = self.classify_page(page_data)
                        
                        # Update counters
                        if result["is_personal_blog"]:
                            personal_blogs += 1
                        else:
                            non_blogs += 1
                        
                        # Save result
                        results.append(result)
                        
                        # Save individual classification result
                        output_file = os.path.join(
                            self.config["output_dir"],
                            json_file
                        )
                        
                        # Combine page data with classification result
                        classified_data = {**page_data, **result}
                        
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(classified_data, f, ensure_ascii=False)
                        
                    except Exception as e:
                        logger.error(f"Error classifying {json_file}: {e}")
                    
                    pbar.update(1)
        
        # Save summary
        summary = {
            "total": len(json_files),
            "personal_blogs": personal_blogs,
            "non_blogs": non_blogs,
            "results": results
        }
        
        with open(os.path.join(self.config["output_dir"], "classification_summary.json"), 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False)
        
        logger.info(f"Classification completed. {personal_blogs} personal blogs identified out of {len(json_files)} pages.") 