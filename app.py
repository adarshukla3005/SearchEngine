"""
Web interface for the Personal Blog Search Engine
"""
import os
import sys
import math
import logging
from flask import Flask, render_template, request, jsonify

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

# Initialize Flask app with the correct template folder
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'templates')
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'static')
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# Initialize optimized search indexer with modified config for deployment
optimized_config = INDEXER_CONFIG.copy()
# Always use optimized index in production environment
if is_production:
    optimized_config["index_dir"] = DEPLOYMENT_CONFIG["optimized_index_dir"]
    logger.info(f"Using optimized index from {DEPLOYMENT_CONFIG['optimized_index_dir']}")
else:
    logger.info(f"Using development index from {optimized_config['index_dir']}")

indexer = OptimizedSearchIndexer(optimized_config)

# Flag to enable hybrid search (BM25 + BERT)
USE_HYBRID_SEARCH = os.environ.get("USE_HYBRID_SEARCH", "true").lower() == "true"

# Load the index at startup
try:
    indexer.load_optimized_index(use_hybrid_search=USE_HYBRID_SEARCH)
    logger.info(f"Index loaded with {len(indexer.document_map)} documents and {len(indexer.inverted_index)} terms.")
    logger.info(f"Search mode: {'Hybrid BM25+BERT' if USE_HYBRID_SEARCH else 'BM25 only'}")
except Exception as e:
    logger.error(f"Error loading index: {e}")
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

@app.route('/api/search')
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
    
    # Limit to requested number
    results = results[:limit]
    
    return jsonify({
        'results': results,
        'total': len(results)
    })

if __name__ == "__main__":
    # Get port from environment variable with a default of 3000 (common for web services)
    port = int(os.environ.get("PORT", 3000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    ) 