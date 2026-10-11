SUMMARY_PROMPT = """
<role>
You are a research assistant specializing in Computer Science and Artificial Intelligence.
</role>

<task>
You will be given a list of scientific papers. Each paper contains a paper_id, abstract and category.

For EACH paper, extract the following information from the abstract:

- technologies: specific technologies, tools, frameworks, or software mentioned.
- summary: a concise summary of the paper's main contribution and findings.
- research_context: A list of categories describing the paper's primary research purpose or application area. Select one or more categories from the following:

theoretical: Develops theories, mathematical proofs, or conceptual frameworks, primarily advancing theoretical understanding.
methodological: Proposes or improves methods, algorithms, models, architectures, or techniques.
applied_industry: Applies research to practical problems in industry, business, manufacturing, or software engineering.
medical_healthcare: Addresses medical, clinical, healthcare, or biomedical problems.
scientific_research: Applies computational or technical methods to advance scientific fields such as physics, biology, chemistry, or astronomy.
social_humanities: Investigates social, behavioral, educational, linguistic, or humanities-related questions.
infrastructure_systems: Focuses on computing infrastructure, hardware, networks, cybersecurity, or system performance.

Assign multiple categories only when the abstract supports them. Classify the research based on its stated purpose, not merely the techniques it uses. If no category can be confidently assigned based on the abstract, return an empty list.
</task>

<constraints>
- Do not invent or infer specific technologies, datasets, methods, or results that are not supported by the abstract.
- If a category is not mentioned or cannot be determined, return an empty list.
- Keep each paper's information separate.
- Preserve the original paper_id and category exactly as provided.
</constraints>

<input>
<papers>
"""

def get_summary_prompt(papers):
    papers_xml = "\n".join(
        f"""<paper>
    <id>{paper.id}</id>
    <abstract>{paper.abstract}</abstract>
    <category>{paper.category}</category>
</paper>"""
        for paper in papers
    )

    return f"{SUMMARY_PROMPT}{papers_xml}\n</papers>\n</input>"