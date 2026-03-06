from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import json
from datetime import datetime

from schemas.models import DailyUpdate, Paper
from services.paper_service import PaperFetcher
from services.llm_service import LLMService
from database import SessionLocal, UpdateRecord, PaperRecord

app = FastAPI(title="BioAI Daily Update API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, you can restrict this to your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Keys - Set these in your environment or a .env file
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "YOUR_GROQ_API_KEY_HERE")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY") 
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") # User fallback key

llm_service = LLMService(api_key=GROQ_API_KEY, tavily_key=TAVILY_API_KEY, gemini_key=GEMINI_API_KEY)
fetcher = PaperFetcher()

# In-memory storage
latest_update = None
web_research_cache = {}

@app.get("/")
async def root():
    return {"message": "BioAI Daily Update API is running"}

@app.get("/updates/latest", response_model=DailyUpdate)
async def get_latest_update():
    if not latest_update:
        raise HTTPException(status_code=404, detail="No updates found.")
    return latest_update

class ChatRequest(BaseModel):
    message: str

@app.post("/papers/{paper_id}/chat")
async def chat_with_paper(paper_id: int, request: ChatRequest):
    db = SessionLocal()
    paper = db.query(PaperRecord).filter(PaperRecord.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    context = {
        "title": paper.title,
        "abstract": paper.abstract,
        "insights": paper.insight_summary
    }
    
    answer = await llm_service.answer_paper_question(context, request.message)
    return {"answer": answer}

@app.get("/research/web")
async def get_web_research(query: str = "AI and Bioinformatics innovations"):
    # Web research using Groq (Simulated trends as Groq lacks live search)
    if query in web_research_cache:
        return {"data": web_research_cache[query]}
    
    insight = await llm_service.search_web_innovation(query)
    web_research_cache[query] = insight
    return {"data": insight}

# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/updates/history")
async def get_history():
    db = SessionLocal()
    updates = db.query(UpdateRecord).order_by(UpdateRecord.date.desc()).limit(10).all()
    return updates

@app.post("/updates/research")
async def trigger_research(ai_topic: str = "AI and Machine Learning", bio_topic: str = "Single-cell cancer bioinformatics"):
    global latest_update
    
    # AI/ML Search
    ai_papers = fetcher.fetch_arxiv_papers(ai_topic, max_results=5)
    
    # Bioinformatics Search
    bio_papers = fetcher.fetch_pubmed_papers(bio_topic, max_results=5)
    
    # Generate insights
    all_papers = ai_papers + bio_papers
    for paper in all_papers:
        paper.insights = await llm_service.generate_insights(paper)
    
    # Perform Cross-Paper Gap Analysis
    overall_gap = await llm_service.perform_cross_paper_analysis(all_papers)

    # Persist to DB
    db = SessionLocal()
    new_update = UpdateRecord(date=datetime.now(), overall_gap_analysis=overall_gap)
    db.add(new_update)
    db.commit()
    db.refresh(new_update)

    for p in all_papers:
        p_rec = PaperRecord(
            update_id=new_update.id,
            source_id=p.source_id,
            title=p.title,
            authors=", ".join(p.authors),
            published_date=p.published_date,
            abstract=p.abstract,
            url=p.url,
            category=p.category,
            insight_summary=p.insights.summary if p.insights else "",
            key_technologies=json.dumps(p.insights.key_technologies if p.insights else []),
            research_gaps=json.dumps(p.insights.research_gaps if p.insights else [])
        )
        db.add(p_rec)
        db.commit() # Commit each to get ID
        p.id = p_rec.id # Attach DB ID back to Pydantic object
    
    latest_update = DailyUpdate(
        date=new_update.date,
        ai_papers=ai_papers,
        bio_papers=bio_papers,
        overall_gap_analysis=overall_gap
    )
    return {"message": "Research completed and saved", "id": new_update.id, "gap_analysis": overall_gap}
