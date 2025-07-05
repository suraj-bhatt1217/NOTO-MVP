# gunicorn.conf.py
import multiprocessing

# Number of workers = (2 x num_cores) + 1
workers = 1  # Reduced to 1 worker to minimize memory usage
threads = 4  # 4 threads per worker
worker_class = 'gthread'
worker_tmp_dir = '/dev/shm'  # Use shared memory if available
max_requests = 1000
max_requests_jitter = 50
timeout = 120
keepalive = 5