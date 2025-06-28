# Custom Search Engine

A specialized search engine focused on high-quality blog content with advanced relevance ranking.

## Features

- Focused web crawler that targets specific blogs and websites
- Content classification to identify relevant pages
- Advanced indexing with BM25-based ranking
- Optimized search with main term identification and proximity boosting
- Hybrid BM25+BERT search for improved semantic understanding
- Web interface for easy searching

## Hybrid Search Architecture

This search engine implements a hybrid approach combining the strengths of both BM25 and BERT:

1. **BM25 (Lexical Matching)**
   - Provides fast, token-based matching
   - Handles term frequency and document length normalization
   - Excellent for exact keyword matching
   - Computationally efficient

2. **BERT (Semantic Understanding)**
   - Captures semantic meaning and context
   - Understands synonyms and related concepts
   - Trained on vast text corpora
   - Uses all-MiniLM-L6-v2 model for speed and efficiency

3. **Hybrid Scoring**
   - Combines BM25 and BERT scores with configurable weights (default: 70% BM25, 30% BERT)
   - Normalizes both scores for fair comparison
   - Provides better results than either method alone

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

Access the web interface at http://localhost:3000 and enter your search query.

## Environment Variables

- `USE_HYBRID_SEARCH`: Set to "true" (default) to enable hybrid search, or "false" to use BM25 only
- `PORT`: Port for the web server (default: 3000)
- `PRODUCTION`: Set to "true" for production mode (default: "false")

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

3. Run with local crawling and indexing
   ```
   # Run the crawler to collect data
   python crawler/run_crawler.py
   
   # Build the search index
   python indexer/build_index.py
   
   # Start the web interface
   python web/app.py
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