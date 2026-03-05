import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List
from schemas.models import Paper

class PaperFetcher:
    def __init__(self):
        self.arxiv_url = "http://export.arxiv.org/api/query"
        self.pubmed_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        self.pubmed_summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    def fetch_arxiv_papers(self, query: str, max_results: int = 5) -> List[Paper]:
        params = {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }
        response = requests.get(self.arxiv_url, params=params)
        if response.status_code != 200:
            return []

        root = ET.fromstring(response.content)
        papers = []
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        for entry in root.findall('atom:entry', ns):
            paper_id = entry.find('atom:id', ns).text
            title = entry.find('atom:title', ns).text.strip()
            abstract = entry.find('atom:summary', ns).text.strip()
            published = entry.find('atom:published', ns).text
            url = entry.find('atom:link[@rel="alternate"]', ns).attrib['href']
            authors = [author.find('atom:name', ns).text for author in entry.findall('atom:author', ns)]
            
            papers.append(Paper(
                source_id=paper_id,
                title=title,
                authors=authors,
                published_date=datetime.fromisoformat(published.replace('Z', '+00:00')),
                abstract=abstract,
                url=url,
                source="arXiv",
                category="AI/ML"
            ))
        return papers

    def fetch_pubmed_papers(self, query: str, max_results: int = 5) -> List[Paper]:
        # Simple PubMed search implementation
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": max_results,
            "sort": "pub+date"
        }
        response = requests.get(self.pubmed_url, params=params)
        if response.status_code != 200:
            return []
        
        id_list = response.json().get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return []

        # Fetch summaries
        summary_params = {
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "json"
        }
        res_summary = requests.get(self.pubmed_summary_url, summary_params)
        if res_summary.status_code != 200:
            return []

        result = res_summary.json().get("result", {})
        papers = []
        for pid in id_list:
            item = result.get(pid)
            if not item: continue
            
            papers.append(Paper(
                source_id=pid,
                title=item.get("title", "No Title"),
                authors=[a.get("name") for a in item.get("authors", [])],
                published_date=datetime.strptime(item.get("pubdate"), "%Y %b %d") if " " in item.get("pubdate") else datetime.now(),
                abstract="Summary view restricted in API. Visit link for details.", # Abstract requires extra fetch
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pid}/",
                source="PubMed",
                category="Bioinformatics"
            ))
        return papers
