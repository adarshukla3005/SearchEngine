"""
Configuration settings for the Personal Blog Search Engine
"""
import os

# Crawler settings
CRAWLER_CONFIG = {
    "max_pages": 200,     # Maximum number of pages to crawl
    "max_depth": 5,        # Maximum depth to crawl from seed URLs
    "rate_limit": 0.2,     # Time to wait between requests (seconds)
    "user_agent": "PersonalBlogSearchBot/1.0",
    "timeout": 25,         # Request timeout in seconds
    "respect_robots": True,  # Whether to respect robots.txt
    "skip_previously_crawled": True,  # Skip pages we've already crawled before
    "seed_urls": [
        # "https://manassaloi.com/posts/",
        "https://waitbutwhy.com/",
        # "https://www.ribbonfarm.com/",
        # "https://www.brainpickings.org/",
        # "https://www.farnamstreetblog.com/",
        # "https://paulgraham.com/articles.html",
        # "https://seths.blog/",
        # "https://stratechery.com/",
        # "https://tim.blog/",
        # "https://www.kalzumeus.com/",
        # "https://slatestarcodex.com/",
        # "https://fs.blog/",
        # "https://blog.samaltman.com/",
        # "https://nav.al/",
        # "https://jamesclear.com/articles",
        "https://www.markmanson.net/",
        # "https://www.perell.com/blog",
        # "https://www.eugenewei.com/",
        # "https://andymatuschak.org/",
        # "https://sirupsen.com/",
        # "https://jvns.ca/",
        "https://overreacted.io/",
        # "https://blog.pragmaticengineer.com/",
        # "https://www.hanselman.com/blog/",
        # "https://www.joelonsoftware.com/",
        # "https://blog.codinghorror.com/",
        # "https://martinfowler.com/",
        # "https://davidwalsh.name/",
        # "https://www.swyx.io/",
        # "https://www.joshwcomeau.com/",
        # "https://css-tricks.com/",
        # "https://alistapart.com/",
        # "https://tympanus.net/codrops/",
        # "https://web.dev/blog/",
        # "https://netflixtechblog.com/",
        "https://medium.com/",
        "https://medium.com/free-code-camp",
    ],
    "data_dir": "data/crawled_pages/",
    "article_path_patterns": [
        "/blog/",
        "/article/",
        "/post/",
        "/posts/",
        "/entry/",
        "/entries/",
        "/story/",
        "/stories/",
    ],
}

# Classification settings
CLASSIFIER_CONFIG = {
    "model_name": "google/gemma-2b",  # Using Gemma 2B as a substitute for Gemma-3 1B
    "batch_size": 16,     # Increased batch size for faster processing
    "threshold_domain": 0.7,  # Confidence threshold for domain-based classification
    "threshold_header": 0.8,  # Confidence threshold for header-based classification
    "cache_dir": "data/model_cache/",
    "output_dir": "data/classified_pages/",
}

# Indexer settings
INDEXER_CONFIG = {
    "index_dir": "data/optimized_index/",  # Using optimized index by default
    "chunk_size": 500,  # Number of documents to process at once
    "min_token_length": 2,
    "max_token_length": 20,
    "stopwords_file": "data/optimized_index/stopwords.txt",
    "title_boost": 5.0,   # Increased boost factor for terms in title
    "meta_boost": 3.0,    # Increased boost factor for terms in meta description
}

# BERT model settings for hybrid search
BERT_CONFIG = {
    "model_name": "sentence-transformers/all-MiniLM-L6-v2",  # Fast and lightweight BERT model
    "cache_dir": "data/bert_cache/",
    "embedding_dim": 384,  # Embedding dimension for all-MiniLM-L6-v2
    "batch_size": 32,     # Batch size for encoding
    "max_seq_length": 128,  # Maximum sequence length
    "embeddings_dir": "data/embeddings/",  # Directory to store pre-computed embeddings
    "hybrid_weight": 0.3,  # Weight for BERT score in hybrid scoring (0.3 BERT, 0.7 BM25)
}

# Web interface settings
WEB_CONFIG = {
    "host": "0.0.0.0",  # Listen on all interfaces
    "port": 5000,
    "debug": True,
    "results_per_page": 15,  # Increased number of results per page
}

# Deployment settings
DEPLOYMENT_CONFIG = {
    "is_production": os.environ.get("PRODUCTION", "false").lower() == "true",
    "optimized_index_dir": "data/optimized_index/",
}

# Override settings for production environment
if DEPLOYMENT_CONFIG["is_production"]:
    WEB_CONFIG["debug"] = False
    # Use optimized index in production
    INDEXER_CONFIG["index_dir"] = DEPLOYMENT_CONFIG["optimized_index_dir"] 