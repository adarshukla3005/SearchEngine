# Personal Blog Search Engine

A custom search engine for personal blogs and tech content.

## Features

- Web crawler for collecting blog content
- Content classification
- Full-text search indexing
- Web interface for searching

## Project Structure

- `search_engine/`: Core search engine components
  - `crawler/`: Web crawler implementation
  - `classifier/`: Content classifier
  - `indexer/`: Search indexer
- `utils/`: Utility functions and configuration
- `web/`: Web interface templates and static files
- `app.py`: Main application entry point
- `data/`: Data storage directories
  - `crawled_pages/`: Storage for crawled pages
  - `classified_pages/`: Storage for classified content
  - `index/`: Search index files

## Setup and Installation

1. Clone the repository:
```
git clone https://github.com/adarshukla3005/SearchEngine.git
cd SearchEngine
```

2. Create and activate a virtual environment:
```
python -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate
```

3. Install dependencies:
```
pip install -r requirements.txt
```

4. Run the crawler to collect data:
```
python -m search_engine.crawler.crawler
```

5. Run the classifier to categorize content:
```
python -m search_engine.classifier.classifier
```

6. Build the search index:
```
python -m search_engine.indexer.indexer
```

7. Start the web interface:
```
python app.py
```

8. Open your browser and go to `http://localhost:5000`

## Configuration

Configuration settings are in `utils/config.py`:

- `CRAWLER_CONFIG`: Settings for the web crawler
- `CLASSIFIER_CONFIG`: Settings for the content classifier
- `INDEXER_CONFIG`: Settings for the search indexer
- `WEB_CONFIG`: Settings for the web interface

## Deployment on Vercel

This project is configured for deployment on Vercel:

1. Fork or clone this repository
2. Sign up for a [Vercel account](https://vercel.com/signup)
3. Install Vercel CLI:
```
npm install -g vercel
```
4. Login to Vercel:
```
vercel login
```
5. Deploy the project:
```
vercel
```

### Important Notes for Vercel Deployment

- The search functionality requires pre-built index files
- You may need to adjust the configuration in `utils/config.py` for production use
- Large data files should be stored separately and not included in the deployment

## License

MIT 