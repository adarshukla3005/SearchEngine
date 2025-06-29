"""
Gunicorn configuration for deployment
"""
import os
import sys
import logging
import multiprocessing

# Set production environment variable for the app
os.environ["PRODUCTION"] = "true"

# Configure logging
logconfig_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'stream': sys.stdout
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'gunicorn.error': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'gunicorn.access': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    }
}

# Bind to the port provided by Render
bind = f"0.0.0.0:{os.environ.get('PORT', '3000')}"

# Worker configuration - use single worker to reduce memory usage
workers = 1  # Single worker to avoid memory issues on free tier
worker_class = "sync"  # Use sync workers for stability
worker_connections = 1000
timeout = 300  # Increase timeout to allow index loading
keepalive = 5

# Disable preload to avoid memory issues
preload_app = False

# Set production environment
raw_env = [
    "PRODUCTION=true",
]

# Logging configuration
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"

# Capture output
capture_output = True

# Graceful timeout
graceful_timeout = 120

# Process naming
proc_name = "search_engine"

# Memory optimization
max_requests = 1  # Restart workers after each request to free memory
worker_tmp_dir = "/dev/shm"  # Use shared memory for temp files

# Called when worker processes are forked
def on_starting(server):
    print("Starting Gunicorn server with production settings")
    
# Called after the server is initialized but before it accepts connections
def post_fork(server, worker):
    print(f"Worker {worker.pid} forked")
    
# Called just before a worker processes the request
def pre_request(worker, req):
    worker.log.debug("%s %s" % (req.method, req.path))
    
# Called after a worker processes the request
def post_request(worker, req, environ, resp):
    worker.log.debug("Response status: %s" % resp.status) 