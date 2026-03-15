from sqlalchemy.orm import sessionmaker

from app.dataMAIN import engine

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
