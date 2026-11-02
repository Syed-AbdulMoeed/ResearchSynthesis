from langchain.chat_models import init_chat_model
from pydantic import BaseModel
from database import Paper, MOCK_PAPERS, PaperSummary, PaperSummaries
from prompts import get_summary_prompt
from dotenv import load_dotenv
from normalize import normalize
from typing import Literal
from normalize import normalize

load_dotenv()


class Agent:
    """Agent responsible for saving related papers and identifying trends"""
    def __init__(self, papers: list[Paper] = None):
        self.papers = papers # Init known papers
        '''with open("models.json", 'r') as file:
            self.models = json.load(file)'''
            

        self.model = "gemini-3.5-flash-lite" # Default model
    

    def work(self):
        prompt = get_summary_prompt(self.papers)

        self.model = "google_genai:" + self.model
        
        llm = init_chat_model(model=self.model)
        structured_llm = llm.with_structured_output(PaperSummaries)
        proc_papers = structured_llm.invoke(prompt)
        sim_mappings, new_keywords, to_review, pending, incorrect_matching = normalize(proc_papers.summaries)
        
        print("sim_mappings")
        print("total:", len(sim_mappings))
        print(sim_mappings)

        print("new")
        print("total:", len(new_keywords))
        print( [(n['name'], n['aliases']) for n in new_keywords])

        #print("Review")
        #print("total:", len(to_review))
        #print(to_review)
        
        print("pending")
        print("total:", len(pending))
        #print(pending)

        print("incorr_matching")
        print("total:", len(incorrect_matching))
        #print(to_review)


        


        
        


#print(get_summary_prompt(MOCK_PAPERS))
