"""
Wrapper script to run the Google search web app directly
"""
import os
import sys
import argparse
import logging

# Add the current directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the main function from the web directory
from web.app import main

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Run the search engine')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on (default: 5000)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to run the server on (default: 0.0.0.0)')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("google_search.log"),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger("search_engine")
    
    logger.info(f"Starting search engine on {args.host}:{args.port}")
    
    # Run the web server with custom settings
    main(host=args.host, port=args.port, debug=args.debug) 