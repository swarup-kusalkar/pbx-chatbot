from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import config

DATABASE_URL = (
    f"mysql+pymysql://{config.MYSQL_USER}:{config.MYSQL_PASSWORD}"
    f"@{config.MYSQL_HOST}:{config.MYSQL_PORT}/{config.MYSQL_DATABASE}"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()