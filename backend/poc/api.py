from datetime import datetime
import io
import requests
from pypdf import PdfReader


def extract_pdf_text(pdf_url):
    """Downloads an Open Access PDF and extracts text from its pages."""
    try:
        # Set a short timeout so non-responsive PDF links don't hang the script
        response = requests.get(pdf_url, timeout=5)
        response.raise_for_status()

        # Parse PDF in memory
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
        # If PDF is paywalled, broken, or blocked by CORS/Cloudflare
        return None


def alex_test(limit=10):
    url = "https://api.openalex.org/works"
    today = datetime.now().strftime("%Y-%m-%d")

    params = {
        "search": "artificial intelligence",
        "sort": "publication_date:desc",
        "filter": f"type:article,to_publication_date:{today}",
        "per_page": limit,
    }

    headers = {"User-Agent": "mailto:your_email@example.com"}

    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()

    latest_articles = []

    for item in data.get("results", []):
        # Determine direct PDF URL if Open Access
        oa_info = item.get("open_access", {})
        primary_loc = item.get("primary_location") or {}
        pdf_url = primary_loc.get("pdf_url") or oa_info.get("oa_url")

        extracted_text = None
        has_text = "No"

        # Attempt extraction if a PDF link is marked accessible
        if oa_info.get("is_oa") and pdf_url:
            extracted_text = extract_pdf_text(pdf_url)
            if extracted_text:
                has_text = "Yes"

        latest_articles.append(
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "publication_date": item.get("publication_date"),
                "has_full_text": has_text,  # "Yes" or "No" indicator
                "pdf_url": pdf_url,
                "full_text": extracted_text,
            }
        )

    # Print summary output for POC demonstration
    for art in latest_articles:
        print(f"[{art['publication_date']}] {art['title']}")
        print(f"Full Text Extracted: {art['has_full_text']}")
        print(f"PDF Link: {art['pdf_url']}")

        if art["has_full_text"] == "Yes":
            # Print first 200 characters of extracted text as a preview
            preview = art["full_text"][:200].replace("\n", " ")
            print(f"Text Snippet: {preview}...\n")
        else:
            print("Text Snippet: [Paywalled / No direct PDF access]\n")
        print("-" * 60)

    return latest_articles


# Run the function
#alex_test(limit=5)
