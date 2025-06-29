"""
Optimized search indexer for production use
"""
import os
import gzip
import json
import pickle
import logging
import gc
from collections import defaultdict

from search_engine.indexer.indexer import SearchIndexer
from search_engine.indexer.bert_embeddings import BertEmbeddings

logger = logging.getLogger("optimized_indexer")

class OptimizedSearchIndexer(SearchIndexer):
    """
    Optimized version of the search indexer for production use
    """
    
    def __init__(self, config):
        """
        Initialize the optimized search indexer
        
        Args:
            config (dict): Configuration dictionary
        """
        super().__init__(config)
        self.bert_embeddings = None
        self.index_dir = config["index_dir"]
        self.average_doc_length = 0
        self.document_lengths = {}
        self.inverted_index = {}
        self.document_map = {}
        self.stopwords = set()
        
    def load_optimized_index(self, use_hybrid_search=True):
        """
        Load the optimized index from disk
        
        Args:
            use_hybrid_search (bool): Whether to use hybrid search (BM25 + BERT)
        """
        # Load document map
        doc_map_path = os.path.join(self.index_dir, "document_map.json")
        logger.info(f"Loading document map from {doc_map_path}")
        with open(doc_map_path, 'r', encoding='utf-8') as f:
            self.document_map = json.load(f)
        
        # Force garbage collection after loading document map
        gc.collect()
        
        # Load inverted index
        inv_index_path = os.path.join(self.index_dir, "inverted_index.pkl.gz")
        logger.info(f"Loading inverted index from {inv_index_path}")
        with gzip.open(inv_index_path, 'rb') as f:
            self.inverted_index = pickle.load(f)
        
        # Force garbage collection after loading inverted index
        gc.collect()
        
        # Load document lengths
        doc_lengths_path = os.path.join(self.index_dir, "document_lengths.pkl.gz")
        logger.info(f"Loading document lengths from {doc_lengths_path}")
        with gzip.open(doc_lengths_path, 'rb') as f:
            self.document_lengths = pickle.load(f)
        
        # Force garbage collection after loading document lengths
        gc.collect()
        
        # Load average document length
        avg_doc_length_path = os.path.join(self.index_dir, "average_doc_length.txt")
        logger.info(f"Loading average document length from {avg_doc_length_path}")
        with open(avg_doc_length_path, 'r') as f:
            self.average_doc_length = float(f.read().strip())
        
        # Load stopwords
        stopwords_path = os.path.join(self.index_dir, "stopwords.txt")
        logger.info(f"Loading stopwords from {stopwords_path}")
        with open(stopwords_path, 'r', encoding='utf-8') as f:
            self.stopwords = set(line.strip() for line in f)
        
        logger.info(f"Optimized index loaded with {len(self.document_map)} documents and {len(self.inverted_index)} terms.")
        
        # Load BERT embeddings if hybrid search is enabled
        if use_hybrid_search:
            try:
                # Force garbage collection before loading BERT
                gc.collect()
                
                # Import BERT_CONFIG from utils.config
                from utils.config import BERT_CONFIG
                
                self.bert_embeddings = BertEmbeddings(BERT_CONFIG)
                self.bert_embeddings.load_index()
                logger.info("BERT embeddings loaded successfully for hybrid search")
            except Exception as e:
                logger.error(f"Error loading BERT embeddings: {e}")
                logger.error("Falling back to BM25-only search")
                self.bert_embeddings = None
        else:
            logger.info("Hybrid search disabled, using BM25-only search")
    
    def bm25_search(self, query, top_k=20):
        """
        Perform BM25 search for the given query
        
        Args:
            query (str): The search query
            top_k (int): The number of results to return
            
        Returns:
            list: The search results
        """
        # Use the parent class's search method
        return super().search(query, top_k=top_k)
    
    def combine_results(self, bm25_results, bert_results, top_k=10):
        """
        Combine BM25 and BERT search results
        
        Args:
            bm25_results (list): BM25 search results
            bert_results (list): BERT search results
            top_k (int): The number of results to return
            
        Returns:
            list: The combined search results
        """
        # Convert BM25 results to dictionary for easier lookup
        bm25_dict = {result["url"]: result for result in bm25_results}
        
        # Convert BERT results to dictionary
        bert_dict = {doc_id: score for doc_id, score in bert_results}
        
        # Combine results with weighted scores
        # Default: 70% BM25, 30% BERT
        bm25_weight = 0.7
        bert_weight = 0.3
        
        combined_results = []
        
        # Process BM25 results first
        for result in bm25_results:
            url = result["url"]
            doc_id = next((id for id in bert_dict if id in self.document_map and self.document_map[id]["url"] == url), None)
            
            if doc_id and doc_id in bert_dict:
                # Normalize BM25 score (already normalized in parent class)
                bm25_score = result["score"]
                
                # Get BERT score
                bert_score = bert_dict[doc_id]
                
                # Calculate combined score
                combined_score = (bm25_weight * bm25_score) + (bert_weight * bert_score)
                
                # Create combined result
                combined_result = result.copy()
                combined_result["score"] = combined_score
                combined_result["search_method"] = "Hybrid BM25+BERT"
                
                combined_results.append(combined_result)
        
        # Sort by combined score
        combined_results.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top-k results
        return combined_results[:top_k]
    
    def search(self, query, top_k=10):
        """
        Search the index for the given query
        
        Args:
            query (str): The search query
            top_k (int): The number of results to return
            
        Returns:
            list: The search results
        """
        # BM25 search
        bm25_results = self.bm25_search(query, top_k=top_k*2)
        
        # If BERT embeddings are not available or there are no results, return BM25 results
        if self.bert_embeddings is None or not bm25_results:
            return bm25_results[:top_k]
        
        try:
            # BERT search
            bert_results = self.bert_embeddings.search(query, top_k=top_k)
            
            # Combine results
            combined_results = self.combine_results(bm25_results, bert_results, top_k)
            
            logger.info(f"Hybrid search: BM25 found {len(bm25_results)} docs, BERT found {len(bert_results)} docs, combined {len(combined_results)} docs")
            
            return combined_results
        except Exception as e:
            logger.error(f"Error in BERT search: {e}")
            logger.error("Falling back to BM25-only search")
            return bm25_results[:top_k]
            
    def optimize_from_existing(self, source_index_dir):
        """
        Optimize an existing index and save it to the configured index directory
        
        Args:
            source_index_dir (str): Path to the source index directory
        """
        logger.info(f"Optimizing index from {source_index_dir} to {self.index_dir}")
        
        try:
            # Make sure target directory exists
            os.makedirs(self.index_dir, exist_ok=True)
            
            # Copy document map from source
            with open(os.path.join(source_index_dir, "document_map.json"), 'r', encoding='utf-8') as f:
                document_map = json.load(f)
                
            # Copy inverted index from source
            with open(os.path.join(source_index_dir, "inverted_index.pkl"), 'rb') as f:
                inverted_index = pickle.load(f)
                
            # Copy document lengths from source
            with open(os.path.join(source_index_dir, "document_lengths.pkl"), 'rb') as f:
                document_lengths = pickle.load(f)
                
            # Copy average document length from source
            with open(os.path.join(source_index_dir, "average_doc_length.txt"), 'r') as f:
                average_doc_length = float(f.read().strip())
            
            # Save document map to target
            with open(os.path.join(self.index_dir, "document_map.json"), 'w', encoding='utf-8') as f:
                json.dump(document_map, f, ensure_ascii=False)
            
            # Save compressed inverted index to target
            with gzip.open(os.path.join(self.index_dir, "inverted_index.pkl.gz"), 'wb') as f:
                pickle.dump(inverted_index, f)
            
            # Save compressed document lengths to target
            with gzip.open(os.path.join(self.index_dir, "document_lengths.pkl.gz"), 'wb') as f:
                pickle.dump(document_lengths, f)
            
            # Save average document length to target
            with open(os.path.join(self.index_dir, "average_doc_length.txt"), 'w') as f:
                f.write(str(average_doc_length))
                
            # Create empty stopwords file if it doesn't exist
            stopwords_file = os.path.join(self.index_dir, "stopwords.txt")
            if not os.path.exists(stopwords_file):
                with open(stopwords_file, 'w', encoding='utf-8') as f:
                    pass
            
            logger.info("Index optimization completed")
            
        except Exception as e:
            logger.error(f"Error optimizing index: {e}")
            raise 