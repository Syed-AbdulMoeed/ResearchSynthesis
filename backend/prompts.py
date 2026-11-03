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

REVIEW_PROMPT = """
<task>
You will receive a list of reviews extracted from scientific papers related to AI and Computer Science.

Each review contains:

A keyword extracted from a paper.
Two candidate technology names.
A summary of the paper.
Determine whether the keyword refers to the same underlying technology as either candidate, using your knowledge and the paper summary as context.

Rules:

Return 1 or 2 to chose option 1 or 2 if applicable.
If neither candidate matches, return null.
Do not select a candidate merely because it is related to the keyword.
Treat distinct technologies, implementations, architectures, and frameworks as different unless they genuinely refer to the same technology.

<reviews>
"""

def get_review_prompt(reviews):
    review_part = ""
    for review in reviews:    
        two = f"<may_match_2> 2: {review[1]["may_match"][1]}</may_match_2>\n" if len(review[1]["may_match"]) > 1 else ""
        one = f"""<review>
    <review_id>{review[0]}</review_id>
    <keyword>{review[1]["candidate"]}</keyword>
    <may_match_1> 1: {review[1]["may_match"][0]}</may_match_1>"""+"\n"
    
        three = f"""<summary>{review[1]["p_summary"]}</summary>
            <paper_id>{review[1]["paper_id"]}</paper_id>
        </review>\n"""
        review_part += one + two + three 
        
    
    return f"{REVIEW_PROMPT}\n{review_part}\n</reviews>"


import json
from typing import Literal
from pydantic import BaseModel

# Same family as the review step. Check the current free-tier limits: this is ONE call per week,
# so a bigger model is affordable. Change it here if the name is wrong or you want Flash instead.
TREND_MODEL = "google_genai:gemini-3.5-flash-lite"


TREND_PROMPT = """
You are the analyst for a weekly research-trend tracker. You are given ONE week of data about
scientific papers (arXiv). A "trend" here means a named technology or method that is mentioned
in several papers. Counts were computed by code and are exact: do not recompute or doubt them.
Your job is to interpret them and write the weekly report.

HOW TO READ THE DATA (JSON):
- week_start / week_end: the week covered. Weeks are by the paper's publication date.
- meta.papers_this_week: how many papers the week has (the denominator for every share).
- meta.categories: papers per arXiv category this week.
- meta.weeks_of_data: how many weeks of data the system has in total, this week included.
- meta.unresolved_keywords: mentions the system could not match to a technology. Counts may be
  slightly too low by about this many.
- counts: totals for the whole week, including items cut from the lists below.
- repeated: technologies mentioned in 2 or more papers this week, biggest first. Fields:
  - papers_this_week, share_of_week_papers: this week's size.
  - prev_weeks: papers per week for the previous weeks, OLDEST FIRST (last entry = last week).
  - total_papers_to_date: all papers mentioning it so far, this week included.
  - weeks_since_first_seen: 0 means it first appeared this week.
  - is_new_this_week: true if the technology was first seen this week.
  - aliases_this_week: the spellings used and how many papers used each.
  - categories_this_week, first_mention, example_titles: context and evidence.
- new_single_mention: names of technologies first seen this week in only ONE paper. A single
  mention is not a trend. It only shows what appeared.

RULES:
1. Use only the data given. Do not use outside knowledge to claim a technology is "popular" or
   "rising". Outside knowledge may only be used to explain what a technology is, briefly.
2. Always quote the numbers you rely on (for example "7 papers this week, 2 last week").
3. If meta.weeks_of_data is below 3, or a technology's prev_weeks are mostly zeros because the
   system has not been running long, you cannot call it "rising". Say it is new or too early to
   tell, and lower the confidence.
4. "rising" needs a clear jump over its own prev_weeks, not just a big count. A technology that is
   big every week is "established".
5. "emerging" is for technologies first seen recently that already appear in several papers.
6. If nothing qualifies, set no_clear_trends to true and leave trends empty. That is a good
   answer. Do not invent trends to fill the report.
7. Mention anything that weakens the numbers in data_caveats (few weeks of data, a partial
   week, unresolved keywords, a very small week, lists cut by a cap).
8. Keep it short. At most 8 trends. One sentence of evidence each.

OUTPUT: fill the requested structure. "summary" is a 3 to 5 sentence plain-language digest of the
week: what the week looked like (size, main categories), the main trends if any, and the biggest
caveat.

Here is the info you have:
"""

def get_trend_prompt(weekly_report):
    """`weekly_report` is trends.report_to_json(...) (a string) or the dict from get_week_report()."""
    if not isinstance(weekly_report, str):
        weekly_report = json.dumps(weekly_report, separators=(",", ":"), ensure_ascii=False)
    return TREND_PROMPT + weekly_report


    

