CREATE TABLE review_decisions (
    id BIGSERIAL PRIMARY KEY,
    candidate TEXT NOT NULL,
    options TEXT[] NOT NULL,
    final_tech TEXT REFERENCES technologies(name),
    paper_ids TEXT[] NOT NULL,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE unresolved_keywords (
    id BIGSERIAL PRIMARY KEY,
    candidate TEXT NOT NULL,
    may_match TEXT[] NOT NULL,
    paper_id TEXT NOT NULL REFERENCES papers(id),
    embedding REAL[] NOT NULL,
    reason TEXT NOT NULL CHECK (reason IN ('no_answer', 'invalid_choice')),
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (candidate, paper_id)
);

