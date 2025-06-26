"""
Configuration settings for the Personal Blog Search Engine
"""

# Crawler settings
CRAWLER_CONFIG = {
    "max_pages": 4000,     # Maximum number of pages to crawl
    "max_depth": 5,        # Maximum depth to crawl from seed URLs
    "rate_limit": 0.2,     # Time to wait between requests (seconds)
    "user_agent": "PersonalBlogSearchBot/1.0",
    "timeout": 25,         # Request timeout in seconds
    "respect_robots": True,  # Whether to respect robots.txt
    "seed_urls": [
        "https://manassaloi.com/",
        "https://waitbutwhy.com/",
        "https://www.ribbonfarm.com/",
        "https://www.brainpickings.org/",
        "https://www.farnamstreetblog.com/",
        "https://paulgraham.com/articles.html",
        "https://seths.blog/",
        "https://stratechery.com/",
        "https://tim.blog/",
        "https://www.kalzumeus.com/",
        "https://slatestarcodex.com/",
        "https://fs.blog/",
        "https://blog.samaltman.com/",
        "https://nav.al/",
        "https://jamesclear.com/articles",
        "https://www.markmanson.net/",
        "https://www.perell.com/blog",
        "https://www.eugenewei.com/",
        "https://andymatuschak.org/",
        "https://sirupsen.com/",
        "https://jvns.ca/",
        "https://overreacted.io/",
        "https://blog.pragmaticengineer.com/",
        "https://www.hanselman.com/blog/",
        "https://www.joelonsoftware.com/",
        "https://blog.codinghorror.com/",
        "https://martinfowler.com/",
        "https://davidwalsh.name/",
        "https://www.swyx.io/",
        "https://www.joshwcomeau.com/",
        "https://css-tricks.com/",
        "https://alistapart.com/",
        "https://tympanus.net/codrops/",
        "https://web.dev/blog/",
        "https://netflixtechblog.com/",
        "https://medium.com/",
        "https://medium.com/free-code-camp",
    ],
    "data_dir": "data/crawled_pages/",
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
    "index_dir": "data/index/",
    "chunk_size": 500,  # Number of documents to process at once
    "min_token_length": 2,
    "max_token_length": 20,
    "stopwords_file": "data/stopwords.txt",
    "title_boost": 5.0,   # Increased boost factor for terms in title
    "meta_boost": 3.0,    # Increased boost factor for terms in meta description
}

# Web interface settings
WEB_CONFIG = {
    "host": "0.0.0.0",  # Listen on all interfaces
    "port": 5000,
    "debug": True,
    "results_per_page": 15,  # Increased number of results per page
} 