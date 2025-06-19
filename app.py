"""
Wrapper script to run the Google search web app directly
"""
import os
import sys

# Add the current directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the main function from the web directory
from web.app import main

if __name__ == "__main__":
    main() 