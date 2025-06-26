import os
import sys
import json
import math
import re
from jinja2 import Environment, FileSystemLoader

# Add the root directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from utils.config import WEB_CONFIG

# Set up Jinja2 environment
template_dir = os.path.join(os.path.dirname(__file__), "../../web")
env = Environment(loader=FileSystemLoader(template_dir))

# Custom filter to mimic url_for
def url_for(endpoint, **kwargs):
    if endpoint == 'static':
        return f"/static/{kwargs.get('filename', '')}"
    return "/"

# Add the filter to the Jinja environment
env.filters['url_for'] = url_for

def handler(event, context):
    """
    Netlify function handler
    """
    # Get the path
    path = event.get("path", "").lstrip("/")
    
    # Get query parameters
    params = event.get("queryStringParameters", {}) or {}
    
    # Handle different routes
    if path == "" or path == "index.html":
        # Home page
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "text/html"
            },
            "body": render_template("index.html")
        }
    elif path == "search":
        # Search page
        query = params.get("q", "")
        page = int(params.get("page", 1))
        
        # Get demo results
        results = get_demo_results(query)
        
        # Calculate pagination
        results_per_page = WEB_CONFIG["results_per_page"]
        total_results = len(results)
        
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
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "text/html"
            },
            "body": render_template("search_results.html", {
                "query": query,
                "results": results,
                "total_results": total_results,
                "pagination": pagination,
                "search_source": "Demo"
            })
        }
    elif path == "api/search":
        # API search endpoint
        query = params.get("q", "")
        limit = int(params.get("limit", WEB_CONFIG["results_per_page"]))
        
        results = get_demo_results(query)
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                'results': results[:limit],
                'total': len(results)
            })
        }
    elif path.startswith("static/"):
        # Serve static files
        file_path = os.path.join(os.path.dirname(__file__), "../../web", path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            with open(file_path, 'rb') as f:
                content = f.read()
            
            content_type = "text/plain"
            if path.endswith(".css"):
                content_type = "text/css"
            elif path.endswith(".js"):
                content_type = "application/javascript"
            elif path.endswith(".png"):
                content_type = "image/png"
            elif path.endswith(".jpg") or path.endswith(".jpeg"):
                content_type = "image/jpeg"
            
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": content_type
                },
                "body": content.decode('utf-8') if content_type.startswith("text") else content.decode('latin1')
            }
        else:
            return {
                "statusCode": 404,
                "body": "File not found"
            }
    else:
        # Not found
        return {
            "statusCode": 404,
            "body": "Not Found"
        }

def render_template(template_name, context=None):
    """
    Render a template with the given context
    """
    if context is None:
        context = {}
    
    template = env.get_template(template_name)
    
    # Render the template
    html = template.render(**context)
    
    # Replace Flask's url_for with our static path
    html = re.sub(r'{{ url_for\(\'static\', filename=\'(.*?)\'\) }}', r'/static/\1', html)
    
    return html

def get_demo_results(query):
    """
    Get demo search results
    """
    if not query:
        return []
    
    # Return demo results
    return [
        {
            "title": "Demo Result: Netlify Serverless Function",
            "url": "https://example.com/demo",
            "snippet": "This is a demo result from the Netlify serverless function. In a real implementation, you would need to store your index in a database or other persistent storage that can be accessed from the serverless function.",
            "source": "Demo"
        },
        {
            "title": f"Search Result for '{query}'",
            "url": f"https://example.com/search?q={query}",
            "snippet": f"This is a sample search result for the query '{query}'. In a production environment, this would be replaced with actual search results from your index.",
            "source": "Demo"
        }
    ] 