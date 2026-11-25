"""Production Gunicorn configuration (Linux server with systemd + Nginx).

Run: gunicorn -c gunicorn.conf.py "app.main:create_app()"
"""

import multiprocessing
import os

bind = os.getenv("GUNICORN_BIND", "127.0.0.1:8000")
worker_class = "uvicorn.workers.UvicornWorker"
workers = int(os.getenv("WEB_CONCURRENCY", str(min(multiprocessing.cpu_count() * 2 + 1, 8))))
timeout = 60
graceful_timeout = 30
keepalive = 5

# Recycle workers periodically to bound memory growth over long uptimes.
max_requests = 2000
max_requests_jitter = 200

accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
forwarded_allow_ips = "127.0.0.1"
