import os

# App stuff
DEBUG = True
SECRET_KEY = "development key"
RATELIMIT_HEADERS_ENABLED = True

# Database stuff.
pg_user = os.environ.get("POSTGRES_ENV_POSTGRES_USER", "osrc")
pg_password = os.environ.get("POSTGRES_ENV_POSTGRES_PASSWORD", "osrc")
pg_host = os.environ.get("POSTGRES_HOST", "db")
pg_port = os.environ.get("POSTGRES_PORT_5432_TCP_ADDR", "5432")
SQLALCHEMY_DATABASE_URI = "postgresql://{0}:{1}@{2}:{3}/postgres".format(
    pg_user, pg_password, pg_host, pg_port
)
SQLALCHEMY_TRACK_MODIFICATIONS = False

REDIS_URI = "redis://redis:6379/0"
REDIS_PREFIX = "osrc2"
REDIS_DEFAULT_TTL = 6 * 30 * 24 * 60 * 60

# GitHub stuff.
GITHUB_ID = None
GITHUB_SECRET = None

# Google stuff.
GOOGLE_KEY = None
