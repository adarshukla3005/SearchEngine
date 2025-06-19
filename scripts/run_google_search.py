"""
Script to run the search engine with fast Google search integration
"""
import os
import sys
import argparse
import subprocess
import time
from dotenv import load_dotenv

# Add parent directory to path to import from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def check_api_key():
    """Check if Gemini API key is set"""
    load_dotenv(".env")  # Load from renamed file
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key or api_key == "your_gemini_api_key_here":
        print("\n⚠️ WARNING: Gemini API key not found or not set!")
        print("Please edit the .env file and add your Gemini API key.")
        print("You can get a key from: https://aistudio.google.com/app/apikey\n")
        
        # Ask if user wants to continue without API key
        response = input("Do you want to continue without the API key? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
        print("Continuing without API key. LLM validation will be skipped.\n")

def run_command(command, description):
    """Run a command and print its output"""
    print(f"\n=== {description} ===")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"Error running {description}. Return code: {result.returncode}")
        sys.exit(1)
    return result

def install_dependencies():
    """Install required dependencies"""
    print("\n=== Checking and installing dependencies ===")
    
    # Check if googlesearch-python is installed
    try:
        import googlesearch
        print("✓ googlesearch-python is already installed")
    except ImportError:
        print("Installing googlesearch-python...")
        subprocess.run("pip install googlesearch-python", shell=True)
    
    # Check if google-generativeai is installed
    try:
        import google.generativeai
        print("✓ google-generativeai is already installed")
    except ImportError:
        print("Installing google-generativeai...")
        subprocess.run("pip install google-generativeai", shell=True)
        
    # Check if concurrent.futures is available (should be in standard library)
    try:
        import concurrent.futures
        print("✓ concurrent.futures is available")
    except ImportError:
        print("Warning: concurrent.futures module not available. This may affect performance.")

def main():
    """Main function to run the search engine with fast Google search"""
    parser = argparse.ArgumentParser(description='Run the search engine with fast Google search integration')
    parser.add_argument('--skip-index', action='store_true', help='Skip loading the local index')
    parser.add_argument('--combine-results', action='store_true', help='Combine Google search with local index results')
    parser.add_argument('--use-validation', action='store_true', help='Use Gemini validation (slower but more accurate)')
    args = parser.parse_args()
    
    # Check dependencies
    install_dependencies()
    
    # Check API key
    check_api_key()
    
    # Create necessary directories
    os.makedirs("data/google_cache", exist_ok=True)
    
    # Update config if needed
    if args.skip_index:
        try:
            # Try to update local config first
            config_path = os.path.join(os.path.dirname(__file__), '../config.py')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    content = f.read()
                content = content.replace('"fallback_to_index": True', '"fallback_to_index": False')
                with open(config_path, 'w') as f:
                    f.write(content)
                print("\n=== Updated local config to skip index fallback ===")
            else:
                # Fall back to main config
                run_command(
                    'python -c "import json; f=open(\'config.py\', \'r\'); '
                    'content=f.read(); f.close(); '
                    'content=content.replace(\'\"fallback_to_index\": True\', \'\"fallback_to_index\": False\'); '
                    'f=open(\'config.py\', \'w\'); f.write(content); f.close()"',
                    "Updating config to skip index fallback"
                )
        except Exception as e:
            print(f"Error updating config: {e}")
    
    if args.combine_results:
        try:
            # Try to update local config first
            config_path = os.path.join(os.path.dirname(__file__), '../config.py')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    content = f.read()
                content = content.replace('"combine_results": False', '"combine_results": True')
                with open(config_path, 'w') as f:
                    f.write(content)
                print("\n=== Updated local config to combine results ===")
            else:
                # Fall back to main config
                run_command(
                    'python -c "import json; f=open(\'config.py\', \'r\'); '
                    'content=f.read(); f.close(); '
                    'content=content.replace(\'\"combine_results\": False\', \'\"combine_results\": True\'); '
                    'f=open(\'config.py\', \'w\'); f.write(content); f.close()"',
                    "Updating config to combine results"
                )
        except Exception as e:
            print(f"Error updating config: {e}")
    
    if args.use_validation:
        try:
            # Try to update local config first
            config_path = os.path.join(os.path.dirname(__file__), '../config.py')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    content = f.read()
                content = content.replace('"skip_validation": True', '"skip_validation": False')
                with open(config_path, 'w') as f:
                    f.write(content)
                print("\n=== Updated local config to use Gemini validation ===")
            else:
                # Fall back to main config
                run_command(
                    'python -c "import json; f=open(\'config.py\', \'r\'); '
                    'content=f.read(); f.close(); '
                    'content=content.replace(\'\"skip_validation\": True\', \'\"skip_validation\": False\'); '
                    'f=open(\'config.py\', \'w\'); f.write(content); f.close()"',
                    "Updating config to use Gemini validation"
                )
        except Exception as e:
            print(f"Error updating config: {e}")
    
    # Start the web interface
    print("\n=== Starting web interface with fast Google search ===")
    print("Access the search engine at http://localhost:5000")
    
    # Get the current script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Run the app.py from the root directory
    app_path = os.path.join(script_dir, "../app.py")
    if os.path.exists(app_path):
        subprocess.run(f"python {app_path}", shell=True)
    else:
        print(f"Error: Could not find app.py at {app_path}")
        sys.exit(1)

if __name__ == "__main__":
    main() 