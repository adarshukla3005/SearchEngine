# Personal Blog Search Engine

## Implementation Summary

We've implemented a focused search engine specifically for personal blogs and articles, using a crawler-based approach. Here's what we've implemented:

### 1. Web Crawler
- Created a robust `Crawler` class that efficiently crawls blogs from seed URLs
- Respects robots.txt constraints
- Implements rate limiting to avoid overloading sites
- Stores crawled content with metadata for further processing

### 2. Content Classifier
- Implemented a hierarchical classification system:
  - Domain-based classification (fastest)
  - Header/footer analysis (medium complexity)
  - Full content analysis (most thorough)
- Uses pattern matching and AI models to determine if content is a personal blog

### 3. Search Indexer
- Built an inverted index for efficient searching
- Implemented BM25 ranking algorithm with customized parameters
- Optimized for blogs and articles with title boosting
- Stores document metadata for result presentation

### 4. Web Application
- Created a clean Flask application to serve search results
- Implemented pagination for better user experience
- Added an API endpoint for programmatic access
- Styled with a responsive, modern UI

### 5. Text Processing
- Implemented custom tokenization and stopword removal
- Added query expansion for better search relevance
- Optimized for personal blog content

## How to Use

1. Run the crawler to collect blog data:
   ```
   python search_engine/crawler/run_crawler.py
   ```

2. Classify the crawled content:
   ```
   python search_engine/classifier/run_classifier.py
   ```

3. Build the search index:
   ```
   python search_engine/indexer/build_index.py
   ```

4. Start the web application:
   ```
   python app.py
   ```

## Configuration

The system is highly configurable through the `utils/config.py` file:
- Crawler settings (seed URLs, depth, rate limiting)
- Classification parameters
- Indexing options
- Web interface configuration 