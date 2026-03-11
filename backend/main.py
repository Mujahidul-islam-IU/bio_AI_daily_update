from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import json
from datetime import datetime

from schemas.models import DailyUpdate, Paper
from services.paper_service import PaperFetcher
from services.llm_service import LLMService
from database import SessionLocal, UpdateRecord, PaperRecord, ChatMessage

app = FastAPI(title="BioAI Daily Update API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "YOUR_GROQ_API_KEY_HERE")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY") 
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

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

# ─── Chat Endpoints ─────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str

@app.post("/papers/{paper_id}/chat")
async def chat_with_paper(paper_id: int, request: ChatRequest):
    db = SessionLocal()
    try:
        paper = db.query(PaperRecord).filter(PaperRecord.id == paper_id).first()
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        context = {
            "title": paper.title,
            "abstract": paper.abstract,
            "insights": paper.insight_summary
        }
        
        # Save user message
        user_msg = ChatMessage(paper_id=paper_id, role="user", content=request.message)
        db.add(user_msg)
        db.commit()
        
        # Generate AI answer
        answer = await llm_service.answer_paper_question(context, request.message)
        
        # Save AI response
        ai_msg = ChatMessage(paper_id=paper_id, role="ai", content=answer)
        db.add(ai_msg)
        db.commit()
        
        return {"answer": answer}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Chat error: {e}")
        return {"answer": f"Sorry, I encountered an error: {str(e)}. Please try again."}
    finally:
        db.close()

@app.get("/papers/{paper_id}/chat/history")
async def get_chat_history(paper_id: int):
    db = SessionLocal()
    try:
        messages = db.query(ChatMessage).filter(
            ChatMessage.paper_id == paper_id
        ).order_by(ChatMessage.timestamp.asc()).all()
        return [{"role": m.role, "content": m.content, "timestamp": str(m.timestamp)} for m in messages]
    finally:
        db.close()

# ─── Web Research ─────────────────────────────────────────

@app.get("/research/web")
async def get_web_research(query: str = "AI and Bioinformatics innovations"):
    if query in web_research_cache:
        return {"data": web_research_cache[query]}
    
    insight = await llm_service.search_web_innovation(query)
    web_research_cache[query] = insight
    return {"data": insight}

# ─── Research Trigger ─────────────────────────────────────

@app.post("/updates/research", response_model=DailyUpdate)
async def trigger_research(
    ai_topic: str = Query(..., description="Query for AI papers"),
    bio_topic: str = Query(..., description="Query for Bioinformatics papers"),
    db: Session = Depends(get_db)
):
    try:
        fetcher = PaperFetcher()
        # 1. Fetch from arXiv, PubMed, bioRxiv, and Semantic Scholar (Nature/Top Journals)
        ai_papers = fetcher.fetch_arxiv_papers(ai_topic, max_results=3)
        bio_papers = fetcher.fetch_pubmed_papers(bio_topic, max_results=3)
        biorxiv_papers = fetcher.fetch_biorxiv_papers(bio_topic, max_results=2)
        nature_papers = fetcher.fetch_springer_papers(bio_topic, max_results=2)
        
        all_papers = ai_papers + bio_papers + biorxiv_papers + nature_papers
    
        # Generate insights for all papers
        for paper in all_papers:
            paper.insights = await llm_service.generate_insights(paper)
        
        # Cross-Paper Gap Analysis
        gap_analysis = await llm_service.perform_cross_paper_analysis(all_papers)

        # Persist to DB
        new_update = UpdateRecord(date=datetime.now(), overall_gap_analysis=gap_analysis)
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
            db.commit()
            p.id = p_rec.id
        
        update_data = DailyUpdate(
            date=datetime.now(),
            ai_papers=ai_papers,
            bio_papers=bio_papers,
            biorxiv_papers=biorxiv_papers,
            nature_papers=nature_papers,
            overall_gap_analysis=gap_analysis
        )
        return update_data
    except Exception as e:
        print(f"Research trigger error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger research: {str(e)}")

