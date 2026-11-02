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

def add_papers(papers: list[Paper]):
    """Adds a paper to the `paper` database using `Paper` class"""
    
    # Transform the list
    papers = [(paper.id, paper.title, paper.abstract, paper.category, paper.authors, paper.pub_date, paper.pdf_url)
              for paper in papers]
    
    with connect(CONNECTION) as conn:
        with conn.cursor() as cur:
            cur.executemany("""
            INSERT INTO papers (id, title, abstract, category, authors, pub_date, pdf_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, papers) 
            #(paper.id, paper.title, paper.abstract, paper.category, paper.authors, paper.pub_date, paper.pdf_url))
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

def add_techs(cur, new_keywords: list[dict]):
    """Save the brand-new technologies. Input: normalize()'s `new_keywords`
    (each dict: name, embedding, aliases, paper_id)."""
    tech_rows = [(t["name"], [float(x) for x in t["embedding"]], t["paper_id"])
                 for t in new_keywords]
    # ON CONFLICT DO NOTHING: a technology that already exists is skipped, not an error,
    cur.executemany("""
        INSERT INTO technologies (name, embedding, paper_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (name) DO NOTHING""", tech_rows)
 
    # Add it to alias table to where counting will be done 
    first_mention_rows = [(t["name"], t["name"], t["paper_id"]) for t in new_keywords]
    cur.executemany("""
        INSERT INTO aliases (name, alias, paper_id)
        VALUES (%s, %s, %s)
        ON CONFLICT ON CONSTRAINT aliases_unique DO NOTHING""", first_mention_rows)
 
 
def add_aliases(cur, sim_mappings: dict):
    """Save every (technology, spelling, paper) link. Input: normalize()'s `sim_mappings`,
    {(tech_name, paper_id): [spelling, spelling, ...]}."""
    rows = []
    for (tech_name, paper_id), spellings in sim_mappings.items():
        for spelling in spellings:
            rows.append((tech_name, spelling, paper_id))
    cur.executemany("""
        INSERT INTO aliases (name, alias, paper_id)
        VALUES (%s, %s, %s)
        ON CONFLICT ON CONSTRAINT aliases_unique DO NOTHING""", rows)
 
 
def add_decisions(cur, decisions: list[dict]):
    """Log the LLM's review decisions.
    Each dict: candidate, options (list), final_tech (str or None), paper_ids (list)."""
    rows = [(d["candidate"], d["options"], d["final_tech"], d["paper_ids"]) for d in decisions]
    cur.executemany("""
        INSERT INTO review_decisions (candidate, options, final_tech, paper_ids)
        VALUES (%s, %s, %s, %s)""", rows)
 
 
def add_unresolved(cur, unresolved: list[tuple]):
    """Park keywords the reviewer could not settle.
    Each item: (review_dict, reason) with the keys normalize() put in to_review."""
    rows = [(r["candidate"], list(r["may_match"]), r["paper_id"],
             [float(x) for x in r["embed"]], reason)
            for r, reason in unresolved]
    cur.executemany("""
        INSERT INTO unresolved_keywords (candidate, may_match, paper_id, embedding, reason)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (candidate, paper_id) DO NOTHING""", rows)
 
 
def save_normalizer_output(sim_mappings, new_keywords, unresolved, decisions):
    """Write one normalizer run to the database as a SINGLE transaction.
    `with connect(...)` commits when the block ends normally and ROLLS BACK if anything
    inside raises, so a failed save leaves the database exactly as it was.
    The ORDER matters: technologies first, because aliases (and review_decisions)
    have a foreign key pointing at technologies.name."""
    with connect(CONNECTION) as conn:
        with conn.cursor() as cur:
            add_techs(cur, new_keywords)
            add_aliases(cur, sim_mappings)
            add_decisions(cur, decisions)
            add_unresolved(cur, unresolved)
 
 
def get_known_techs() -> tuple[list[dict], list[list[float]]]:
    """Get technologies, embeddings, and lists of aliases."""
    with connect(CONNECTION) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT
                    t.name,
                    t.embedding,
                    COALESCE(
                        ARRAY_AGG(DISTINCT a.alias) FILTER (WHERE a.alias <> t.name),
                        ARRAY[]::TEXT[]
                    ) AS aliases
                FROM technologies AS t
                LEFT JOIN aliases AS a
                    ON a.name = t.name
                GROUP BY t.name
            """)
            raw = cur.fetchall()
            # built from the same `raw` list, so row i of the matrix is raw[i]'s embedding
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
