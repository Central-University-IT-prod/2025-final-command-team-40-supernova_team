import os

import redis

REDIS_URL = os.environ["REDIS_URL"]

redis_session = redis.from_url(REDIS_URL)
