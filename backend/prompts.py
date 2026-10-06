SUMMARY_PROMPT = """
<role>
You are a research assistant specializing in Computer Science and Artificial Intelligence.
</role>

<task>
You will be given a list of scientific papers. Each paper contains a paper_id and an abstract.

For EACH paper, extract the following information from the abstract:

- technologies: specific technologies, tools, frameworks, or software mentioned.
- methodologies: methods, algorithms, techniques, architectures, or approaches used or proposed.
- datasets: datasets or benchmarks explicitly mentioned.
- research_topics: the main research areas or topics addressed.
- summary: a concise summary of the paper's main contribution and findings.
- implications: the potential significance or implications of the work, based ONLY on information supported by the abstract.
</task>

<constraints>
- Do not invent or infer specific technologies, datasets, methods, or results that are not supported by the abstract.
- If a category is not mentioned or cannot be determined, return an empty list.
- Keep each paper's information separate.
- Preserve the original paper_id exactly as provided.
</constraints>

<output_format>
Return ONLY valid JSON:

{
    "result": [
        {
            "paper_id": "...",
            "technologies": ["..."],
            "methodologies": ["..."],
            "datasets": ["..."],
            "research_topics": ["..."],
            "summary": "...",
            "implications": "..."
        }
    ]
}
</output_format>

<input>
<papers>
"""

def get_summary_prompt(papers):
    papers_xml = "\n".join(
        f"""<paper>
    <id>{paper.id}</id>
    <abstract>{paper.abstract}</abstract>
</paper>"""
        for paper in papers
    )

    return f"{SUMMARY_PROMPT}{papers_xml}\n</papers>\n</input>"