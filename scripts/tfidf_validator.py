"""
Enhanced validation for search results using BM25 and Semantic Similarity
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
    Enhanced validator for identifying blog posts and articles using BM25 and semantic similarity
    """
    
    def __init__(self):
        """
        Initialize the validator
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
        
        # Additional content indicators for blogs
        self.content_indicators = [
            "read", "learn", "discover", "explore", "understand",
            "guide", "tutorial", "tips", "advice", "strategy",
            "insight", "perspective", "opinion", "review", "analysis",
            "explanation", "breakdown", "deep dive", "case study"
        ]
        
        # IDF corpus (will be built dynamically)
        self.idf_corpus = {}
        self.corpus_size = 0
        
        # BM25 parameters - standard values from literature
        self.k1 = 1.5  # Term frequency saturation parameter
        self.b = 0.75  # Document length normalization
        
        # Document length normalization factors
        self.avg_doc_length = 100  # Will be updated as documents are processed
        self.doc_lengths = {}
        
        try:
            # Try to import sentence-transformers if available
            from sentence_transformers import SentenceTransformer
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            self.use_semantic = True
            logger.info("Sentence transformer model loaded successfully for semantic search")
        except ImportError:
            self.use_semantic = False
            logger.info("Sentence transformer not available - semantic search disabled")
    
    def preprocess_text(self, text: str) -> List[str]:
        """
        Preprocess text for BM25 calculation - improved tokenization
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters and digits
        text = re.sub(r'[^\w\s-]', ' ', text)  # Keep hyphens as they may be important
        text = re.sub(r'\d+', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Tokenize
        tokens = text.split()
        
        # Remove very short tokens and stop words
        tokens = [token for token in tokens if len(token) > 2 and token not in self.get_stop_words()]
        
        return tokens
    
    def get_stop_words(self) -> set:
        """
        Return a set of English stop words
        """
        return {
            "a", "an", "the", "and", "or", "but", "if", "because", "as", "what",
            "which", "this", "that", "these", "those", "then", "just", "so", "than",
            "such", "when", "who", "how", "where", "why", "is", "are", "was", "were",
            "be", "been", "being", "have", "has", "had", "having", "do", "does", "did",
            "doing", "would", "should", "could", "ought", "i", "you", "he", "she", "it",
            "we", "they", "their", "his", "her", "him", "them", "its", "our", "your",
            "of", "at", "by", "for", "with", "about", "against", "between", "into",
            "through", "during", "before", "after", "above", "below", "to", "from",
            "up", "down", "in", "out", "on", "off", "over", "under", "again", "further",
            "then", "once", "here", "there", "all", "any", "both", "each", "few", "more",
            "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same",
            "so", "than", "too", "very", "can", "will", "just", "don", "don't", "should",
            "now", "also", "may", "like"
        }
    
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
        # Update doc lengths for BM25
        for i, doc_tokens in enumerate(documents):
            doc_id = f"doc_{i}_{len(doc_tokens)}"
            self.doc_lengths[doc_id] = len(doc_tokens)
        
        # Update average document length
        if self.doc_lengths:
            self.avg_doc_length = sum(self.doc_lengths.values()) / len(self.doc_lengths)
        
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
        Calculate IDF for a token using BM25's variant of IDF
        """
        if self.corpus_size == 0 or token not in self.idf_corpus:
            return 0.0
        
        # BM25 variant of IDF calculation
        n = self.corpus_size
        df = self.idf_corpus[token]
        return math.log((n - df + 0.5) / (df + 0.5) + 1.0)
    
    def calculate_bm25_score(self, query_tokens: List[str], doc_tokens: List[str]) -> float:
        """
        Calculate BM25 score between query and document
        """
        if not query_tokens or not doc_tokens:
            return 0.0
        
        # Document length
        doc_length = len(doc_tokens)
        
        # Count term frequencies in document
        doc_term_freq = Counter(doc_tokens)
        
        # Calculate BM25 score
        score = 0.0
        for token in query_tokens:
            if token in doc_term_freq:
                # Term frequency in document
                tf = doc_term_freq[token]
                
                # IDF score for token
                idf = self.calculate_idf(token)
                
                # BM25 term scoring formula
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)
                score += idf * (numerator / denominator)
        
        return score
    
    def calculate_semantic_similarity(self, query: str, document: str) -> float:
        """
        Calculate semantic similarity using sentence embeddings
        """
        if not self.use_semantic:
            return 0.0
            
        try:
            # Create embeddings
            query_embedding = self.embedder.encode(query, convert_to_tensor=True)
            doc_embedding = self.embedder.encode(document, convert_to_tensor=True)
            
            # Calculate cosine similarity
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
            
            query_embedding_np = query_embedding.cpu().numpy().reshape(1, -1)
            doc_embedding_np = doc_embedding.cpu().numpy().reshape(1, -1)
            
            similarity = cosine_similarity(query_embedding_np, doc_embedding_np)[0][0]
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating semantic similarity: {e}")
            return 0.0
    
    def is_blog_article(self, url: str, title: str, description: str) -> Tuple[bool, float]:
        """
        Determine if a search result is a blog/article and calculate relevance score
        """
        # Check URL for blog indicators
        url_lower = url.lower()
        domain_score = 0.0
        
        # Check for blog domains with higher weight
        for domain in self.blog_domains:
            if domain in url_lower:
                domain_score += 0.25
                break
        
        # Check for blog URL patterns with higher weight
        if "/blog/" in url_lower or "/article/" in url_lower or "/post/" in url_lower:
            domain_score += 0.35
        elif "/posts/" in url_lower or "/essays/" in url_lower or "/writing/" in url_lower:
            domain_score += 0.3
        
        # Additional URL patterns that might indicate blogs
        if "/insights/" in url_lower or "/news/" in url_lower or "/opinion/" in url_lower:
            domain_score += 0.2
        
        # Combine title and description for content analysis
        combined_text = f"{title} {description}"
        tokens = self.preprocess_text(combined_text)
        
        # Calculate TF for the document
        tf = self.calculate_tf(tokens)
        
        # Calculate score based on blog/article terms with higher weight
        term_score = 0.0
        for term in self.blog_article_terms:
            if term in tf:
                term_score += tf[term] * 2.5
        
        # Check for content indicators
        for term in self.content_indicators:
            if term in tf:
                term_score += tf[term] * 1.5
        
        # Normalize term score with higher cap
        term_score = min(0.5, term_score)
        
        # Check for structural patterns with higher weight
        structure_score = 0.0
        for pattern in self.structural_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                structure_score += 0.07
        
        # Cap structure score with higher cap
        structure_score = min(0.35, structure_score)
        
        # Add base score to ensure minimum confidence
        base_score = 0.1
        
        # Calculate final score
        final_score = base_score + domain_score + term_score + structure_score
        
        # Normalize to 0-1 range
        final_score = min(1.0, final_score)
        
        # Determine if it's a blog/article (threshold of 0.3)
        is_blog = final_score >= 0.3
        
        logger.debug(f"URL: {url}, Score: {final_score}, Is blog/article: {is_blog}")
        
        return is_blog, final_score
    
    def validate_results(self, results: List[Dict], query: str) -> List[Dict]:
        """
        Validate search results to check if they are blogs/articles
        and calculate relevance scores using enhanced algorithms
        """
        query_tokens = self.preprocess_text(query)
        
        for result in results:
            url = result["url"]
            title = result["title"] 
            description = result["description"]
            
            # Check if it's a blog/article
            is_blog, blog_score = self.is_blog_article(url, title, description)
            
            # Calculate BM25 relevance score
            combined_text = f"{title} {description}"
            doc_tokens = self.preprocess_text(combined_text)
            
            # BM25 score - higher weight for relevance
            bm25_score = self.calculate_bm25_score(query_tokens, doc_tokens)
            # Normalize BM25 score to 0-1 range (typically scores are higher than 1)
            normalized_bm25 = min(1.0, bm25_score / 10.0)
            
            # Calculate semantic similarity if available
            semantic_score = 0.0
            if self.use_semantic:
                semantic_score = self.calculate_semantic_similarity(query, combined_text)
            
            # Boost score for exact matches in title
            title_lower = title.lower()
            query_lower = query.lower()
            title_boost = 0.0
            
            if query_lower in title_lower:
                title_boost = 0.4
            else:
                # Check for partial matches with higher boost
                query_terms = query_lower.split()
                for term in query_terms:
                    if len(term) > 3 and term in title_lower:
                        title_boost += 0.35 / len(query_terms)  # Normalize by number of terms
                
                # Cap title boost
                title_boost = min(0.4, title_boost)
            
            # Add source boost (favor discovered blogs slightly)
            source_boost = 0.25 if result.get("source") == "Discovered Blog" else 0.15
            
            # Check for content quality indicators
            quality_score = 0.0
            
            # Length-based quality heuristic - longer descriptions tend to be better quality
            if len(description) > 200:
                quality_score += 0.1
            
            # Indicate presence of semantic score in results for debugging
            if self.use_semantic and semantic_score > 0:
                result["semantic_score"] = round(semantic_score, 3)
            
            # Combine scores with adjusted weights
            # - Blog score: 35%
            # - BM25 score: 25%
            # - Semantic score: 20% (if available)
            # - Title boost: 15%
            # - Quality score: 5%
            # - Source boost: 5%
            if self.use_semantic:
                final_score = (blog_score * 0.35) + (normalized_bm25 * 0.25) + \
                               (semantic_score * 0.2) + (title_boost * 0.15) + \
                               (quality_score * 0.05) + (source_boost * 0.05)
            else:
                # Without semantic scoring, redistribute weights
                final_score = (blog_score * 0.40) + (normalized_bm25 * 0.35) + \
                               (title_boost * 0.15) + (quality_score * 0.05) + \
                               (source_boost * 0.05)
            
            # Apply minimum score to ensure reasonable confidence
            final_score = max(0.3, final_score)
            
            # Normalize to 0-1 range
            final_score = min(1.0, final_score)
            
            # Store BM25 score for debugging
            result["bm25_score"] = round(normalized_bm25, 3)
            
            # Update result
            result["is_blog_article"] = is_blog
            result["score"] = final_score
        
        return results 