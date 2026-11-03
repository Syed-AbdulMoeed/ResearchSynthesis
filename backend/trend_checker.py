from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from typing import Literal
from pydantic import BaseModel
from prompts import get_trend_prompt


load_dotenv()

class Trend(BaseModel):
    technology: str                                  # must be a name from the data, exactly as given
    kind: Literal["rising", "emerging", "established"]
    confidence: Literal["low", "medium", "high"]
    evidence: str                                    # one sentence, with the numbers


class WeeklyTrendReport(BaseModel):
    summary: str
    no_clear_trends: bool
    trends: list[Trend]
    data_caveats: list[str]




class TrendChecker:
    def __init__(self):
        
        self.llm = init_chat_model("google_genai:gemini-3.5-flash-lite")
        self.llm = self.llm.with_structured_output(WeeklyTrendReport)
        self.llm = self.llm.with_retry(stop_after_attempt=2, wait_exponential_jitter=True)   # 2, not 3: quota

    def find_trends(self, weekly_report) -> WeeklyTrendReport:
        """One LLM call: weekly report in, structured WeeklyTrendReport out."""
        
        return self.llm.invoke(get_trend_prompt(weekly_report))
        