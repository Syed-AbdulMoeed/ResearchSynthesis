CREATE TABLE papers (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    category TEXT NOT NULL,
    authors TEXT NOT NULL,
    pub_date DATE NOT NULL,
    pdf_url TEXT 
)