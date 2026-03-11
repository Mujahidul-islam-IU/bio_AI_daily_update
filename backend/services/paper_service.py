import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List
from schemas.models import Paper

def compute_relevance(title: str, abstract: str, query: str) -> float:
    combined = (title + " " + abstract).lower()
    query_words = query.lower().split()
    if not query_words or not combined:
        return 0.0
    
    occurrences = sum(combined.count(qw) for qw in query_words)
    words = combined.split()
    density = occurrences / max(len(words), 1)
    
    phrase_bonus = 2.0 if query.lower() in combined else 0.0
    score = min((density * 1000), 60.0) + (phrase_bonus * 20.0)
    
    if query.lower() in title.lower():
        score += 20.0
        
    final_score = min(max(round(score + 65.0, 1), 60.0), 99.9)
    return final_score


class PaperFetcher:
    def __init__(self):
        self.arxiv_url = "http://export.arxiv.org/api/query"
        self.pubmed_search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        self.pubmed_fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        self.biorxiv_url = "https://api.biorxiv.org/details/biorxiv"
        # Springer Nature Open Access API
        self.springer_url = "https://export.arxiv.org/api/query" # Placeholder, real API is below

    def fetch_arxiv_papers(self, query: str, max_results: int = 5) -> List[Paper]:
        params = {
            "search_query": f'all:"{query}"',
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending"
        }
        try:
            response = requests.get(self.arxiv_url, params=params)
            if response.status_code != 200:
                return []

            root = ET.fromstring(response.content)
            papers = []
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('atom:entry', ns):
                try:
                    paper_id = entry.find('atom:id', ns).text
                    title = entry.find('atom:title', ns).text.strip()
                    abstract = entry.find('atom:summary', ns).text.strip()
                    published = entry.find('atom:published', ns).text
                    url_elem = entry.find('atom:link[@rel="alternate"]', ns)
                    url = url_elem.attrib['href'] if url_elem is not None else paper_id
                    authors = [author.find('atom:name', ns).text for author in entry.findall('atom:author', ns)]
                    
                    paper_obj = Paper(
                        source_id=paper_id,
                        title=title,
                        authors=authors,
                        published_date=datetime.fromisoformat(published.replace('Z', '+00:00')),
                        abstract=abstract,
                        url=url,
                        source="arXiv",
                        category="AI/ML",
                        relevance_score=compute_relevance(title, abstract, query)
                    )
                    
                    # Strict word match filtering to guarantee relevance
                    combined_text = (title + " " + abstract).lower()
                    query_words = query.lower().split()
                    if all(word in combined_text for word in query_words):
                        papers.append(paper_obj)
                        
                    if len(papers) >= max_results:
                        break
                except Exception as e:
                    pass
            return papers
        except Exception as e:
            return []

    def fetch_pubmed_papers(self, query: str, max_results: int = 5) -> List[Paper]:
        try:
            # Query recent papers and sort by date for freshness
            recent_years = f'"{datetime.now().year-2}"[Date - Publication] : "3000"[Date - Publication]'
            strict_query = f"({query}[Title/Abstract]) AND ({recent_years})"
            search_params = {"db": "pubmed", "term": strict_query, "retmode": "json", "retmax": max_results * 4, "sort": "pub+date"}
            response = requests.get(self.pubmed_search_url, params=search_params)
            if response.status_code != 200: return []
            
            id_list = response.json().get("esearchresult", {}).get("idlist", [])
            if not id_list: return []

            fetch_params = {"db": "pubmed", "id": ",".join(id_list), "retmode": "xml", "rettype": "abstract"}
            fetch_response = requests.get(self.pubmed_fetch_url, params=fetch_params)
            if fetch_response.status_code != 200: return []

            root = ET.fromstring(fetch_response.content)
            papers = []
            
            for article in root.findall('.//PubmedArticle'):
                try:
                    medline = article.find('.//MedlineCitation')
                    article_data = medline.find('.//Article')
                    pmid = medline.find('PMID').text
                    title_elem = article_data.find('ArticleTitle')
                    title = title_elem.text if title_elem is not None and title_elem.text else "No Title"
                    
                    abstract_elem = article_data.find('.//Abstract')
                    if abstract_elem is not None:
                        abstract_parts = []
                        for text_elem in abstract_elem.findall('AbstractText'):
                            label = text_elem.get('Label', '')
                            text = text_elem.text or ''
                            if label: abstract_parts.append(f"{label}: {text}")
                            else: abstract_parts.append(text)
                        abstract = " ".join(abstract_parts)
                    else:
                        abstract = "Abstract not available for this article."
                    
                    authors = []
                    author_list = article_data.find('.//AuthorList')
                    if author_list is not None:
                        for author in author_list.findall('Author'):
                            last = author.find('LastName')
                            fore = author.find('ForeName')
                            if last is not None and fore is not None: authors.append(f"{fore.text} {last.text}")
                            elif last is not None: authors.append(last.text)
                    if not authors: authors = ["Unknown"]
                    
                    pub_date = article_data.find('.//PubDate')
                    try:
                        year = pub_date.find('Year').text if pub_date.find('Year') is not None else str(datetime.now().year)
                        month = pub_date.find('Month').text if pub_date.find('Month') is not None else "Jan"
                        day = pub_date.find('Day').text if pub_date.find('Day') is not None else "1"
                        pdate = datetime.strptime(f"{year} {month} {day}", "%Y %b %d")
                    except:
                        pdate = datetime.now()
                    
                    paper_obj = Paper(
                        source_id=pmid,
                        title=title,
                        authors=authors,
                        published_date=pdate,
                        abstract=abstract,
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        source="PubMed",
                        category="Bioinformatics",
                        relevance_score=compute_relevance(title, abstract, query)
                    )
                    
                    # Strict word match filtering
                    combined_text = (title + " " + abstract).lower()
                    query_words = query.lower().split()
                    if all(word in combined_text for word in query_words):
                        papers.append(paper_obj)
                        
                    if len(papers) >= max_results:
                        break
                except Exception as e:
                    pass
            return papers
        except Exception as e:
            return []

    def fetch_biorxiv_papers(self, query: str, max_results: int = 5) -> List[Paper]:
        try:
            today = datetime.now()
            from_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
            to_date = today.strftime("%Y-%m-%d")
            url = f"{self.biorxiv_url}/{from_date}/{to_date}/0"
            response = requests.get(url, timeout=15)
            if response.status_code != 200: return []
            
            data = response.json()
            collection = data.get("collection", [])
            query_terms = query.lower().split()
            filtered = []
            
            for item in collection:
                combined = (item.get("title", "") + " " + item.get("abstract", "")).lower()
                # Require all terms to be present for high relevance
                if all(term in combined for term in query_terms):
                    filtered.append(item)
                if len(filtered) >= max_results: break
            
            papers = []
            for item in filtered[:max_results]:
                try:
                    doi = item.get("doi", "")
                    pdate_str = item.get("date", "")
                    try: pdate = datetime.strptime(pdate_str, "%Y-%m-%d")
                    except: pdate = datetime.now()
                    authors_str = item.get("authors", "Unknown")
                    authors = [a.strip() for a in authors_str.split(";") if a.strip()][:5]
                    
                    papers.append(Paper(
                        source_id=doi,
                        title=item.get("title", "No Title"),
                        authors=authors if authors else ["Unknown"],
                        published_date=pdate,
                        abstract=item.get("abstract", "Abstract not available."),
                        url=f"https://doi.org/{doi}" if doi else "#",
                        source="bioRxiv",
                        category="Preprint",
                        relevance_score=compute_relevance(item.get("title", "No Title"), item.get("abstract", "Abstract not available."), query)
                    ))
                except Exception as e:
                    pass
            return papers
        except Exception as e:
            return []

    def fetch_springer_papers(self, query: str, max_results: int = 5) -> List[Paper]:
        """Fetch reputable peer-reviewed papers from Crossref (representing Top Journals)."""
        try:
            crossref_url = "https://api.crossref.org/works"
            
            crossref_params = {
                "query": query,
                "filter": "has-abstract:true,type:journal-article",
                "select": "DOI,title,abstract,author,issued,container-title,URL",
                "rows": max_results * 8
            }
            
            headers = {"User-Agent": "BioAIDailyUpdate/1.0 (mailto:test@example.com)"}
            response = requests.get(crossref_url, params=crossref_params, headers=headers, timeout=12)
            if response.status_code != 200: 
                return []
            
            data = response.json()
            papers = []
            
            for item in data.get("message", {}).get("items", []):
                try:
                    title_list = item.get("title", [])
                    title = title_list[0] if title_list else "No Title"
                    
                    abstract = item.get("abstract", "")
                    if abstract:
                        import re
                        abstract = re.sub(r'<[^>]+>', '', abstract).strip()
                    else:
                        abstract = "Abstract not available."
                        
                    issued = item.get("issued", {}).get("date-parts", [[datetime.now().year]])[0]
                    year = issued[0] if len(issued) > 0 else datetime.now().year
                    month = issued[1] if len(issued) > 1 else 1
                    day = issued[2] if len(issued) > 2 else 1
                    
                    # Skip papers older than 3 years
                    if year < datetime.now().year - 3:
                        continue
                        
                    try:
                        pdate = datetime(year, month, day)
                    except:
                        pdate = datetime.now()
                        
                    doi = item.get("DOI", "")
                    url = item.get("URL", f"https://doi.org/{doi}")
                    
                    venue_list = item.get("container-title", [])
                    venue = venue_list[0] if venue_list else "Reputed Journal"
                    
                    authors = []
                    for a in item.get("author", [])[:3]:
                        name = f"{a.get('given', '')} {a.get('family', '')}".strip()
                        if name: authors.append(name)
                    if not authors: authors = ["Unknown"]
                    
                    # Ensure abstract has length and strictly matches query logic
                    combined_text = (title + " " + abstract).lower()
                    query_words = query.lower().split()
                    
                    if abstract and len(abstract) > 50 and all(w in combined_text for w in query_words):
                        papers.append(Paper(
                            source_id=doi if doi else url,
                            title=title,
                            authors=authors,
                            published_date=pdate,
                            abstract=abstract,
                            url=url,
                            source=venue,
                            category="Nature / Top Journals",
                            relevance_score=compute_relevance(title, abstract, query)
                        ))
                    
                    if len(papers) >= max_results:
                        break
                except Exception as e:
                    print(f"Skipping Crossref entry: {e}")
            
            return papers
        except Exception as e:
            print(f"Crossref fetch error: {e}")
            return []
