# Personal Blog Search Engine

A custom search engine that prioritizes authentic personal blogs and articles over SEO-optimized corporate content, with the option to use Google search with Gemini AI validation.

## Features

- Web crawler to collect content from across the internet
- Content classifier using Gemma-3 1B to identify authentic personal blogs
- Search indexing system for efficient retrieval
- Google search integration with Gemini AI for query enhancement and result validation
- Web interface for searching content

## Project Structure

- `crawler/`: Web crawling components
- `classifier/`: Content classification using Gemma-3 1B
- `indexer/`: Search indexing and retrieval
- `web/`: Flask web interface
- `utils/`: Utility functions for text processing
- `google_search/`: Google search integration components with Gemini AI validation

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. For Google search with Gemini AI:
   - Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Create a `.env` file with your API key:
     ```
     GEMINI_API_KEY=your_gemini_api_key_here
     ```

3. Choose one of the following options:

   ### Option 1: Run with local crawling and indexing
   ```
   # Run the crawler to collect data
   python crawler/run_crawler.py
   
   # Build the search index
   python indexer/build_index.py
   
   # Start the web interface
   python web/app.py
   ```

   ### Option 2: Run with Google search integration
   ```
   # Start the web interface with Google search
   python run_google_search.py
   
   # To skip local index fallback
   python run_google_search.py --skip-index
   
   # To combine Google search with local index results
   python run_google_search.py --combine-results
   
   # To use Gemini validation (slower but more accurate)
   python run_google_search.py --use-validation
   ```

4. Access the search engine at http://localhost:5000

## Configuration

Edit `config.py` to customize crawler behavior, classification thresholds, Google search settings, and other options.

## How It Works

### Local Search Mode
1. Crawls the web starting from seed URLs
2. Classifies content to identify personal blogs
3. Indexes the content for efficient retrieval
4. Provides search functionality through a web interface

### Google Search Mode
1. Takes user query and enhances it using Gemini AI
2. Searches Google for relevant blogs and articles
3. Validates results using Gemini AI to ensure they're blogs/articles
4. Displays results with relevance scores and explanations

## Google Search Components

The `google_search/` directory contains the following components:

- `fast_google_search.py`: Optimized version of Google search that prioritizes speed
- `google_search.py`: Full-featured Google search with Gemini validation
- `run_google_search.py`: CLI tool to run the search engine with Google integration 