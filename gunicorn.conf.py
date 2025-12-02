# gunicorn.conf.py
import multiprocessing
import os
import sys

# Bind to Railway's PORT environment variable, or default to 8080
bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"

# Number of workers = (2 x num_cores) + 1
workers = 1  # Reduced to 1 worker to minimize memory usage
threads = 4  # 4 threads per worker
worker_class = 'gthread'
worker_tmp_dir = '/dev/shm'  # Use shared memory if available
max_requests = 1000
max_requests_jitter = 50
timeout = 120
keepalive = 5

# Logging configuration - CRITICAL for Railway
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stderr
loglevel = 'info'
capture_output = True  # Capture stdout/stderr
enable_stdio_inheritance = True  # Inherit stdout/stderr

# Access log format - simple format that Railway can parse
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'