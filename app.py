"""
Web interface for the Personal Blog Search Engine
"""
import os
import sys
import math
import logging
import traceback
from flask import Flask, render_template, request, jsonify, send_from_directory

# Add the current directory to the path to find modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from search_engine.indexer.optimized_indexer import OptimizedSearchIndexer
from utils.config import WEB_CONFIG, INDEXER_CONFIG, DEPLOYMENT_CONFIG

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("web.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("web")

# Set production flag based on environment variable
is_production = os.environ.get("PRODUCTION", "false").lower() == "true"
logger.info(f"Running in {'production' if is_production else 'development'} mode")

# Get absolute paths for templates and static files
app_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(app_dir, 'web', 'templates')
static_dir = os.path.join(app_dir, 'web', 'static')

logger.info(f"Template directory: {template_dir}")
logger.info(f"Static directory: {static_dir}")

# Initialize Flask app with the correct template folder
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir, static_url_path='/static')

# Initialize optimized search indexer with modified config for deployment
optimized_config = INDEXER_CONFIG.copy()
# Always use optimized index in production environment
if is_production:
    optimized_config["index_dir"] = DEPLOYMENT_CONFIG["optimized_index_dir"]
    logger.info(f"Using optimized index from {DEPLOYMENT_CONFIG['optimized_index_dir']}")
else:
    logger.info(f"Using development index from {optimized_config['index_dir']}")

# Log directory structure without listing all files
try:
    logger.info("Checking directory structure:")
    for root, dirs, files in os.walk("data"):
        logger.info(f"Directory: {root} - {len(files)} files")
except Exception as e:
    logger.error(f"Error checking directories: {e}")

# Add explicit static file route to ensure they're served properly
@app.route('/static/<path:filename>')
def serve_static(filename):
    logger.info(f"Serving static file: {filename}")
    return send_from_directory(static_dir, filename)

# Initialize indexer
indexer = OptimizedSearchIndexer(optimized_config)

# Flag to enable hybrid search (BM25 + BERT)
USE_HYBRID_SEARCH = os.environ.get("USE_HYBRID_SEARCH", "true").lower() == "true"

# Load the index at startup
try:
    logger.info("Starting to load optimized index...")
    indexer.load_optimized_index(use_hybrid_search=USE_HYBRID_SEARCH)
    logger.info(f"Index loaded with {len(indexer.document_map)} documents and {len(indexer.inverted_index)} terms.")
    logger.info(f"Search mode: {'Hybrid BM25+BERT' if USE_HYBRID_SEARCH else 'BM25 only'}")
except Exception as e:
    error_msg = f"Error loading index: {e}"
    logger.error(error_msg)
    logger.error(traceback.format_exc())  # Log the full traceback
    logger.error("Make sure to run the indexer and prepare_for_deployment.py first!")
    # Don't exit in production as this would prevent the app from starting
    if not is_production:
        sys.exit(1)

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
        logger.info(f"Index search query: '{query}', found {len(index_results)} results using {search_source}")
        
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
    
    # Log first few results
    for i, result in enumerate(all_results[:5]):  # Log first 5 results
        logger.info(f"Result {i+1}: {result.get('title', 'No title')} - {result.get('url', 'No URL')} ({result.get('search_method', search_source)})")
    
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
    
    results = []
    search_source = "Hybrid BM25+BERT" if USE_HYBRID_SEARCH else "BM25"
    
    # Domains to exclude (e.g., Spotify blogs)
    excluded_domains = {"open.spotify.com", "spotify.com", "podcasts.apple.com", "podcasts.google.com"}
    
    # Search the index
    try:
        logger.info(f"API search request for query: '{query}'")
        index_results = indexer.search(query, top_k=limit * 2)  # Get more results for filtering
        logger.info(f"API search found {len(index_results)} results")
        
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
        # Check if indexer is loaded
        doc_count = len(indexer.document_map)
        term_count = len(indexer.inverted_index)
        return jsonify({
            'status': 'healthy',
            'document_count': doc_count,
            'term_count': term_count,
            'mode': 'production' if is_production else 'development',
            'search_mode': 'hybrid' if USE_HYBRID_SEARCH else 'bm25'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

if __name__ == "__main__":
    # Get port from environment variable with a default of 3000 (common for web services)
    port = int(os.environ.get("PORT", 3000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    ) 