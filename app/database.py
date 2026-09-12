from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core import settings

# Verilənlər bazasına qoşulma mühərriki
engine = create_engine(settings.database_url)

# Baza əməliyyatları üçün sessiya
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Modellərimiz üçün əsas sinif
Base = declarative_base()

# API endpointləri üçün asılılıq (Dependency)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
