from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class PaperInsight(BaseModel):
    summary: str
    key_technologies: List[str]
    research_gaps: List[str]
    multimodal_insights: Optional[str] = None

class Paper(BaseModel):
    id: Optional[int] = None
    source_id: str
    title: str
    authors: List[str]
    published_date: datetime
    abstract: str
    url: str
    source: str  # e.g., 'arXiv', 'PubMed', 'bioRxiv'
    category: str  # e.g., 'AI/ML', 'Bioinformatics'
    insights: Optional[PaperInsight] = None
    figure_urls: List[str] = Field(default_factory=list)

class DailyUpdate(BaseModel):
    date: datetime
    ai_papers: List[Paper]
    bio_papers: List[Paper]
    biorxiv_papers: List[Paper] = []
    overall_gap_analysis: Optional[str] = None
