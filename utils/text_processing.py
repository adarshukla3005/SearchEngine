"""
Text processing utilities for the search engine
"""
import re
import string
from typing import List, Set

# Try to use NLTK for better tokenization, but fall back to basic tokenization if not available
try:
    import nltk
    from nltk.stem import PorterStemmer
    from nltk.tokenize import word_tokenize
    
    # Download NLTK resources if needed
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
    
    # Initialize stemmer
    stemmer = PorterStemmer()
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

def load_stopwords(filepath: str) -> Set[str]:
    """
    Load stopwords from a file
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        # Default English stopwords if file not found
        return {"a", "an", "the", "and", "or", "but", "if", "because", "as", "what",
                "when", "where", "how", "who", "which", "this", "that", "these", "those",
                "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
                "do", "does", "did", "for", "of", "on", "in", "to", "from", "with"}

def tokenize(text: str) -> List[str]:
    """
    Tokenize text into words with improved processing
    """
    if not text:
        return []
        
    # Convert to lowercase
    text = text.lower()
    
    # Replace HTML entities
    text = re.sub(r'&\w+;', ' ', text)
    
    # Remove URLs
    text = re.sub(r'https?://\S+', ' ', text)
    
    # Remove punctuation but preserve some meaningful separators with spaces
    text = re.sub(r'[^\w\s-]', ' ', text)
    
    # Replace hyphens with spaces to handle hyphenated words
    text = text.replace('-', ' ')
    
    # Use NLTK for better tokenization if available
    if NLTK_AVAILABLE:
        try:
            # Use NLTK tokenization
            tokens = word_tokenize(text)
            
            # Apply stemming to improve matching
            tokens = [stemmer.stem(token) for token in tokens]
            
            # Remove very short tokens (likely not meaningful)
            tokens = [token for token in tokens if len(token) > 1]
            
            return tokens
        except Exception:
            # Fall back to basic tokenization if NLTK fails
            pass
    
    # Basic tokenization as fallback
    tokens = text.split()
    return [token for token in tokens if len(token) > 1]

def clean_text(text: str) -> str:
    """
    Clean text by removing HTML tags, extra whitespace, etc.
    """
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_domain(url: str) -> str:
    """
    Extract domain from URL
    """
    # Simple domain extraction
    match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    if match:
        return match.group(1)
    return ""

def extract_title_from_html(html_content: str) -> str:
    """
    Extract title from HTML content
    """
    match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
    if match:
        return clean_text(match.group(1))
    return ""

def extract_meta_description(html_content: str) -> str:
    """
    Extract meta description from HTML content
    """
    match = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', 
                     html_content, re.IGNORECASE)
    if not match:
        match = re.search(r'<meta[^>]*content="([^"]*)"[^>]*name="description"', 
                         html_content, re.IGNORECASE)
    if match:
        return clean_text(match.group(1))
    return ""

def expand_query(query: str) -> str:
    """
    Expand query with related terms to improve search results
    """
    # Clean the query first
    query = query.lower().strip()
    
    # Handle multi-word queries better
    query_phrases = [phrase.strip() for phrase in query.split() if phrase.strip()]
    
    # Tokenize the query
    tokens = []
    for phrase in query_phrases:
        tokens.extend(tokenize(phrase))
    
    # Create expanded query with original tokens
    expanded_query = tokens.copy()
    
    # Add stemmed versions if NLTK is available
    if NLTK_AVAILABLE:
        try:
            for token in tokens:
                stemmed = stemmer.stem(token)
                if stemmed != token and stemmed not in expanded_query:
                    expanded_query.append(stemmed)
        except Exception:
            pass
    
    # Add the original query phrases as well for exact matches
    for phrase in query_phrases:
        if phrase not in expanded_query and len(phrase) > 1:
            expanded_query.append(phrase)
    
    # Join the tokens back into a string
    return " ".join(expanded_query)

def identify_main_terms(query: str, stopwords: Set[str]) -> List[str]:
    """
    Identify the main terms in a query that should receive higher importance
    Uses heuristics like word length, position, and frequency
    """
    if not query:
        return []
        
    # Clean and tokenize
    query = query.lower().strip()
    tokens = tokenize(query)
    
    # Additional common words to ignore beyond stopwords
    additional_ignore_words = {
        "for", "with", "about", "from", "into", "during", "after", "before", 
        "without", "under", "over", "between", "through", "against", "among",
        "throughout", "towards", "upon", "concerning", "of", "to", "in", "on",
        "at", "by", "as", "via", "onto", "into", "within", "among", "along"
    }
    
    # Combined set of words to ignore
    ignore_words = stopwords.union(additional_ignore_words)
    
    # Filter out stopwords and common prepositions/conjunctions
    non_stop_tokens = [t for t in tokens if t not in ignore_words]
    
    # If we have no tokens after filtering, return original tokens
    if not non_stop_tokens:
        return tokens
    
    # Identify potential main terms based on length (longer words tend to be more important)
    main_terms = []
    
    # First, check for longer words (5+ chars) which are likely more important
    for token in non_stop_tokens:
        if len(token) >= 5:
            main_terms.append(token)
    
    # If we don't have any long words, consider medium length words (4+ chars)
    if not main_terms:
        for token in non_stop_tokens:
            if len(token) >= 4:
                main_terms.append(token)
    
    # If we still don't have main terms, use all non-ignored words
    if not main_terms:
        main_terms = non_stop_tokens
    
    # Prioritize first and last non-ignored terms in the query (often more important)
    first_non_ignored = next((t for t in tokens if t not in ignore_words), None)
    last_non_ignored = next((t for t in reversed(tokens) if t not in ignore_words), None)
    
    if first_non_ignored and first_non_ignored not in main_terms:
        main_terms.append(first_non_ignored)
    
    if last_non_ignored and last_non_ignored not in main_terms:
        main_terms.append(last_non_ignored)
    
    return main_terms 