import requests
import xml.etree.ElementTree as ET
from  database import get_papers_id


class Controller:
    """Main class for interacting with xariv API"""

    def __init__(self, limit=5):
        
        #|---search in the AI category or with a title having AI---|
        self.PARAMS = {
            "search_query": "cat:cs.AI OR ti:\"artificial intelligence\"",
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": limit
        }
        self.URL = "http://export.arxiv.org/api/query"


    def get_articles(self):
        """Get new articles if they are different"""

        #|----Call arXiv API----|
        print("Sending API request")
        response = requests.get(self.URL, params=self.PARAMS)
        response.raise_for_status()
        print("Success")
        root = ET.fromstring(response.content)

        articles, ids = self.proccess_xml(root)
        return ids

    def proccess_xml(self, root) -> tuple[list[dict], list[str]]:
        """Proccess XML from arxiv and return tuple of (articles, ids)"""
        # arXiv returns Atom XML format        
        namespace = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom"
        }
        fetched_articles = []
        fetched_ids = []

        #|----Proccess XML package----|
        print("Processing XML package")
        for entry in root.findall("atom:entry", namespace):
            
            pub_date = entry.find("atom:published", namespace).text[:10]

            # Make tile & abstract one line
            title = entry.find("atom:title", namespace).text.strip().replace("\n", " ") 
            abstract = entry.find("atom:summary", namespace).text.strip().replace("\n", " ") 

            # Make csv of authors
            authors = [
                author.find("atom:name", namespace).text
                for author in entry.findall("atom:author", namespace)
            ]
            author = ", ".join(authors)

            # Get primary category if present
            primary_category = entry.find("arxiv:primary_category", namespace)
            category = primary_category.get("term") if primary_category is not None else None
            print(category)

            # Extract ID
            arxiv_id_url = entry.find("atom:id", namespace).text
            arxiv_id = arxiv_id_url.split("/abs/")[-1]
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"    

            fetched_articles.append(
            {
                "id": arxiv_id,
                "title": title,
                "publication_date": pub_date,
                "abstract": abstract,
                "pdf_url": pdf_url,
                "category": category,
                "author": author
            }
        )
            fetched_ids.append(arxiv_id)
        return fetched_articles, fetched_ids

    def are_articles_updated(ids, self):
        return None

cont = Controller()
print(cont.get_articles())