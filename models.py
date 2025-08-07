# models.py
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

DB_URL = "sqlite:///policysimplify.db"
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class PolicyDoc(Base):
    __tablename__ = "docs"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    gcs_url = Column(String)
    summary = Column(Text)
    obligations = Column(Text)
    upload_time = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit"
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String)
    filename = Column(String)
    obligation = Column(Text)
    who = Column(String)
    time = Column(DateTime, default=datetime.utcnow)

def create_db():
    Base.metadata.create_all(bind=engine)
