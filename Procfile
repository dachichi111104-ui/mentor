web: gunicorn projecthub_config.wsgi --log-file -
worker: celery -A projecthub_config worker --loglevel=info
beat: celery -A projecthub_config beat --loglevel=info
