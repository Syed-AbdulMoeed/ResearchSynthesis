from psycopg import connect 
from dotenv import load_dotenv
from pydantic import BaseModel
import os

class Paper(BaseModel):
    id: str
    title: str
    summary: str
    category: str
    authors: str
    pub_date: str
    pdf_url: str | None = None

load_dotenv()

def add_paper(paper: Paper):
    """Adds a paper to the `paper` database using `Paper` class"""
    with connect(os.getenv("CONNECTION")) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO papers (id, title, summary, category, authors, pub_date, pdf_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (paper.id, paper.title, paper.summary, paper.category, paper.authors, paper.pub_date, paper.pdf_url))
        return True


def get_papers_id() -> list[str]:
    with connect(os.getenv("CONNECTION")) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT id FROM papers
            """)

            # convert list of tuples to list of strs
            return [row[0] for row in cur.fetchall()]


#print(get_papers_id())