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

from search_engine.indexer.indexer import SearchIndexer
from utils.config import WEB_CONFIG, INDEXER_CONFIG

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

# Initialize Flask app with the correct template folder
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'templates')
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'static')
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# Initialize search indexer
try:
    indexer = SearchIndexer(INDEXER_CONFIG)
    indexer.load_index()
    logger.info(f"Index loaded with {len(indexer.document_map)} documents and {len(indexer.inverted_index)} terms.")
except Exception as e:
    logger.error(f"Error loading index: {e}")
    indexer = None

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
    search_source = "Local Index"
    
    # Get index results
    try:
        if indexer:
            index_results = indexer.search(query, top_k=results_per_page * 2)
            logger.info(f"Index search query: '{query}', found {len(index_results)} results")
            
            # Add source to results
            for result in index_results:
                result["source"] = "Local Index"
    except Exception as e:
        logger.error(f"Error with index search: {e}")
        index_results = []
    
    all_results = index_results
    
    # Total results
    total_results = len(all_results)
    
    # Log first few results
    for i, result in enumerate(all_results[:5]):  # Log first 5 results
        logger.info(f"Result {i+1}: {result.get('title', 'No title')} - {result.get('url', 'No URL')} ({result.get('source', 'Local Index')})")
    
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
    
    # Search the index
    try:
        if indexer:
            index_results = indexer.search(query, top_k=limit)
            
            # Add source
            for result in index_results:
                result["source"] = "Local Index"
                
            results.extend(index_results)
                
    except Exception as e:
        logger.error(f"Error with index search API: {e}")
    
    # Limit to requested number
    results = results[:limit]
    
    return jsonify({
        'results': results,
        'total': len(results)
    })

def main():
    """
    Main function to run the web interface
    """
    # Run the app
    app.run(
        host=WEB_CONFIG["host"],
        port=WEB_CONFIG["port"],
        debug=WEB_CONFIG["debug"]
    )

if __name__ == "__main__":
    main() 