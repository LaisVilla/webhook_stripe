# gunicorn.conf.py
bind = "0.0.0.0:10000"  # O Render vai sobrescrever a porta
workers = 4
threads = 2
timeout = 120
keepalive = 5
worker_class = "gthread"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50