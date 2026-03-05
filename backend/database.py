from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///./bioai.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UpdateRecord(Base):
    __tablename__ = "updates"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    overall_gap_analysis = Column(Text, nullable=True)
    papers = relationship("PaperRecord", back_populates="update")

class PaperRecord(Base):
    __tablename__ = "papers"
    id = Column(Integer, primary_key=True, index=True)
    update_id = Column(Integer, ForeignKey("updates.id"))
    source_id = Column(String)
    title = Column(String)
    authors = Column(String)
    published_date = Column(DateTime)
    abstract = Column(Text)
    url = Column(String)
    category = Column(String)
    insight_summary = Column(Text)
    key_technologies = Column(String) # JSON string
    research_gaps = Column(String)    # JSON string
    
    update = relationship("UpdateRecord", back_populates="papers")

Base.metadata.create_all(bind=engine)
