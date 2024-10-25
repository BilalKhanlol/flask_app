# Gunicorn configuration file
import os

# Worker timeout increased to handle long-running requests
timeout = 300  # 5 minutes
workers = 4
threads = 2
worker_class = 'gthread'
bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"