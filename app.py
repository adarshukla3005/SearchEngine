"""
Web interface for the Personal Blog Search Engine
"""
import os
import sys
import math
import logging
import traceback
import gc
from flask import Flask, render_template, request, jsonify, send_from_directory

# Add the current directory to the path to find modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from search_engine.indexer.optimized_indexer import OptimizedSearchIndexer
from utils.config import WEB_CONFIG, INDEXER_CONFIG

# Set up logging with reduced verbosity
logging.basicConfig(
    level=logging.WARNING,  # Changed from INFO to WARNING
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("web.log"),
        logging.StreamHandler()
    ]
)

# Set specific loggers to different levels
logging.getLogger("web").setLevel(logging.INFO)
logging.getLogger("werkzeug").setLevel(logging.WARNING)
logging.getLogger("faiss").setLevel(logging.ERROR)

logger = logging.getLogger("web")

# Get absolute paths for templates and static files
app_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(app_dir, 'web', 'templates')
static_dir = os.path.join(app_dir, 'web', 'static')

logger.info(f"Template directory: {template_dir}")
logger.info(f"Static directory: {static_dir}")

# Initialize Flask app with the correct template folder
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir, static_url_path='/static')

# Initialize optimized search indexer with optimized index path
optimized_config = INDEXER_CONFIG.copy()
optimized_config["index_dir"] = "data/optimized_index/"
logger.info(f"Using optimized index from {optimized_config['index_dir']}")

# Check directory structure but don't log all files
try:
    directory_count = 0
    file_count = 0
    for root, dirs, files in os.walk("data"):
        directory_count += 1
        file_count += len(files)
    logger.info(f"Data directory contains {directory_count} directories and {file_count} files")
except Exception as e:
    logger.error(f"Error checking directories: {e}")

# Add explicit static file route to ensure they're served properly
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(static_dir, filename)

# Serve favicon
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(static_dir, 'img'), 'favicon.ico')

# Initialize indexer but don't load data yet
indexer = OptimizedSearchIndexer(optimized_config)

# Set search mode from environment variable (default: hybrid)
SEARCH_MODE = os.environ.get("SEARCH_MODE", "hybrid").lower()
USE_HYBRID_SEARCH = SEARCH_MODE == "hybrid"

logger.info(f"Search mode set to: {SEARCH_MODE} (Hybrid: {USE_HYBRID_SEARCH})")

# Flag to track if index is loaded
index_loaded = False

def load_index():
    """Load the index lazily when needed"""
    global index_loaded
    if index_loaded:
        return True
    
    try:
        logger.info("Starting to load optimized index...")
        # Force garbage collection before loading index
        gc.collect()
        indexer.load_optimized_index(use_hybrid_search=USE_HYBRID_SEARCH)
        logger.info(f"Index loaded with {len(indexer.document_map)} documents and {len(indexer.inverted_index)} terms.")
        index_loaded = True
        return True
    except Exception as e:
        error_msg = f"Error loading index: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())  # Log the full traceback
        return False

@app.route('/')
def home():
    """
    Home page
    """
    return render_template('index.html')

