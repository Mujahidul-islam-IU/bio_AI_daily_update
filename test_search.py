import sys
import os
sys.path.append('c:\\KH mujahidul\\bio_AI_daily_update\\backend')

from services.paper_service import PaperFetcher

def test_fetcher():
    fetcher = PaperFetcher()
    
    print("--- ArXiv (AI/ML) Test ---")
    query = "Large Language Models in Healthcare"
    ai_papers = fetcher.fetch_arxiv_papers(query, max_results=2)
    for p in ai_papers:
        print(f"TITLE: {p.title}")
    
    print("\n--- PubMed (Bioinformatics) Test ---")
    query = "Single-cell RNA sequencing"
    bio_papers = fetcher.fetch_pubmed_papers(query, max_results=2)
    for p in bio_papers:
        print(f"TITLE: {p.title}")
        
    print("\n--- bioRxiv (Preprint) Test ---")
    query = "Cancer Genomics"
    rxiv = fetcher.fetch_biorxiv_papers(query, max_results=2)
    for p in rxiv:
        print(f"TITLE: {p.title}")

    print("\n--- Semantic Scholar (Nature/Top Journals) Test ---")
    query = "Transformers in Genomics"
    sem = fetcher.fetch_springer_papers(query, max_results=2)
    for p in sem:
        print(f"TITLE: {p.title}")

if __name__ == "__main__":
    test_fetcher()
