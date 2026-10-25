CREATE TABLE technologies(
    name TEXT PRIMARY KEY,
    embedding REAL[] NOT NULL,
    paper_id TEXT REFERENCES papers(id) NOT NULL 
)