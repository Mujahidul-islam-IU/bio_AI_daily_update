from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, ForeignKey, Boolean
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
    bookmarked = Column(Boolean, default=False)
    relevance_score = Column(Float, default=0.0)
    
    update = relationship("UpdateRecord", back_populates="papers")
    chat_messages = relationship("ChatMessage", back_populates="paper")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"))
    role = Column(String)  # 'user' or 'ai'
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    paper = relationship("PaperRecord", back_populates="chat_messages")

Base.metadata.create_all(bind=engine)

# Auto-migration for existing databases
def run_migrations():
    """Ensure all required columns exist in the database."""
    try:
        with engine.connect() as conn:
            from sqlalchemy import inspect, text
            inspector = inspect(engine)
            
            # Check papers table
            if 'papers' in inspector.get_table_names():
                columns = [c['name'] for c in inspector.get_columns('papers')]
                if 'source_id' not in columns:
                    conn.execute(text("ALTER TABLE papers ADD COLUMN source_id TEXT"))
                if 'bookmarked' not in columns:
                    conn.execute(text("ALTER TABLE papers ADD COLUMN bookmarked BOOLEAN DEFAULT 0"))
                if 'relevance_score' not in columns:
                    conn.execute(text("ALTER TABLE papers ADD COLUMN relevance_score REAL DEFAULT 0.0"))
                conn.commit()
            
            # Check updates table
            if 'updates' in inspector.get_table_names():
                columns = [c['name'] for c in inspector.get_columns('updates')]
                if 'overall_gap_analysis' not in columns:
                    conn.execute(text("ALTER TABLE updates ADD COLUMN overall_gap_analysis TEXT"))
                conn.commit()
    except Exception as e:
        print(f"Migration notice: {e}")

run_migrations()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
