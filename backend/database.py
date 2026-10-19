from psycopg import connect 
from psycopg.rows import dict_row
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Literal
import os

class Paper(BaseModel):
    id: str
    title: str
    abstract: str
    category: str
    authors: str
    pub_date: str
    pdf_url: str | None = None


class PaperSummary(BaseModel):
    paper_id: str
    technologies: list[str]
    category: str
    summary: str
    research_context: list[Literal[
        "theoretical",
        "methodological",
        "applied_industry",
        "medical_healthcare",
        "scientific_research",
        "social_humanities",
        "infrastructure_systems",
        "other",
        "unclear"
    ]]


class PaperSummaries(BaseModel):
    summaries: list[PaperSummary]

load_dotenv()
CONNECTION = os.getenv("CONNECTION")

def add_paper(paper: Paper):
    """Adds a paper to the `paper` database using `Paper` class"""
    with connect(CONNECTION) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO papers (id, title, abstract, category, authors, pub_date, pdf_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (paper.id, paper.title, paper.abstract, paper.category, paper.authors, paper.pub_date, paper.pdf_url))
        return True


def get_papers_id() -> list[str]:
    with connect(CONNECTION) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT id FROM papers
            """)

            # convert list of tuples to list of strs
            return [row[0] for row in cur.fetchall()]


def get_latest_paper() -> set[str]:
    """Return the id of the papers with the latest date"""
    with connect(CONNECTION) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id
                FROM papers
                WHERE pub_date = (
                    SELECT pub_date
                    FROM papers
                    ORDER BY pub_date DESC
                    LIMIT 1
                );
""")
            return {row[0] for row in cur.fetchall()}


# I want to insert it in batch

def add_techs(names, embeds):
    """batch processes tech"""
    rows = list(zip(names, embeds)) 
    with connect(CONNECTION) as conn:
        with conn.cursor() as con:
            con.executemany("""
            INSERT INTO technologies (name, embedding)
            VALUES (%s, %s)""", rows)


def add_aliases(names_aliases: dict[str:list]):
    """add aliases in batch"""

    # transform dict with str:list
    rows = []
    for key, vals in names_aliases.items():
        for val in vals: rows.append((key,val))
    with connect(CONNECTION) as conn:
        with conn.cursor() as con:
            con.executemany("""
            INSERT INTO aliases (name, alias)
            VALUES (%s, %s)""", (rows))


def get_known_techs() -> tuple[list[dict], list[list[float]]]:
    """Get technologies, embeddings, and lists of aliases."""
    with connect(CONNECTION) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT
                    t.name,
                    t.embedding,
                    COALESCE(
                        ARRAY_AGG(a.name) FILTER (WHERE a.name IS NOT NULL),
                        ARRAY[]::TEXT[]
                    ) AS aliases
                FROM technologies AS t
                LEFT JOIN aliases AS a
                    ON a.name = t.name
                GROUP BY t.name, t.embedding
            """)

            raw = cur.fetchall()
            emb_matrix = [row["embedding"] for row in raw]

            return raw, emb_matrix
            

MOCK_PAPERS = [
    Paper(
        id="1706.03762",
        title="Attention Is All You Need",
        abstract="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks in an encoder-decoder configuration. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train.",
        category="cs.CL",
        authors="Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz Kaiser, Illia Polosukhin",
        pub_date="2017-06-12"
    ),

    Paper(
        id="1810.04805",
        title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        abstract="We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context in all layers. As a result, the pre-trained BERT model can be fine-tuned with just one additional output layer to create state-of-the-art models for a wide range of tasks.",
        category="cs.CL",
        authors="Jacob Devlin, Ming-Wei Chang, Kenton Lee, Kristina Toutanova",
        pub_date="2018-10-11"
    ),

    Paper(
        id="2005.14165",
        title="Language Models are Few-Shot Learners",
        abstract="Recent work has demonstrated substantial gains on many NLP tasks and benchmarks by pre-training on a large corpus of text followed by fine-tuning on a specific task. Here we show that scaling up language models greatly improves task-agnostic, few-shot performance, sometimes even reaching competitiveness with prior state-of-the-art fine-tuning approaches. Specifically, we train GPT-3, an autoregressive language model with 175 billion parameters, and test its performance in the few-shot setting.",
        category="cs.CL",
        authors="Tom B. Brown, Benjamin Mann, Nick Ryder, Melanie Subbiah, Prafulla Dhariwal, Arvind Neelakantan, Pranav Shyam, Girish Sastry, Amanda Askell, Sandhini Agarwal, Ariel Herbert-Voss, Gretchen Krueger, Tom Henighan, Rewon Child, Aditya Ramesh, Daniel Ziegler, Jeffrey Wu, Clemens Winter, Christopher Hesse, Mark Chen, Eric Sigler, Scott Gray, Benjamin Chess, Jack Clark, Christopher Berner, Sam McCandlish, Alec Radford, Ilya Sutskever, Dario Amodei",
        pub_date="2020-05-28"
    )
]

def test():
    techs, b = get_known_techs()
    for tech in techs:
        print(tech['aliases'], tech['name'])
#print(get_papers_id())
#print(get_known_techs())
