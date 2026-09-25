from datetime import datetime
import io
import xml.etree.ElementTree as ET
import requests
from pypdf import PdfReader


def extract_pdf_text(pdf_url):
    """Downloads an open-access arXiv PDF and extracts its text contents."""
    try:
        # Set user-agent header as requested by arXiv API terms of use
        headers = {"User-Agent": "ArXiv-POC-Script/1.0 (mailto:your_email@example.com)"}
        response = requests.get(pdf_url, headers=headers, timeout=10)
        response.raise_for_status()

        # Load PDF directly in memory
        pdf_file = io.BytesIO(response.content)
        reader = PdfReader(pdf_file)

        extracted_pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_pages.append(text)

        full_text = "\n".join(extracted_pages)
        return full_text if full_text.strip() else None

    except Exception:
        return None


def arxiv_test(limit=5):
    # Search arXiv for Artificial Intelligence (cat:cs.AI or title/abstract match)
    url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": "cat:cs.AI OR ti:\"artificial intelligence\"",
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": limit,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    # arXiv returns Atom XML format
    root = ET.fromstring(response.content)
    namespace = {"atom": "http://www.w3.org/2005/Atom"}

    latest_articles = []

    for entry in root.findall("atom:entry", namespace):
        title = entry.find("atom:title", namespace).text.strip().replace("\n", " ")
        published = entry.find("atom:published", namespace).text[:10]
        abstract = entry.find("atom:summary", namespace).text.strip().replace("\n", " ")
        arxiv_id_url = entry.find("atom:id", namespace).text

        # Extract ID (e.g., 'http://arxiv.org/abs/2401.12345v1' -> '2401.12345v1')
        arxiv_id = arxiv_id_url.split("/abs/")[-1]

        # arXiv PDFs follow a deterministic URL structure
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        # Attempt PDF extraction
        extracted_text = extract_pdf_text(pdf_url)
        has_text = "Yes" if extracted_text else "No"

        latest_articles.append(
            {
                "id": arxiv_id,
                "title": title,
                "publication_date": published,
                "abstract": abstract,
                "pdf_url": pdf_url,
                "has_full_text": has_text,
                "full_text": extracted_text,
            }
        )

    # Print summary output for POC demonstration
    for art in latest_articles:
        print(f"[{art['publication_date']}] {art['title']}")
        print(f"arXiv ID: {art['id']}")
        print(f"Full Text Extracted: {art['has_full_text']}")
        print(f"PDF URL: {art['pdf_url']}")
        print(f"Abstract:  {art['abstract']}")

        if art["has_full_text"] == "Yes":
            # Show a 200 character preview of the full paper text
            preview = art["full_text"][:200].replace("\n", " ")
            print(f"Text Snippet: {preview}...\n")
        else:
            print("Text Snippet: [Extraction Failed]\n")
        print("-" * 60)

    return latest_articles


# Run the POC
if __name__ == "__main__":
    arxiv_test(limit=3)