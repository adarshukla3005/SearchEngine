"""
Script to run the content classifier
"""
import os
import sys
import argparse

# Add parent directory to path to import from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from search_engine.classifier.classifier import ContentClassifier
from utils.config import CLASSIFIER_CONFIG, CRAWLER_CONFIG

def main():
    """
    Main function to run the classifier
    """
    parser = argparse.ArgumentParser(description='Run the content classifier')
    parser.add_argument('--input-dir', type=str, default=CRAWLER_CONFIG["data_dir"],
                        help='Directory containing crawled pages')
    parser.add_argument('--output-dir', type=str, default=CLASSIFIER_CONFIG["output_dir"],
                        help='Directory to save classified pages')
    parser.add_argument('--batch-size', type=int, default=CLASSIFIER_CONFIG["batch_size"],
                        help='Batch size for processing')
    args = parser.parse_args()
    
    # Update config with command-line arguments
    config = CLASSIFIER_CONFIG.copy()
    config["output_dir"] = args.output_dir
    config["batch_size"] = args.batch_size
    
    # Create output directory if it doesn't exist
    os.makedirs(config["output_dir"], exist_ok=True)
    
    # Run classifier
    classifier = ContentClassifier(config)
    classifier.classify_batch(args.input_dir)

if __name__ == "__main__":
    main() 