import os

DEBUG = False
SECRET_KEY = "development key"

# Database stuff.
pg_user = os.environ.get("POSTGRES_ENV_POSTGRES_USER", "postgres")
pg_password = os.environ.get("POSTGRES_ENV_POSTGRES_PASSWORD", "password")
pg_ip = os.environ.get("POSTGRES_PORT_5432_TCP_ADDR", "localhost")
SQLALCHEMY_DATABASE_URI = "postgresql://{0}:{1}@{2}:5432/postgres".format(
    pg_user, pg_password, pg_ip
)
SQLALCHEMY_TRACK_MODIFICATIONS = False

# GitHub stuff.
GITHUB_ID = None
GITHUB_SECRET = None

# Google stuff.
GOOGLE_KEY = None
