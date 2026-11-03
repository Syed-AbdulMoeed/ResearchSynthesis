from langchain.chat_models import init_chat_model
from pydantic import BaseModel
from database import Paper, MOCK_PAPERS, PaperSummary, PaperSummaries, add_papers
from prompts import get_summary_prompt
from dotenv import load_dotenv
from normalize import normalize_and_save
from typing import Literal

load_dotenv()


class PaperProcessor:
    """Agent responsible for saving related papers and identifying trends"""
    def __init__(self, papers: list[Paper] = None):
        self.papers = papers # Init known papers
        self.model = "gemini-3.5-flash-lite" # Default model

        # Save papers
        add_papers(papers)


    def work(self):
        prompt = get_summary_prompt(self.papers)

        self.model = "google_genai:" + self.model
        
        llm = init_chat_model(model=self.model)
        structured_llm = llm.with_structured_output(PaperSummaries)
        proc_papers = structured_llm.invoke(prompt)
        sim_mappings, new_keywords, to_review, pending, incorrect_matching = normalize_and_save(proc_papers.summaries)
        return sim_mappings, new_keywords, to_review, pending, incorrect_matching



        


        
        


#print(get_summary_prompt(MOCK_PAPERS))
