CREATE TABLE aliases(
    name TEXT REFERENCES technologies(name),
    alias TEXT NOT NULL,
    paper_id TEXT REFERENCES papers(id) NOT NULL,
    CONSTRAINT aliases_unique UNIQUE (name, alias, paper_id)
)