"""
Optimized search indexer with compression for deployment
"""
import os
import json
import pickle
import logging
import gzip
import re
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import numpy as np

from utils.text_processing import tokenize, load_stopwords, expand_query, identify_main_terms
try:
    from search_engine.indexer.bert_embeddings import BertEmbeddings
except ImportError:
    # BERT embeddings module might not be available
    pass

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
        
        # BERT embeddings for hybrid search
        self.bert_embeddings = None
        self.use_hybrid_search = False
    
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
    
    def load_optimized_index(self, use_hybrid_search: bool = False):
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
        
        # Initialize BERT embeddings for hybrid search if requested
        self.use_hybrid_search = use_hybrid_search
        if use_hybrid_search:
            try:
                # Import BERT config here to avoid circular imports
                from utils.config import BERT_CONFIG
                self.bert_embeddings = BertEmbeddings(BERT_CONFIG)
                if self.bert_embeddings.load_index():
                    logger.info("BERT embeddings loaded successfully for hybrid search")
                else:
                    logger.warning("Failed to load BERT embeddings. Falling back to BM25 only.")
                    self.use_hybrid_search = False
            except Exception as e:
                logger.error(f"Error initializing BERT embeddings: {e}")
                logger.warning("Falling back to BM25 only.")
                self.use_hybrid_search = False
    
    def search(self, query: str, top_k: int = 20) -> List[Dict]:
        """
        Search the index for documents matching the query
        """
        # Check if query is empty
        if not query or query.strip() == "":
            return []
        
        # Save original query for exact phrase matching
        original_query = query.lower().strip()
        
        # Tokenize query
        query_tokens = tokenize(query)
        
        # Identify main terms using the specialized function
        main_query_terms = identify_main_terms(query, self.stopwords)
        
        # Expand query with related terms
        expanded_query = expand_query(query)
        expanded_query_tokens = tokenize(expanded_query)
        
        # Filter query tokens
        filtered_query_tokens = [
            token for token in expanded_query_tokens
            if token not in self.stopwords
            and self.config["min_token_length"] <= len(token) <= self.config["max_token_length"]
        ]
        
        # If no valid tokens after filtering, return empty results
        if not filtered_query_tokens:
            return []
        
        # Calculate BM25 scores with main term boosting
        bm25_scores = self._calculate_bm25_scores(filtered_query_tokens, query_tokens, original_query, main_query_terms)
        
        # Use hybrid search if enabled
        if self.use_hybrid_search and self.bert_embeddings:
            try:
                # Get BERT similarity scores
                bert_results = self.bert_embeddings.search(query, top_k=top_k*3)
                
                # Convert to dictionary for easier lookup
                bert_scores = {doc_id: score for doc_id, score in bert_results}
                
                # Import BERT config here to avoid circular imports
                from utils.config import BERT_CONFIG
                
                # Combine BM25 and BERT scores with weighted average
                # Default: 70% BM25, 30% BERT
                bert_weight = BERT_CONFIG.get("hybrid_weight", 0.3)
                bm25_weight = 1.0 - bert_weight
                
                # Combine scores
                scores = {}
                
                # Normalize BM25 scores to 0-1 range if we have scores
                if bm25_scores:
                    max_bm25_score = max(bm25_scores.values())
                    if max_bm25_score > 0:
                        normalized_bm25_scores = {doc_id: score / max_bm25_score for doc_id, score in bm25_scores.items()}
                    else:
                        normalized_bm25_scores = bm25_scores
                else:
                    normalized_bm25_scores = {}
                
                # Combine all document IDs from both methods
                all_doc_ids = set(normalized_bm25_scores.keys()) | set(bert_scores.keys())
                
                for doc_id in all_doc_ids:
                    bm25_score = normalized_bm25_scores.get(doc_id, 0.0)
                    bert_score = bert_scores.get(doc_id, 0.0)
                    
                    # Weighted average of both scores
                    scores[doc_id] = (bm25_weight * bm25_score) + (bert_weight * bert_score)
                
                logger.info(f"Hybrid search: BM25 found {len(normalized_bm25_scores)} docs, BERT found {len(bert_scores)} docs, combined {len(scores)} docs")
                
            except Exception as e:
                logger.error(f"Error in hybrid search: {e}")
                logger.warning("Falling back to BM25 only.")
                scores = bm25_scores
        else:
            # Just use BM25 scores
            scores = bm25_scores
            
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
        top_docs = sorted_docs[:top_k*3]  # Get more results initially for filtering
        
        # Format results with minimum relevance threshold
        results = []
        min_relevance_threshold = 0.08  # Increased minimum relevance threshold
        
        # Track which documents contain which main terms for filtering
        main_term_presence = self._get_main_term_document_presence(main_query_terms)
        
        # Determine minimum required main terms (at least 1, or more for longer queries)
        min_required_main_terms = max(1, len(main_query_terms) // 2)
        
        # Domains to exclude (e.g., Spotify blogs)
        excluded_domains = {"open.spotify.com", "spotify.com", "podcasts.apple.com", "podcasts.google.com"}
        
        for doc_id, score in top_docs:
            if doc_id in self.document_map and score > min_relevance_threshold:
                doc_info = self.document_map[doc_id]
                
                # Skip documents from excluded domains
                url = doc_info.get("url", "").lower()
                if any(domain in url for domain in excluded_domains):
                    continue
                
                # Check if document contains enough main terms
                if main_query_terms and doc_id in main_term_presence:
                    present_main_terms = len(main_term_presence[doc_id])
                    if present_main_terms < min_required_main_terms:
                        continue  # Skip documents without enough main terms
                
                # Truncate content snippet to 2-3 lines (approximately 150-200 characters)
                content_snippet = doc_info.get("content_snippet", "")
                if content_snippet:
                    # Count up to 3 newlines or 200 characters
                    end_pos = 0
                    newline_count = 0
                    
                    for i, char in enumerate(content_snippet):
                        if char == '\n':
                            newline_count += 1
                            if newline_count >= 3:  # Limit to 3 lines
                                end_pos = i
                                break
                        if i >= 200:  # Maximum 200 characters
                            end_pos = i
                            break
                    
                    # If we found a cutoff point, truncate the snippet
                    if end_pos > 0:
                        content_snippet = content_snippet[:end_pos] + "..."
                    elif len(content_snippet) > 200:
                        content_snippet = content_snippet[:200] + "..."
                
                results.append({
                    "url": doc_info["url"],
                    "title": doc_info["title"],
                    "description": doc_info.get("description", ""),
                    "content_snippet": content_snippet,
                    "score": score,
                    "main_terms_matched": len(main_term_presence.get(doc_id, set())) if main_query_terms else 0,
                    "search_method": "Hybrid BM25+BERT" if self.use_hybrid_search else "BM25"
                })
                
                # Stop once we have enough results
                if len(results) >= top_k:
                    break
        
        return results
    
    def _calculate_bm25_scores(self, query_tokens: List[str], original_query_tokens: List[str], 
                              original_query: str, main_query_terms: List[str]) -> Dict[str, float]:
        """
        Calculate BM25 scores for documents matching the query tokens with additional relevance boosting
        """
        scores = defaultdict(float)
        N = len(self.document_map)  # Total number of documents
        
        # Track which documents contain which main terms
        main_term_presence = defaultdict(set)
        
        # For each query term
        for qt in query_tokens:
            if qt in self.inverted_index:
                # Calculate IDF for this term
                n = len(self.inverted_index[qt])  # Number of documents containing the term
                idf = max(0.0, np.log((N - n + 0.5) / (n + 0.5)))
                
                # Determine term importance based on whether it's a main term
                term_importance = 2.5 if qt in main_query_terms else 1.0
                
                # Additional boost for exact matches from original query
                if qt in original_query_tokens:
                    term_importance *= 1.8
                
                # For each document containing the term
                for doc_id, tf in self.inverted_index[qt]:
                    if doc_id in self.document_lengths:
                        # Calculate BM25 score for this term in this document
                        doc_len = self.document_lengths[doc_id]
                        
                        # BM25 term frequency component
                        tf_component = ((self.k1 + 1) * tf) / (self.k1 * (1 - self.b + self.b * doc_len / self.average_doc_length) + tf)
                        
                        # Add to document score with term importance boost
                        scores[doc_id] += idf * tf_component * term_importance
                        
                        # Track main term presence
                        if qt in main_query_terms:
                            main_term_presence[doc_id].add(qt)
        
        # Additional boosting for documents with query terms in title and description
        for doc_id in list(scores.keys()):
            if doc_id in self.document_map:
                doc_info = self.document_map[doc_id]
                title = doc_info.get("title", "").lower()
                description = doc_info.get("description", "").lower()
                content = doc_info.get("content_snippet", "").lower()
                
                # Strong boost for exact phrase match in title or description
                if original_query in title:
                    scores[doc_id] *= 2.0
                elif original_query in description:
                    scores[doc_id] *= 1.7
                elif original_query in content:
                    scores[doc_id] *= 1.4
                
                # Boost for main terms appearing in title/description
                main_term_title_matches = sum(1 for term in main_query_terms if term in title)
                main_term_desc_matches = sum(1 for term in main_query_terms if term in description)
                
                # Calculate percentage of main query terms that match
                if main_query_terms:
                    main_term_title_pct = main_term_title_matches / len(main_query_terms)
                    main_term_desc_pct = main_term_desc_matches / len(main_query_terms)
                    
                    # Apply stronger boosts for main term matches
                    if main_term_title_pct > 0:
                        # Up to 250% boost for main term title matches
                        scores[doc_id] *= (1.0 + main_term_title_pct * 2.5)
                    
                    if main_term_desc_pct > 0:
                        # Up to 150% boost for main term description matches
                        scores[doc_id] *= (1.0 + main_term_desc_pct * 1.5)
                
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
                
                # Proximity boost - check if main terms appear close together in content
                if len(main_query_terms) > 1 and content:
                    proximity_score = self._calculate_term_proximity(content, main_query_terms)
                    if proximity_score > 0:
                        scores[doc_id] *= (1.0 + proximity_score * 0.5)  # Up to 50% boost
                
                # Apply a significant boost if all main terms are present in the document
                if main_query_terms and len(main_term_presence[doc_id]) == len(main_query_terms):
                    # All main terms are present - major boost (3x)
                    scores[doc_id] *= 3.0
                elif main_query_terms and len(main_term_presence[doc_id]) >= len(main_query_terms) * 0.75:
                    # At least 75% of main terms are present - good boost (2x)
                    scores[doc_id] *= 2.0
                elif main_query_terms and len(main_term_presence[doc_id]) >= len(main_query_terms) * 0.5:
                    # At least 50% of main terms are present - moderate boost (1.5x)
                    scores[doc_id] *= 1.5
                elif main_query_terms and len(main_term_presence[doc_id]) < len(main_query_terms) * 0.5:
                    # Less than half of main terms are present - reduce score
                    scores[doc_id] *= 0.7
        
        return scores
        
    def _calculate_term_proximity(self, text: str, terms: List[str]) -> float:
        """
        Calculate how close the query terms appear together in text
        Returns a score between 0 and 1, where 1 means all terms are adjacent
        """
        if not terms or not text:
            return 0.0
            
        # Find positions of all terms in the text
        positions = {}
        for term in terms:
            positions[term] = [m.start() for m in re.finditer(r'\b' + re.escape(term) + r'\b', text)]
            
        # If any term is missing, return 0
        if any(len(pos) == 0 for pos in positions.values()):
            return 0.0
            
        # Calculate minimum distance between terms
        min_distance = float('inf')
        term_count = len(terms)
        
        # For each position of the first term
        for pos1 in positions[terms[0]]:
            # Find closest positions of other terms
            max_distance = 0
            found_all = True
            
            for i in range(1, term_count):
                term_positions = positions[terms[i]]
                closest_pos = min(term_positions, key=lambda x: abs(x - pos1))
                distance = abs(closest_pos - pos1)
                max_distance = max(max_distance, distance)
                
                if distance > len(text) // 4:  # If terms are too far apart (more than 25% of text length)
                    found_all = False
                    break
            
            if found_all and max_distance < min_distance:
                min_distance = max_distance
        
        # Convert distance to proximity score (inverse relationship)
        if min_distance == float('inf'):
            return 0.0
        
        # Normalize by text length, with a maximum meaningful distance of 100 characters
        max_meaningful_distance = min(100, len(text) // 2)
        proximity_score = 1.0 - min(min_distance, max_meaningful_distance) / max_meaningful_distance
        
        return proximity_score
    
    def _get_main_term_document_presence(self, main_terms: List[str]) -> Dict[str, Set[str]]:
        """
        Find which documents contain which main terms
        Returns a dictionary mapping doc_id to a set of main terms it contains
        """
        presence = defaultdict(set)
        
        for term in main_terms:
            if term in self.inverted_index:
                for doc_id, _ in self.inverted_index[term]:
                    presence[doc_id].add(term)
                    
        return presence 