@app.route('/search')
def search():
    """
    Search endpoint
    """
    # Get query parameters
    query = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    
    if not query:
        return render_template('index.html')
    
    # Load index if not already loaded
    if not load_index():
        return render_template('index.html', error="Search engine is still initializing. Please try again in a moment.")
    
    # Calculate pagination
    results_per_page = WEB_CONFIG["results_per_page"]
    start_idx = (page - 1) * results_per_page
    
    index_results = []
    all_results = []
    search_source = "Hybrid BM25+BERT" if USE_HYBRID_SEARCH else "BM25"
    
    # Domains to exclude (e.g., Spotify blogs)
    excluded_domains = {"open.spotify.com", "spotify.com", "podcasts.apple.com", "podcasts.google.com"}
    
    # Get index results
    try:
        index_results = indexer.search(query, top_k=results_per_page * 3)  # Get more results for filtering
        logger.info(f"Search query: '{query}', found {len(index_results)} results using {search_source}")
        
        # Add source to results and filter out excluded domains
        filtered_results = []
        for result in index_results:
            # Skip results from excluded domains
            url = result.get("url", "").lower()
            if any(domain in url for domain in excluded_domains):
                continue
                
            result["source"] = search_source
            filtered_results.append(result)
            
        index_results = filtered_results
            
    except Exception as e:
        logger.error(f"Error with index search: {e}")
        logger.error(traceback.format_exc())  # Log the full traceback
        index_results = []
    
    all_results = index_results
    
    # Total results
    total_results = len(all_results)
    
    # Log only first result for brevity
    if all_results and logger.isEnabledFor(logging.INFO):
        first_result = all_results[0]
        logger.info(f"Top result: {first_result.get('title', 'No title')} - {first_result.get('url', 'No URL')}")
    
    # Paginate results
    paginated_results = all_results[start_idx:start_idx + results_per_page]
    
    # Calculate total pages
    total_pages = math.ceil(total_results / results_per_page) if total_results > 0 else 0
    
    # Generate pagination links
    pagination = {
        'current_page': page,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if page < total_pages else None,
    }
    
    return render_template(
        'search_results.html',
        query=query,
        results=paginated_results,
        total_results=total_results,
        pagination=pagination,
        search_source=search_source
    )

# Ensure API endpoints work properly
@app.route('/api/search', methods=['GET'])
def api_search():
    """
    API endpoint for search
    """
    # Get query parameters
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', WEB_CONFIG["results_per_page"]))
    
    if not query:
        return jsonify({'results': [], 'total': 0})
    
    # Load index if not already loaded
    if not load_index():
        return jsonify({'error': 'Search engine is still initializing'}), 503
    
    results = []
    search_source = "Hybrid BM25+BERT" if USE_HYBRID_SEARCH else "BM25"
    
    # Domains to exclude (e.g., Spotify blogs)
    excluded_domains = {"open.spotify.com", "spotify.com", "podcasts.apple.com", "podcasts.google.com"}
    
    # Search the index
    try:
        logger.info(f"API search: '{query}'")
        index_results = indexer.search(query, top_k=limit * 2)  # Get more results for filtering
        
        # Filter out excluded domains and add source
        for result in index_results:
            # Skip results from excluded domains
            url = result.get("url", "").lower()
            if any(domain in url for domain in excluded_domains):
                continue
                
            result["source"] = search_source
            results.append(result)
            
    except Exception as e:
        logger.error(f"Error with index search API: {e}")
        logger.error(traceback.format_exc())  # Log the full traceback
    
    # Limit to requested number
    results = results[:limit]
    
    return jsonify({
        'results': results,
        'total': len(results)
    })

# Add a health check endpoint
@app.route('/health')
@app.route('/api/health')
def health_check():
    """
    Health check endpoint for monitoring
    """
    try:
        # Check if index is loaded
        if index_loaded:
            doc_count = len(indexer.document_map)
            term_count = len(indexer.inverted_index)
            return jsonify({
                'status': 'healthy',
                'index_loaded': True,
                'document_count': doc_count,
                'term_count': term_count,
                'search_mode': SEARCH_MODE
            })
        else:
            return jsonify({
                'status': 'initializing',
                'index_loaded': False
            })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

if __name__ == "__main__":
    print("\n" + "="*50)
    print("Personal Blog Search Engine")
    print("="*50)
    print(f"Search mode: {SEARCH_MODE.upper()}")
    print(f"Server running at: http://localhost:{WEB_CONFIG['port']}")
    print("Press Ctrl+C to stop the server")
    print("="*50 + "\n")
    
    # Run the Flask app
    app.run(
        host=WEB_CONFIG["host"],
        port=WEB_CONFIG["port"],
        debug=WEB_CONFIG["debug"]
    ) 