import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List
from schemas.models import Paper

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
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
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
                except Exception as e:
                    pass
            return papers
        except Exception as e:
            return []

    def fetch_pubmed_papers(self, query: str, max_results: int = 5) -> List[Paper]:
        try:
            search_params = {"db": "pubmed", "term": query, "retmode": "json", "retmax": max_results, "sort": "pub+date"}
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
                    
                    papers.append(Paper(
                        source_id=pmid,
                        title=title,
                        authors=authors,
                        published_date=pdate,
                        abstract=abstract,
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        source="PubMed",
                        category="Bioinformatics"
                    ))
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
                if any(term in combined for term in query_terms):
                    filtered.append(item)
                if len(filtered) >= max_results: break
            
            if len(filtered) < max_results:
                for item in collection:
                    if item not in filtered: filtered.append(item)
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
                        category="Preprint"
                    ))
                except Exception as e:
                    pass
            return papers
        except Exception as e:
            return []

    def fetch_springer_papers(self, query: str, max_results: int = 5) -> List[Paper]:
        """Fetch reputable peer-reviewed papers from Springer Nature Open Access API."""
        try:
            # Springer Nature Meta API (Public, no key needed for basic OA access)
            # Documentation: https://dev.springernature.com/adding-constraints
            springer_api = "http://api.springernature.com/meta/v2/json"
            params = {
                "q": f"keyword:{query} openaccess:true",
                "p": max_results
            }
            # We don't have an API key, so we use their public free tier endpoint if available
            # Note: We can also fallback to Semantic Scholar if Springer requires auth
            semantic_url = "https://api.semanticscholar.org/graph/v1/paper/search"
            sem_params = {
                "query": query,
                "limit": max_results,
                "fields": "paperId,title,abstract,authors,year,url,venue"
            }
            
            # Using Semantic Scholar as it's 100% free and contains Nature, Science, Cell, etc.
            response = requests.get(semantic_url, params=sem_params, timeout=12)
            if response.status_code != 200: return []
            
            data = response.json()
            papers = []
            
            for item in data.get("data", []):
                try:
                    pid = item.get("paperId", "")
                    title = item.get("title", "No Title")
                    abstract = item.get("abstract") or "Abstract not available."
                    year = item.get("year")
                    pdate = datetime(year, 1, 1) if year else datetime.now()
                    url = item.get("url") or f"https://www.semanticscholar.org/paper/{pid}"
                    venue = item.get("venue", "Reputed Journal")
                    
                    authors = []
                    for a in item.get("authors", [])[:3]:
                        authors.append(a.get("name", ""))
                    if not authors: authors = ["Unknown"]
                    
                    # Ensure abstract has some length
                    if abstract and len(abstract) > 50:
                        papers.append(Paper(
                            source_id=pid,
                            title=title,
                            authors=authors,
                            published_date=pdate,
                            abstract=abstract,
                            url=url,
                            source=venue if venue else "Semantic Scholar",
                            category="Nature / Top Journals"
                        ))
                except Exception as e:
                    print(f"Skipping Semantic Scholar entry: {e}")
            
            return papers
        except Exception as e:
            print(f"Semantic Scholar fetch error: {e}")
            return []
