import os
from sqlalchemy import create_engine
DEFAULT_URL = "mysql+pymysql://root:password@localhost:3306/conference_db"

def make_engine():
    url = os.environ.get("DATABASE_URL", DEFAULT_URL)
    connect_args = {}
    if os.environ.get("DB_SSL_CA"):
        connect_args["ssl_ca"] = os.environ["DB_SSL_CA"]
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=280,
        connect_args=connect_args,
    )