from app.core import request_data_from_url, url_bootstrap_static


bootstrap_static = request_data_from_url(url_bootstrap_static)

events = bootstrap_static['events']
