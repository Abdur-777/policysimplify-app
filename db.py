from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
import os

# For SQLite local dev
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///policysimplify.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class CouncilUser(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    name = Column(String)
    email = Column(String)
    docs = relationship("PolicyDoc", back_populates="user")

class PolicyDoc(Base):
    __tablename__ = "docs"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    summary = Column(Text)
    obligations = Column(Text)  # Store as JSON string
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("CouncilUser", back_populates="docs")

def create_db():
    Base.metadata.create_all(bind=engine)
