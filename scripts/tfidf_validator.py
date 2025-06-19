"""
TF-IDF based validation for search results to identify blog posts and articles
"""
import re
import math
import logging
from typing import Dict, List, Tuple
import numpy as np
from collections import Counter

# Set up logging
logger = logging.getLogger("tfidf_validator")

class TFIDFValidator:
    """
    TF-IDF based validator for identifying blog posts and articles
    """
    
    def __init__(self):
        """
        Initialize the TF-IDF validator
        """
        # Common blog/article related terms
        self.blog_article_terms = [
            "blog", "article", "post", "author", "published", "written", 
            "opinion", "review", "guide", "tutorial", "how-to", "tips",
            "insights", "analysis", "thoughts", "perspective", "commentary",
            "featured", "guest post", "editorial", "column", "series",
            "newsletter", "weekly", "monthly", "daily", "journal", "digest",
            "roundup", "collection", "curated", "personal", "experience"
        ]
        
        # Common blog/article structural elements
        self.structural_patterns = [
            r"comments?(\s+section)?",
            r"share(\s+this)?",
            r"author(\s+bio)?",
            r"published(\s+on)?",
            r"posted(\s+on)?",
            r"date",
            r"read(\s+more)?",
            r"tags?",
            r"categories",
            r"related(\s+posts)?",
            r"subscribe",
            r"newsletter",
            r"follow",
            r"like",
            r"bookmark",
            r"save",
            r"print",
            r"email",
            r"pdf",
        ]
        
        # Common blog domains
        self.blog_domains = [
            "wordpress", "blogspot", "medium", "substack", "tumblr", 
            "blogger", "ghost", "wix", "squarespace", "typepad",
            "hashnode", "dev.to", "mirror.xyz", "beehiiv", "revue",
            "notion", "telegraph", "svbtle"
        ]
        
        # IDF corpus (will be built dynamically)
        self.idf_corpus = {}
        self.corpus_size = 0
    
    def preprocess_text(self, text: str) -> List[str]:
        """
        Preprocess text for TF-IDF calculation
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters and digits
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\d+', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Tokenize
        tokens = text.split()
        
        # Remove very short tokens
        tokens = [token for token in tokens if len(token) > 2]
        
        return tokens
    
    def calculate_tf(self, tokens: List[str]) -> Dict[str, float]:
        """
        Calculate term frequency
        """
        # Count occurrences of each token
        token_counts = Counter(tokens)
        
        # Calculate TF
        total_tokens = len(tokens) if len(tokens) > 0 else 1
        tf = {token: count / total_tokens for token, count in token_counts.items()}
        
        return tf
    
    def update_idf_corpus(self, documents: List[List[str]]):
        """
        Update IDF corpus with new documents
        """
        # Count documents containing each term
        for doc_tokens in documents:
            unique_tokens = set(doc_tokens)
            for token in unique_tokens:
                if token not in self.idf_corpus:
                    self.idf_corpus[token] = 1
                else:
                    self.idf_corpus[token] += 1
        
        # Update corpus size
        self.corpus_size += len(documents)
    
    def calculate_idf(self, token: str) -> float:
        """
        Calculate IDF for a token
        """
        if self.corpus_size == 0 or token not in self.idf_corpus:
            return 1.0
        
        return math.log(self.corpus_size / (1 + self.idf_corpus[token]))
    
    def is_blog_article(self, url: str, title: str, description: str) -> Tuple[bool, float]:
        """
        Determine if a search result is a blog/article and calculate relevance score
        """
        # Check URL for blog indicators
        url_lower = url.lower()
        domain_score = 0.0
        
        # Check for blog domains
        for domain in self.blog_domains:
            if domain in url_lower:
                domain_score += 0.2
                break
        
        # Check for blog URL patterns
        if "/blog/" in url_lower or "/article/" in url_lower or "/post/" in url_lower:
            domain_score += 0.3
        elif "/posts/" in url_lower or "/essays/" in url_lower or "/writing/" in url_lower:
            domain_score += 0.25
        
        # Combine title and description for content analysis
        combined_text = f"{title} {description}"
        tokens = self.preprocess_text(combined_text)
        
        # Calculate TF for the document
        tf = self.calculate_tf(tokens)
        
        # Calculate score based on blog/article terms
        term_score = 0.0
        for term in self.blog_article_terms:
            if term in tf:
                term_score += tf[term] * 2.0  # Weight these terms higher
        
        # Normalize term score
        term_score = min(0.4, term_score)
        
        # Check for structural patterns
        structure_score = 0.0
        for pattern in self.structural_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                structure_score += 0.05
        
        # Cap structure score
        structure_score = min(0.3, structure_score)
        
        # Calculate final score
        final_score = domain_score + term_score + structure_score
        
        # Normalize to 0-1 range
        final_score = min(1.0, final_score)
        
        # Determine if it's a blog/article (threshold of 0.3)
        is_blog = final_score >= 0.3
        
        logger.debug(f"URL: {url}, Score: {final_score}, Is blog/article: {is_blog}")
        
        return is_blog, final_score
    
    def calculate_query_similarity(self, query_tokens: List[str], doc_tokens: List[str]) -> float:
        """
        Calculate similarity between query and document using TF-IDF
        """
        if not query_tokens or not doc_tokens:
            return 0.0
        
        # Calculate TF for query and document
        query_tf = self.calculate_tf(query_tokens)
        doc_tf = self.calculate_tf(doc_tokens)
        
        # Calculate TF-IDF vectors
        query_tfidf = {}
        doc_tfidf = {}
        
        # Update IDF corpus
        self.update_idf_corpus([query_tokens, doc_tokens])
        
        # Calculate TF-IDF for query
        for token, tf in query_tf.items():
            idf = self.calculate_idf(token)
            query_tfidf[token] = tf * idf
        
        # Calculate TF-IDF for document
        for token, tf in doc_tf.items():
            idf = self.calculate_idf(token)
            doc_tfidf[token] = tf * idf
        
        # Calculate cosine similarity
        dot_product = 0.0
        for token, tfidf in query_tfidf.items():
            if token in doc_tfidf:
                dot_product += tfidf * doc_tfidf[token]
        
        # Calculate magnitudes
        query_magnitude = math.sqrt(sum(tfidf ** 2 for tfidf in query_tfidf.values()))
        doc_magnitude = math.sqrt(sum(tfidf ** 2 for tfidf in doc_tfidf.values()))
        
        # Avoid division by zero
        if query_magnitude == 0 or doc_magnitude == 0:
            return 0.0
        
        # Calculate cosine similarity
        similarity = dot_product / (query_magnitude * doc_magnitude)
        
        return similarity
    
    def validate_results(self, results: List[Dict], query: str) -> List[Dict]:
        """
        Validate search results to check if they are blogs/articles
        and calculate relevance scores
        """
        query_tokens = self.preprocess_text(query)
        
        for result in results:
            url = result["url"]
            title = result["title"]
            description = result["description"]
            
            # Check if it's a blog/article
            is_blog, blog_score = self.is_blog_article(url, title, description)
            
            # Calculate relevance to query
            combined_text = f"{title} {description}"
            doc_tokens = self.preprocess_text(combined_text)
            
            # Calculate similarity between query and document
            similarity_score = self.calculate_query_similarity(query_tokens, doc_tokens)
            
            # Boost score for exact matches in title
            title_lower = title.lower()
            query_lower = query.lower()
            title_boost = 0.0
            
            if query_lower in title_lower:
                title_boost = 0.3
            else:
                # Check for partial matches
                query_terms = query_lower.split()
                for term in query_terms:
                    if len(term) > 3 and term in title_lower:
                        title_boost += 0.1
                
                # Cap title boost
                title_boost = min(0.3, title_boost)
            
            # Combine scores with weights
            # - Blog score: 50%
            # - Similarity score: 30%
            # - Title boost: 20%
            final_score = (blog_score * 0.5) + (similarity_score * 0.3) + title_boost
            
            # Normalize to 0-1 range
            final_score = min(1.0, final_score)
            
            # Update result
            result["is_blog_article"] = is_blog
            result["score"] = final_score
        
        return results 