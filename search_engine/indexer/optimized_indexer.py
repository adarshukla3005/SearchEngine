"""
Optimized search indexer with compression for deployment
"""
import os
import json
import pickle
import logging
import gzip
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import numpy as np

from utils.text_processing import tokenize, load_stopwords, expand_query

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("indexer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("optimized_indexer")

class OptimizedSearchIndexer:
    """
    Optimized search indexer with compression for deployment
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the indexer with configuration
        """
        self.config = config
        
        # Create index directory if it doesn't exist
        os.makedirs(self.config["index_dir"], exist_ok=True)
        
        # Load stopwords
        self.stopwords = load_stopwords(self.config["stopwords_file"])
        
        # Initialize index data structures
        self.document_map = {}  # Maps doc_id to document metadata
        self.inverted_index = defaultdict(list)  # Maps term to list of (doc_id, term_freq)
        self.document_lengths = {}  # Maps doc_id to document length (for BM25)
        self.average_doc_length = 0.0  # Average document length (for BM25)
        
        # BM25 parameters
        self.k1 = 1.2  # Term frequency saturation parameter
        self.b = 0.75  # Document length normalization parameter
        self.k3 = 8.0  # Query term weight parameter
        
        # Boosting factors
        self.title_boost = self.config.get("title_boost", 3.0)
        self.meta_boost = self.config.get("meta_boost", 2.0)
    
    def optimize_from_existing(self, source_index_dir: str):
        """
        Create an optimized index from an existing index
        """
        # Load existing index
        try:
            # Load document map
            with open(os.path.join(source_index_dir, "document_map.json"), 'r', encoding='utf-8') as f:
                self.document_map = json.load(f)
            
            # Load inverted index
            with open(os.path.join(source_index_dir, "inverted_index.pkl"), 'rb') as f:
                self.inverted_index = defaultdict(list, pickle.load(f))
            
            # Load document lengths
            with open(os.path.join(source_index_dir, "document_lengths.pkl"), 'rb') as f:
                self.document_lengths = pickle.load(f)
            
            # Load average document length
            with open(os.path.join(source_index_dir, "average_doc_length.txt"), 'r') as f:
                self.average_doc_length = float(f.read().strip())
                
            logger.info(f"Loaded existing index with {len(self.document_map)} documents and {len(self.inverted_index)} terms.")
            
            # Now optimize and save
            self._optimize_index()
            self._save_optimized_index()
            
        except Exception as e:
            logger.error(f"Error optimizing index: {e}")
            raise
    
    def _optimize_index(self):
        """
        Optimize the index by:
        1. Removing low-frequency terms
        2. Truncating document content snippets
        3. Removing unnecessary fields
        """
        # 1. Remove terms that appear in very few documents (e.g., only 1 document)
        min_doc_frequency = 2
        terms_to_remove = []
        
        for term, postings in self.inverted_index.items():
            if len(postings) < min_doc_frequency:
                terms_to_remove.append(term)
        
        for term in terms_to_remove:
            del self.inverted_index[term]
            
        logger.info(f"Removed {len(terms_to_remove)} low-frequency terms")
        
        # 2. Truncate document content snippets and remove unnecessary fields
        for doc_id in self.document_map:
            # Truncate content snippet
            if "content_snippet" in self.document_map[doc_id]:
                self.document_map[doc_id]["content_snippet"] = self.document_map[doc_id]["content_snippet"][:100]
            
            # Remove unnecessary fields
            if "confidence" in self.document_map[doc_id]:
                del self.document_map[doc_id]["confidence"]
            if "method" in self.document_map[doc_id]:
                del self.document_map[doc_id]["method"]
    
    def _save_optimized_index(self):
        """
        Save the optimized index with compression
        """
        # Save document map with minimal JSON formatting
        with open(os.path.join(self.config["index_dir"], "document_map.json"), 'w', encoding='utf-8') as f:
            json.dump(self.document_map, f, ensure_ascii=False, separators=(',', ':'))
        
        # Save inverted index with compression
        with gzip.open(os.path.join(self.config["index_dir"], "inverted_index.pkl.gz"), 'wb', compresslevel=9) as f:
            pickle.dump(dict(self.inverted_index), f, protocol=pickle.HIGHEST_PROTOCOL)
        
        # Save document lengths with compression
        with gzip.open(os.path.join(self.config["index_dir"], "document_lengths.pkl.gz"), 'wb', compresslevel=9) as f:
            pickle.dump(self.document_lengths, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        # Save average document length
        with open(os.path.join(self.config["index_dir"], "average_doc_length.txt"), 'w') as f:
            f.write(str(self.average_doc_length))
            
        logger.info(f"Optimized index saved to {self.config['index_dir']}")
    
    def load_optimized_index(self):
        """
        Load the optimized index
        """
        # Load document map
        with open(os.path.join(self.config["index_dir"], "document_map.json"), 'r', encoding='utf-8') as f:
            self.document_map = json.load(f)
        
        # Load inverted index with decompression
        with gzip.open(os.path.join(self.config["index_dir"], "inverted_index.pkl.gz"), 'rb') as f:
            self.inverted_index = defaultdict(list, pickle.load(f))
        
        # Load document lengths with decompression
        with gzip.open(os.path.join(self.config["index_dir"], "document_lengths.pkl.gz"), 'rb') as f:
            self.document_lengths = pickle.load(f)
        
        # Load average document length
        with open(os.path.join(self.config["index_dir"], "average_doc_length.txt"), 'r') as f:
            self.average_doc_length = float(f.read().strip())
        
        logger.info(f"Optimized index loaded with {len(self.document_map)} documents and {len(self.inverted_index)} terms.")
    
    def search(self, query: str, top_k: int = 20) -> List[Dict]:
        """
        Search the index for documents matching the query
        """
        # Check if query is empty
        if not query or query.strip() == "":
            return []
        
        # Expand query with related terms
        expanded_query = expand_query(query)
        
        # Save original query for exact phrase matching
        original_query = query.lower().strip()
        
        # Tokenize query
        query_tokens = tokenize(expanded_query)
        
        # Get original query tokens for exact matching
        original_query_tokens = tokenize(query)
        
        # Filter query tokens
        filtered_query_tokens = [
            token for token in query_tokens
            if token not in self.stopwords
            and self.config["min_token_length"] <= len(token) <= self.config["max_token_length"]
        ]
        
        # If no valid tokens after filtering, return empty results
        if not filtered_query_tokens:
            return []
        
        # Calculate BM25 scores
        scores = self._calculate_bm25_scores(filtered_query_tokens, original_query_tokens, original_query)
        
        # If we have scores, normalize them to 0-1 range
        if scores:
            # Find max score for normalization
            max_score = max(scores.values())
            if max_score > 0:
                # Normalize scores
                for doc_id in scores:
                    scores[doc_id] = scores[doc_id] / max_score
        
        # Sort documents by score
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Get top-k documents
        top_docs = sorted_docs[:top_k]
        
        # Format results
        results = []
        for doc_id, score in top_docs:
            if doc_id in self.document_map and score > 0.05:  # Minimum relevance threshold (5%)
                doc_info = self.document_map[doc_id]
                results.append({
                    "url": doc_info["url"],
                    "title": doc_info["title"],
                    "description": doc_info.get("description", ""),
                    "content_snippet": doc_info.get("content_snippet", ""),
                    "score": score
                })
        
        return results
    
    def _calculate_bm25_scores(self, query_tokens: List[str], original_query_tokens: List[str], original_query: str) -> Dict[str, float]:
        """
        Calculate BM25 scores for documents matching the query tokens with additional relevance boosting
        """
        scores = defaultdict(float)
        N = len(self.document_map)  # Total number of documents
        
        # For each query term
        for qt in query_tokens:
            if qt in self.inverted_index:
                # Calculate IDF for this term
                n = len(self.inverted_index[qt])  # Number of documents containing the term
                idf = max(0.0, np.log((N - n + 0.5) / (n + 0.5)))
                
                # Boost exact matches from original query
                term_importance = 1.8 if qt in original_query_tokens else 1.0
                
                # For each document containing the term
                for doc_id, tf in self.inverted_index[qt]:
                    if doc_id in self.document_lengths:
                        # Calculate BM25 score for this term in this document
                        doc_len = self.document_lengths[doc_id]
                        
                        # BM25 term frequency component
                        tf_component = ((self.k1 + 1) * tf) / (self.k1 * (1 - self.b + self.b * doc_len / self.average_doc_length) + tf)
                        
                        # Add to document score with term importance boost
                        scores[doc_id] += idf * tf_component * term_importance
        
        # Additional boosting for documents with query terms in title and description
        for doc_id in list(scores.keys()):
            if doc_id in self.document_map:
                doc_info = self.document_map[doc_id]
                title = doc_info.get("title", "").lower()
                description = doc_info.get("description", "").lower()
                content = doc_info.get("content_snippet", "").lower()
                
                # Strong boost for exact phrase match in title or description
                if original_query in title:
                    scores[doc_id] *= 1.8
                elif original_query in description:
                    scores[doc_id] *= 1.5
                elif original_query in content:
                    scores[doc_id] *= 1.3
                    
                # Calculate how many original query terms appear in title and description
                title_matches = sum(1 for term in original_query_tokens if term in title)
                desc_matches = sum(1 for term in original_query_tokens if term in description)
                
                # Calculate percentage of query terms that match
                if original_query_tokens:
                    title_match_pct = title_matches / len(original_query_tokens)
                    desc_match_pct = desc_matches / len(original_query_tokens)
                    
                    # Apply graduated boosts based on percentage of matches
                    if title_match_pct > 0:
                        # Up to 200% boost for title matches
                        scores[doc_id] *= (1.0 + title_match_pct * 2.0)
                    
                    if desc_match_pct > 0:
                        # Up to 100% boost for description matches
                        scores[doc_id] *= (1.0 + desc_match_pct * 1.0)
        
        return scores 