"""
Configuration settings for Google Search integration
"""

# Seed URLs for blog discovery
SEED_URLS = [
    "https://waitbutwhy.com/",
    "https://manassaloi.com/",
    "https://www.kalzumeus.com/",
    "https://www.scotthyoung.com/blog/",
    "https://www.ribbonfarm.com/",
    "https://slatestarcodex.com/",
    "https://www.mrmoneymustache.com/",
    "https://paulgraham.com/articles.html",
    "https://fs.blog/",
    "https://blog.samaltman.com/",
    "https://stratechery.com/",
    "https://www.collaborativefund.com/blog/",
    "https://nav.al/",
    "https://jamesclear.com/articles",
    "https://tim.blog/",
    "https://www.raptitude.com/",
    "https://www.lesswrong.com/",
    "https://www.markmanson.net/",
    "https://seths.blog/",
    "https://www.joshwcomeau.com/",
    "https://danluu.com/",
    "https://www.swyx.io/",
    "https://www.julian.com/blog",
    "https://www.perell.com/blog",
    "https://www.eugenewei.com/",
    "https://www.benkuhn.net/",
    "https://www.tomcritchlow.com/",
    "https://www.hanselman.com/blog/",
    "https://www.joelonsoftware.com/",
    "https://blog.codinghorror.com/",
    "https://www.brainpickings.org/",
    "https://hyperboleandahalf.blogspot.com/",
    "http://1000awesomethings.com/",
    "https://kottke.org/",
    "https://nealpasricha.com/",
    "https://gen.medium.com/"
]

# Google search settings
GOOGLE_SEARCH_CONFIG = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "cache_dir": "data/google_cache/",
    "results_per_query": 30,  # Increased from 15
    "llm_validation": False,  # Disable LLM validation
    "confidence_threshold": 0.3,  # Lowered from 0.4 to include more results
    "skip_validation": False,  # Enable TF-IDF validation
    "request_timeout": 10,    # Increased from 5 to allow more time for fetching metadata
    "max_workers": 15,        # Number of parallel workers for fetching metadata
    "seed_urls": SEED_URLS    # Add seed URLs to config
}

# Web interface settings for Google search
GOOGLE_WEB_CONFIG = {
    "host": "0.0.0.0",  # Listen on all interfaces
    "port": 5000,
    "debug": True,
    "results_per_page": 25,  # Increased from 15
    "use_google_search": True,  # Whether to use Google search
    "fallback_to_index": True,  # Whether to fall back to index if Google search fails
    "combine_results": True,   # Changed to True to combine Google search and index results
} 