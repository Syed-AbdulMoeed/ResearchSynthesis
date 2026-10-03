CREATE TABLE papers (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    abstract TEXT NOT NULL,
    category TEXT NOT NULL,
    authors TEXT NOT NULL,
    pub_date DATE NOT NULL,
    pdf_url TEXT 
)