from sqlalchemy import create_engine, Column, String, Boolean, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine       = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()

class Patient(Base):
    __tablename__ = "patients"
    id         = Column(String, primary_key=True)
    name       = Column(String, nullable=False)
    email      = Column(String, unique=True, nullable=False)
    password   = Column(String, nullable=False)
    phone      = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active  = Column(Boolean, default=True)

class Doctor(Base):
    __tablename__ = "doctors"
    id             = Column(String, primary_key=True)
    name           = Column(String, nullable=False)
    email          = Column(String, unique=True, nullable=False)
    password       = Column(String, nullable=False)
    phone          = Column(String, nullable=True)
    specialization = Column(String, nullable=True)
    hospital       = Column(String, nullable=True)
    latitude       = Column(Float, nullable=True)
    longitude      = Column(Float, nullable=True)
    is_available   = Column(Boolean, default=True)
    created_at     = Column(DateTime, default=datetime.utcnow)

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()