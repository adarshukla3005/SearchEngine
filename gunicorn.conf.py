import os

workers = 4
bind = f"0.0.0.0:{os.environ.get('PORT', '3000')}"
timeout = 120
worker_class = "sync"
accesslog = "-"
errorlog = "-" 