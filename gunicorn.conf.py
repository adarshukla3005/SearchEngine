import os

# Set production environment variable for the app
os.environ["PRODUCTION"] = "true"

# Worker configuration
workers = 4
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"  # Default to port 10000 for Render
timeout = 120  # Increased timeout for index loading
worker_class = "sync"
preload_app = True  # Preload the application to load the index once
accesslog = "-"
errorlog = "-"

# Called when worker processes are forked
def on_starting(server):
    print("Starting Gunicorn server with production settings")
    
# Called after the server is initialized but before it accepts connections
def post_fork(server, worker):
    print(f"Worker {worker.pid} forked") 