# ─── History ─────────────────────────────────────────────

@app.get("/updates/history")
async def get_history():
    db = SessionLocal()
    try:
        updates = db.query(UpdateRecord).order_by(UpdateRecord.date.desc()).limit(20).all()
        result = []
        for u in updates:
            paper_count = db.query(PaperRecord).filter(PaperRecord.update_id == u.id).count()
            result.append({
                "id": u.id,
                "date": str(u.date),
                "paper_count": paper_count,
                "gap_analysis_preview": (u.overall_gap_analysis or "")[:200]
            })
        return result
    finally:
        db.close()

@app.get("/updates/{update_id}")
async def get_update_detail(update_id: int):
    db = SessionLocal()
    try:
        update = db.query(UpdateRecord).filter(UpdateRecord.id == update_id).first()
        if not update:
            raise HTTPException(status_code=404, detail="Update not found")
        
        papers = db.query(PaperRecord).filter(PaperRecord.update_id == update_id).all()
        paper_list = []
        for p in papers:
            paper_list.append({
                "id": p.id,
                "title": p.title,
                "authors": p.authors,
                "published_date": str(p.published_date),
                "abstract": p.abstract,
                "url": p.url,
                "category": p.category,
                "insight_summary": p.insight_summary,
                "key_technologies": json.loads(p.key_technologies) if p.key_technologies else [],
                "research_gaps": json.loads(p.research_gaps) if p.research_gaps else [],
                "bookmarked": p.bookmarked or False
            })
        
        return {
            "id": update.id,
            "date": str(update.date),
            "overall_gap_analysis": update.overall_gap_analysis,
            "papers": paper_list
        }
    finally:
        db.close()

# ─── Bookmarks ───────────────────────────────────────────

@app.post("/papers/{paper_id}/bookmark")
async def toggle_bookmark(paper_id: int):
    db = SessionLocal()
    try:
        paper = db.query(PaperRecord).filter(PaperRecord.id == paper_id).first()
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        paper.bookmarked = not (paper.bookmarked or False)
        db.commit()
        return {"bookmarked": paper.bookmarked}
    finally:
        db.close()

@app.get("/papers/bookmarks")
async def get_bookmarks():
    db = SessionLocal()
    try:
        papers = db.query(PaperRecord).filter(PaperRecord.bookmarked == True).all()
        return [{
            "id": p.id,
            "title": p.title,
            "authors": p.authors,
            "url": p.url,
            "category": p.category,
            "insight_summary": p.insight_summary,
            "bookmarked": True
        } for p in papers]
    finally:
        db.close()

# ─── Export ──────────────────────────────────────────────

@app.get("/updates/{update_id}/export", response_class=PlainTextResponse)
async def export_update(update_id: int):
    db = SessionLocal()
    try:
        update = db.query(UpdateRecord).filter(UpdateRecord.id == update_id).first()
        if not update:
            raise HTTPException(status_code=404, detail="Update not found")
        
        papers = db.query(PaperRecord).filter(PaperRecord.update_id == update_id).all()
        
        md = f"# BioAI Research Report\n"
        md += f"**Date:** {update.date}\n\n"
        
        if update.overall_gap_analysis:
            md += f"## Gap Analysis\n{update.overall_gap_analysis}\n\n"
        
        md += "## Papers\n\n"
        for p in papers:
            md += f"### {p.title}\n"
            md += f"- **Authors:** {p.authors}\n"
            md += f"- **Category:** {p.category}\n"
            md += f"- **URL:** {p.url}\n"
            if p.insight_summary:
                md += f"- **Summary:** {p.insight_summary}\n"
            techs = json.loads(p.key_technologies) if p.key_technologies else []
            if techs:
                md += f"- **Technologies:** {', '.join(techs)}\n"
            gaps = json.loads(p.research_gaps) if p.research_gaps else []
            if gaps:
                md += f"- **Research Gaps:** {', '.join(gaps)}\n"
            md += "\n"
        
        return md
    finally:
        db.close()
