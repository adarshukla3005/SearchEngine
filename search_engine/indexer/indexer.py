"""
Search indexer for the Personal Blog Search Engine
"""
import os
import json
import pickle
import logging
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import numpy as np
from tqdm import tqdm

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
logger = logging.getLogger("indexer")

class SearchIndexer:
    """
    Search indexer for building and querying the search index
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
        
        # BM25 parameters - tuned for better results
        self.k1 = 1.2  # Term frequency saturation parameter
        self.b = 0.75  # Document length normalization parameter
        self.k3 = 8.0  # Query term weight parameter
        
        # Boosting factors
        self.title_boost = self.config.get("title_boost", 3.0)
        self.meta_boost = self.config.get("meta_boost", 2.0)
    
    def _process_document(self, doc_id: str, document: Dict) -> Dict[str, float]:
        """
        Process a document and return its tokens with field-specific weights
        Returns a dict mapping token -> weighted frequency
        """
        # Extract text from document fields
        title = document.get("title", "")
        meta_desc = document.get("meta_description", "")
        content = document.get("content", "")
        
        # Process each field separately
        title_tokens = tokenize(title)
        meta_tokens = tokenize(meta_desc)
        content_tokens = tokenize(content)
        
        # Filter tokens
        filtered_title_tokens = [
            token for token in title_tokens
            if token not in self.stopwords
            and self.config["min_token_length"] <= len(token) <= self.config["max_token_length"]
        ]
        
        filtered_meta_tokens = [
            token for token in meta_tokens
            if token not in self.stopwords
            and self.config["min_token_length"] <= len(token) <= self.config["max_token_length"]
        ]
        
        filtered_content_tokens = [
            token for token in content_tokens
            if token not in self.stopwords
            and self.config["min_token_length"] <= len(token) <= self.config["max_token_length"]
        ]
        
        # Apply field-specific boosting
        weighted_tokens = defaultdict(float)
        
        # Add title tokens with boost
        for token in filtered_title_tokens:
            weighted_tokens[token] += self.title_boost
        
        # Add meta description tokens with boost
        for token in filtered_meta_tokens:
            weighted_tokens[token] += self.meta_boost
        
        # Add content tokens with normal weight
        for token in filtered_content_tokens:
            weighted_tokens[token] += 1.0
        
        return weighted_tokens
    
    def build_index_from_crawled(self, documents_dir: str):
        """
        Build the search index directly from crawled documents
        """
        # Get list of all JSON files in the documents directory
        json_files = [f for f in os.listdir(documents_dir) if f.endswith('.json') and f not in ['visited_urls.json', 'visited_urls.json.bak']]
        
        # Process documents in chunks
        total_docs = 0
        total_tokens = 0
        
        with tqdm(total=len(json_files), desc="Indexing") as pbar:
            for chunk_start in range(0, len(json_files), self.config["chunk_size"]):
                chunk_files = json_files[chunk_start:chunk_start + self.config["chunk_size"]]
                
                for json_file in chunk_files:
                    try:
                        # Load document
                        with open(os.path.join(documents_dir, json_file), 'r', encoding='utf-8') as f:
                            document = json.load(f)
                        
                        # Generate document ID
                        doc_id = json_file.replace('.json', '')
                        
                        # Process document
                        weighted_tokens = self._process_document(doc_id, document)
                        
                        # Store document metadata
                        self.document_map[doc_id] = {
                            "url": document["url"],
                            "title": document.get("title", ""),
                            "description": document.get("meta_description", ""),
                            "content_snippet": document.get("content", "")[:200] + "..." if document.get("content") else ""
                        }
                        
                        # Store document length as sum of weighted frequencies
                        doc_length = sum(weighted_tokens.values())
                        self.document_lengths[doc_id] = doc_length
                        
                        # Update inverted index
                        for term, weight in weighted_tokens.items():
                            self.inverted_index[term].append((doc_id, weight))
                        
                        total_docs += 1
                        total_tokens += len(weighted_tokens)
                        
                    except Exception as e:
                        logger.error(f"Error processing {json_file}: {e}")
                    
                    pbar.update(1)
        
        # Calculate average document length
        if total_docs > 0:
            self.average_doc_length = sum(self.document_lengths.values()) / total_docs
        
        # Save index
        self._save_index()
        
        logger.info(f"Indexing completed. {total_docs} pages indexed with {len(self.inverted_index)} unique terms.")
    
    def build_index(self, documents_dir: str):
        """
        Build the search index from classified documents
        """
        # Get list of all JSON files in the documents directory
        json_files = [f for f in os.listdir(documents_dir) if f.endswith('.json') and f != 'classification_summary.json']
        
        # Process documents in chunks
        total_docs = 0
        total_tokens = 0
        personal_blogs = 0
        
        with tqdm(total=len(json_files), desc="Indexing") as pbar:
            for chunk_start in range(0, len(json_files), self.config["chunk_size"]):
                chunk_files = json_files[chunk_start:chunk_start + self.config["chunk_size"]]
                
                for json_file in chunk_files:
                    try:
                        # Load document
                        with open(os.path.join(documents_dir, json_file), 'r', encoding='utf-8') as f:
                            document = json.load(f)
                        
                        # Skip non-personal blogs
                        if not document.get("is_personal_blog", False):
                            pbar.update(1)
                            continue
                        
                        # Generate document ID
                        doc_id = json_file.replace('.json', '')
                        
                        # Process document
                        weighted_tokens = self._process_document(doc_id, document)
                        
                        # Store document metadata
                        self.document_map[doc_id] = {
                            "url": document["url"],
                            "title": document.get("title", ""),
                            "description": document.get("meta_description", ""),
                            "content_snippet": document.get("content", "")[:200] + "..." if document.get("content") else "",
                            "confidence": document.get("confidence", 0.0),
                            "method": document.get("method", "")
                        }
                        
                        # Store document length as sum of weighted frequencies
                        doc_length = sum(weighted_tokens.values())
                        self.document_lengths[doc_id] = doc_length
                        
                        # Update inverted index
                        for term, weight in weighted_tokens.items():
                            self.inverted_index[term].append((doc_id, weight))
                        
                        total_docs += 1
                        total_tokens += len(weighted_tokens)
                        personal_blogs += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing {json_file}: {e}")
                    
                    pbar.update(1)
        
        # Calculate average document length
        if total_docs > 0:
            self.average_doc_length = sum(self.document_lengths.values()) / total_docs
        
        # Save index
        self._save_index()
        
        logger.info(f"Indexing completed. {personal_blogs} personal blogs indexed with {len(self.inverted_index)} unique terms.")
    
    def _save_index(self):
        """
        Save the index to disk
        """
        # Save document map
        with open(os.path.join(self.config["index_dir"], "document_map.json"), 'w', encoding='utf-8') as f:
            json.dump(self.document_map, f, ensure_ascii=False)
        
        # Save inverted index
        with open(os.path.join(self.config["index_dir"], "inverted_index.pkl"), 'wb') as f:
            pickle.dump(dict(self.inverted_index), f)
        
        # Save document lengths
        with open(os.path.join(self.config["index_dir"], "document_lengths.pkl"), 'wb') as f:
            pickle.dump(self.document_lengths, f)
        
        # Save average document length
        with open(os.path.join(self.config["index_dir"], "average_doc_length.txt"), 'w') as f:
            f.write(str(self.average_doc_length))
    
    def load_index(self):
        """
        Load the index from disk
        """
        # Load document map
        with open(os.path.join(self.config["index_dir"], "document_map.json"), 'r', encoding='utf-8') as f:
            self.document_map = json.load(f)
        
        # Load inverted index
        with open(os.path.join(self.config["index_dir"], "inverted_index.pkl"), 'rb') as f:
            self.inverted_index = defaultdict(list, pickle.load(f))
        
        # Load document lengths
        with open(os.path.join(self.config["index_dir"], "document_lengths.pkl"), 'rb') as f:
            self.document_lengths = pickle.load(f)
        
        # Load average document length
        with open(os.path.join(self.config["index_dir"], "average_doc_length.txt"), 'r') as f:
            self.average_doc_length = float(f.read().strip())
        
        logger.info(f"Index loaded with {len(self.document_map)} documents and {len(self.inverted_index)} terms.")
    
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
                    "description": doc_info["description"],
                    "content_snippet": self._generate_relevant_snippet(doc_info, original_query_tokens),
                    "score": score
                })
        
        return results
    
    def _generate_relevant_snippet(self, doc_info: Dict, query_tokens: List[str]) -> str:
        """
        Generate a more relevant snippet from document content based on query terms
        """
        content = doc_info.get("content_snippet", "")
        if not content or not query_tokens:
            return content
        
        # Convert to lowercase for case-insensitive matching
        content_lower = content.lower()
        
        # Find the best window containing most query terms
        best_start = 0
        best_count = 0
        window_size = 200  # Characters in snippet window
        
        for i in range(0, len(content) - window_size, 20):  # Step by 20 chars for efficiency
            window = content_lower[i:i+window_size]
            count = sum(1 for term in query_tokens if term in window)
            
            if count > best_count:
                best_count = count
                best_start = i
        
        # If we found a good match, use it; otherwise return the beginning
        if best_count > 0:
            snippet = content[best_start:best_start+window_size] + "..."
        else:
            snippet = content[:200] + "..." if len(content) > 200 else content
        
        return snippet
    
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
                
                # Strong boost for exact phrase match in title or description (80% boost)
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
                        
                # Term proximity boost - if all terms appear close together
                if len(original_query_tokens) > 1 and all(term in content for term in original_query_tokens):
                    scores[doc_id] *= 1.25
        
        return scores 