# Custom Search Engine

A specialized search engine focused on high-quality blog content with advanced relevance ranking.

- **Demo Video:** [Video Link](https://drive.google.com/file/d/1ggm0SKx9Gy-jUG2TuZY0Jvg1joPGm-a7/view?usp=sharing)

## Workflow of the Project

![image](https://github.com/user-attachments/assets/a31fd8d7-2ac3-41c8-8133-f425ef381de7)


## Core Components

### Crawler
- **Purpose**: Collects blog content from specified websites
- **Features**:
  - Focused crawling based on seed URLs (currently configured for 3 primary sources)
  - Smart URL filtering to target article and blog content
  - Respects robots.txt and implements rate limiting
  - Skips previously crawled pages to avoid duplication
  - Currently configured to crawl up to **1000 pages**
  - Stores raw HTML and extracted text content
  - Tracks domain statistics and crawl progress

### Classifier
- **Purpose**: Identifies relevant high-quality blog content
- **Features**:
  - Uses the Gemma-2b model for content classification
  - Evaluates pages based on content quality, formatting, and topic relevance
  - Applies configurable threshold settings for classification
  - Separates personal blog content from commercial/marketing content

### Indexer
- **Purpose**: Creates optimized search indexes for fast retrieval
- **Features**:
  - Implements BM25 algorithm for relevance ranking
  - Handles stemming and stopword removal
  - Creates inverted index structure for efficient searching
  - Computes document statistics like term frequency and document length
  - Supports field boosting for title and meta description
  - Optimized index format for reduced memory usage and faster searching

### Semantic Search
- **Purpose**: Enhances search with semantic understanding
- **Features**:
  - Uses sentence-transformers/all-MiniLM-L6-v2 BERT model
  - Generates document embeddings for vector search
  - Combines with BM25 for hybrid search capabilities
  - Configurable weighting between lexical and semantic search (70/30 by default)

### Web Interface
- Simple, responsive interface with light/dark mode
- Search results include title, description, and content snippets
- Relevance indicators and pagination support

## Statistics

- **Pages Crawled**: Up to 1000 pages from configured seed URLs
- **Index Size**: Optimized for efficient storage and lookup
- **Response Time**: Fast search results with hybrid ranking

## Query Processing and Ranking

The search engine uses an advanced query processing pipeline:

1. **Main Term Identification**: Automatically identifies the most important terms in a query based on:
   - Word length (longer words typically carry more meaning)
   - Position in query (first and last words often have special importance)
   - Stopword filtering (removes common words like "the", "and", etc.)

2. **Query Expansion**: Enhances the original query with related terms including:
   - Stemmed variations of query terms
   - Original phrases preserved for exact matching

3. **BM25 Ranking**: Uses a modified BM25 algorithm with:
   - Main term boosting (2.5x weight for identified main terms)
   - Title and description field boosting
   - Exact phrase matching detection
   - Term proximity scoring (rewards documents where query terms appear close together)

4. **BERT Semantic Search**:
   - Encodes query into dense vector representation
   - Uses FAISS for fast similarity search against document embeddings
   - Finds semantically similar documents even with different terminology

5. **Relevance Boosting**:
   - Up to 250% boost for main terms appearing in document titles
   - Up to 150% boost for main terms in descriptions
   - 50% boost for documents where main terms appear in close proximity
   - Graduated scoring based on percentage of query terms matched

## Installation and Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the crawler: `python -m search_engine.crawler.run_crawler`
4. Run the classifier: `python -m search_engine.classifier.run_classifier`
5. Build the index: `python -m search_engine.indexer.build_index`
6. Optimize the index: `python -m search_engine.indexer.optimize_index`
7. Generate BERT embeddings: `python -m search_engine.indexer.generate_bert_embeddings`
8. Start the web interface: `python app.py`

## Usage

Access the web interface at http://localhost:5000 and enter your search query. Switch between light and dark modes using the theme toggle in the upper right corner.

## Environment Variables

- `USE_HYBRID_SEARCH`: Set to "true" (default) to enable hybrid search, or "false" to use BM25 only
- `PORT`: Port for the web server (default: 5000)
- `PRODUCTION`: Set to "true" for production mode (default: "false")

## Project Structure

- `crawler/`: Web crawling components
  - `crawler.py`: Core crawler implementation
  - `run_crawler.py`: Script to initiate crawling
  - `query_crawler.py`: Alternative crawler for query-based crawling
- `classifier/`: Content classification components
  - `classifier.py`: Implementation of the classification system
  - `run_classifier.py`: Script to run classification on crawled content
- `indexer/`: Search indexing and retrieval components
  - `indexer.py`: Core indexing functionality
  - `optimized_indexer.py`: Optimized version for faster search
  - `build_index.py`: Script to build the initial index
  - `optimize_index.py`: Script to create the optimized index format
  - `bert_embeddings.py`: Functionality for semantic embeddings
  - `generate_bert_embeddings.py`: Script to create and store embeddings
- `web/`: Flask web interface with templates and static assets
- `utils/`: Utility functions for text processing
  - `config.py`: Configuration settings for all components
  - `text_processing.py`: Text processing utilities
- `logs/`: Storage location for log files from all components
- `data/`: Data storage directories
  - `crawled_pages/`: Raw crawled content from websites
  - `classified_pages/`: Content after classification
  - `index/`: Initial search index
  - `optimized_index/`: Final optimized search index format
  - `embeddings/`: BERT embeddings for semantic search

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run with local crawling and indexing
   ```
   # Run the crawler to collect data (up to 1000 pages)
   python search_engine/crawler/run_crawler.py
   
   # Run the classifier to identify personal blogs
   python search_engine/classifier/run_classifier.py
   
   # Build the search index
   python search_engine/indexer/build_index.py
   
   # Optimize the index for faster searching
   python search_engine/indexer/optimize_index.py
   
   # Generate BERT embeddings for semantic search
   python search_engine/indexer/generate_bert_embeddings.py
   
   # Start the web interface
   python app.py
   ```

3. Access the search engine at http://localhost:5000

## Deployment on Render

### Preparing for Deployment

1. Run the prepare_for_deployment.py script to create an optimized index:
   ```
   python web/utils/prepare_for_deployment.py
   ```

2. Verify deployment readiness:
   ```
   python web/utils/check_deployment.py
   ```

3. Make sure the following files are included in your repository:
   - All application code
   - `requirements.txt`
   - `runtime.txt` (specifies Python version)
   - `web/utils/gunicorn.conf.py` (web server configuration)
   - The optimized index files in `data/optimized_index/`

### Deploying to Render

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Configure the service:
   - **Name**: Your choice (e.g., custom-search-engine)
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Environment Variables**:
     - `PRODUCTION`: true
     - `USE_HYBRID_SEARCH`: true (or false if you prefer BM25-only for better performance)

4. Click "Create Web Service"

## Configuration

Edit `utils/config.py` to customize crawler behavior, classification thresholds, and other options. The current configuration is set to:

- Crawl up to 1000 pages
- Maximum depth of 5 from seed URLs
- Rate limiting of 0.2 seconds between requests
- Three primary seed URLs (with more available but commented out)
- Skip previously crawled pages to avoid duplication
