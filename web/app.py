"""
Web interface for Google Search integration
"""
import os
import sys
import math
import logging
from flask import Flask, render_template, request, jsonify

# Add parent directory to path to import from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import from config
from config import GOOGLE_SEARCH_CONFIG, GOOGLE_WEB_CONFIG

# Import the TF-IDF search integration
from scripts.fast_tfidf_search import FastTFIDFSearchIntegration

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("google_search.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("google_search_web")

# Initialize Flask app
app = Flask(__name__, 
           template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates')),
           static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'static')))

# Initialize Google search integration with the TF-IDF version
google_search = FastTFIDFSearchIntegration(GOOGLE_SEARCH_CONFIG)

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
    results_per_page = GOOGLE_WEB_CONFIG["results_per_page"]
    start_idx = (page - 1) * results_per_page
    
    # Search using Google with the TF-IDF integration
    try:
        # Request more results than needed for better quality
        results_to_fetch = min(results_per_page * 3, GOOGLE_SEARCH_CONFIG["results_per_query"])
        google_results = google_search.search_google(query, num_results=results_to_fetch)
        logger.info(f"Google search query: '{query}', found {len(google_results)} results")
        
        # Count sources
        google_count = sum(1 for r in google_results if r.get("source") == "Google Search")
        discovered_count = sum(1 for r in google_results if r.get("source") == "Discovered Blog")
        
        # Source is already added in FastTFIDFSearchIntegration
        all_results = google_results
        
        # Set search source description
        if google_count > 0 and discovered_count > 0:
            search_source = f"Google Search ({google_count}) + Discovered Blogs ({discovered_count})"
        elif google_count > 0:
            search_source = "Google Search"
        elif discovered_count > 0:
            search_source = "Discovered Blogs"
        else:
            search_source = "No Results"
        
    except Exception as e:
        logger.error(f"Error with Google search: {e}")
        all_results = []
        search_source = "Error: No Results"
    
    # Total results
    total_results = len(all_results)
    
    # Log first few results
    for i, result in enumerate(all_results[:5]):  # Log first 5 results
        logger.info(f"Result {i+1}: {result.get('title', 'No title')} - {result.get('url', 'No URL')} - {result.get('source', 'Unknown')}")
    
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
    limit = int(request.args.get('limit', GOOGLE_WEB_CONFIG["results_per_page"]))
    
    if not query:
        return jsonify({'results': [], 'total': 0})
    
    # Search using Google with the TF-IDF integration
    try:
        results = google_search.search_google(query, num_results=limit)
        
        # Count sources
        google_count = sum(1 for r in results if r.get("source") == "Google Search")
        discovered_count = sum(1 for r in results if r.get("source") == "Discovered Blog")
        
        if google_count > 0 and discovered_count > 0:
            source = f"Google Search ({google_count}) + Discovered Blogs ({discovered_count})"
        elif google_count > 0:
            source = "Google Search"
        elif discovered_count > 0:
            source = "Discovered Blogs"
        else:
            source = "No Results"
    except Exception as e:
        logger.error(f"Error with Google search API: {e}")
        results = []
        source = "Error"
    
    return jsonify({
        'results': results,
        'total': len(results),
        'source': source
    })

def main():
    """
    Main function to run the web interface
    """
    # Create necessary directories
    os.makedirs("data/google_cache", exist_ok=True)
    
    # Start the web server
    app.run(
        host=GOOGLE_WEB_CONFIG.get("host", "0.0.0.0"),
        port=GOOGLE_WEB_CONFIG.get("port", 5000),
        debug=GOOGLE_WEB_CONFIG.get("debug", True)
    )

if __name__ == "__main__":
    main() 