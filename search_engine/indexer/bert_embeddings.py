"""
BERT embeddings generator and retrieval for hybrid search
"""
import os
import json
import logging
import numpy as np
import torch
import faiss
from typing import Dict, List, Tuple, Optional
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bert_embeddings.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("bert_embeddings")

class BertEmbeddings:
    """
    BERT embeddings generator and retrieval for hybrid search
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the BERT embeddings generator
        """
        self.config = config
        self.model = None
        self.index = None
        self.doc_ids = []
        
        # Create directories if they don't exist
        os.makedirs(self.config["cache_dir"], exist_ok=True)
        os.makedirs(self.config["embeddings_dir"], exist_ok=True)
        
        # Index file paths
        self.index_file = os.path.join(self.config["embeddings_dir"], "faiss_index.bin")
        self.doc_ids_file = os.path.join(self.config["embeddings_dir"], "doc_ids.json")
    
    def load_model(self):
        """
        Load the BERT model
        """
        if self.model is None:
            logger.info(f"Loading BERT model: {self.config['model_name']}")
            try:
                # Use cache_dir for model files
                self.model = SentenceTransformer(
                    self.config["model_name"],
                    cache_folder=self.config["cache_dir"]
                )
                logger.info("BERT model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading BERT model: {e}")
                raise
    
    def generate_embeddings(self, document_map: Dict[str, Dict]):
        """
        Generate embeddings for all documents in the document map
        """
        self.load_model()
        
        logger.info(f"Generating embeddings for {len(document_map)} documents")
        
        # Prepare documents for embedding
        doc_ids = []
        texts = []
        
        for doc_id, doc_info in tqdm(document_map.items(), desc="Preparing documents"):
            # Combine title and content for better semantic representation
            title = doc_info.get("title", "")
            content = doc_info.get("content_snippet", "")
            description = doc_info.get("description", "")
            
            # Create a combined text representation with more weight on title
            combined_text = f"{title} {title} {description} {content}"
            
            doc_ids.append(doc_id)
            texts.append(combined_text)
        
        # Generate embeddings in batches
        batch_size = self.config["batch_size"]
        embeddings = []
        
        for i in tqdm(range(0, len(texts), batch_size), desc="Generating embeddings"):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = self.model.encode(
                batch_texts, 
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True  # Normalize for cosine similarity
            )
            embeddings.append(batch_embeddings)
        
        # Combine all batches
        all_embeddings = np.vstack(embeddings)
        
        # Create and save FAISS index
        self._create_and_save_index(doc_ids, all_embeddings)
        
        logger.info("Embeddings generation completed")
    
    def _create_and_save_index(self, doc_ids: List[str], embeddings: np.ndarray):
        """
        Create and save FAISS index
        """
        # Create FAISS index - using L2 distance (can be converted to cosine similarity with normalized vectors)
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        
        # Add embeddings to index
        index.add(embeddings)
        
        # Save index to disk
        logger.info(f"Saving FAISS index to {self.index_file}")
        faiss.write_index(index, self.index_file)
        
        # Save document IDs mapping
        logger.info(f"Saving document IDs mapping to {self.doc_ids_file}")
        with open(self.doc_ids_file, 'w') as f:
            json.dump(doc_ids, f)
        
        # Update instance variables
        self.index = index
        self.doc_ids = doc_ids
    
    def load_index(self):
        """
        Load the FAISS index and document IDs mapping
        """
        if not os.path.exists(self.index_file) or not os.path.exists(self.doc_ids_file):
            logger.error("Index files not found. Run generate_embeddings first.")
            return False
        
        try:
            # Load FAISS index
            logger.info(f"Loading FAISS index from {self.index_file}")
            self.index = faiss.read_index(self.index_file)
            
            # Load document IDs mapping
            logger.info(f"Loading document IDs mapping from {self.doc_ids_file}")
            with open(self.doc_ids_file, 'r') as f:
                self.doc_ids = json.load(f)
            
            logger.info(f"Index loaded with {len(self.doc_ids)} documents")
            return True
        except Exception as e:
            logger.error(f"Error loading index: {e}")
            return False
    
    def search(self, query: str, top_k: int = 100) -> List[Tuple[str, float]]:
        """
        Search for similar documents using BERT embeddings
        Returns list of (doc_id, similarity_score) tuples
        """
        if self.index is None or not self.doc_ids:
            if not self.load_index():
                logger.error("Index not loaded. Cannot perform search.")
                return []
        
        if self.model is None:
            self.load_model()
        
        # Generate query embedding
        query_embedding = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        
        # Search in FAISS index
        distances, indices = self.index.search(query_embedding, top_k)
        
        # Convert to list of (doc_id, similarity_score) tuples
        # Note: FAISS returns L2 distances, convert to similarity scores (1 / (1 + distance))
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.doc_ids):
                doc_id = self.doc_ids[idx]
                distance = distances[0][i]
                # Convert distance to similarity score (higher is better)
                similarity = 1.0 / (1.0 + distance)
                results.append((doc_id, similarity))
        
        return results 