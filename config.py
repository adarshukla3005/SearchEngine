"""
Configuration settings for Google Search integration
"""

# Google search settings
GOOGLE_SEARCH_CONFIG = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "cache_dir": "data/google_cache/",
    "results_per_query": 30,  # Increased from 15
    "llm_validation": False,  # Disable LLM validation
    "confidence_threshold": 0.3,  # Minimum confidence threshold for blog/article validation with TF-IDF
    "skip_validation": False,  # Enable TF-IDF validation
    "request_timeout": 3,     # Reduced timeout for faster responses
    "max_workers": 10         # Increased from 5 for better parallelism
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