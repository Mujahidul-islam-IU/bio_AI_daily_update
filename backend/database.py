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

# Auto-migration for existing databases
def run_migrations():
    """Ensure all required columns exist in the database."""
    try:
        # Use raw connection for DDL check
        with engine.connect() as conn:
            # Check papers table for source_id
            from sqlalchemy import inspect
            inspector = inspect(engine)
            columns = [c['name'] for c in inspector.get_columns('papers')]
            if 'source_id' not in columns:
                print("Adding source_id to papers table...")
                conn.execute("ALTER TABLE papers ADD COLUMN source_id TEXT")
            
            # Check updates table for overall_gap_analysis
            columns = [c['name'] for c in inspector.get_columns('updates')]
            if 'overall_gap_analysis' not in columns:
                print("Adding overall_gap_analysis to updates table...")
                conn.execute("ALTER TABLE updates ADD COLUMN overall_gap_analysis TEXT")
    except Exception as e:
        print(f"Migration notice: {e}")

run_migrations()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
