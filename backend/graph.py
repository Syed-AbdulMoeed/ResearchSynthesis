from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver          # [A] needed for interrupt() (swap for Postgres later)
from langgraph.types import interrupt, Command               # [B] interrupt = pause, Command = route / resume
from typing import TypedDict, Literal
from controller import Controller
from database import Paper
from paper_processor import PaperProcessor
from trend_checker import TrendChecker
from trend import get_week_report

class State(TypedDict):
    new_papers: list[Paper]
    found_new: bool = False
    report: str
    


def search_for_papers(state: State):
    return { "new_papers": Controller(limit=30).get_papers()}


def process_papers(state: State):
    agent = PaperProcessor(state["new_papers"])
    agent.work()
    return {"found_new": True}      # [C] was {"status": "found"}: "status" is not in State, so LangGraph silently dropped it


def route_on_papers(state: State):
    if state["new_papers"]:
        return "process"
    return "end"

def search_for_trend(state: State):
    checker = TrendChecker()

    return { "report" :checker.find_trends(get_week_report())}


# [D] The human step. It is its OWN node on purpose: when you resume, LangGraph re-runs the node
# that called interrupt() from its first line. If this node also called the LLM, the LLM would run
# again on every resume. Here the only thing before interrupt() is nothing, so re-running is free.
def review_report(state: State) -> Command[Literal["trend", "__end__"]]:
    answer = interrupt({"report": state["report"],
                        "question": "Continue, or repeat the trend step?"})
    if answer == "repeat":
        return Command(goto="trend")      # go back: only the trend node runs again, not search/process
    return Command(goto=END)              # "continue": go forward (later: the save-digest node)


graph = StateGraph(State)

graph.add_node("search", search_for_papers)
graph.add_node("process", process_papers)
graph.add_node("trend", search_for_trend)
graph.add_node("review", review_report)      # [E] replaces the unused duplicate "get_trend" node

graph.add_edge(START, "search")

graph.add_conditional_edges(
    "search",
    route_on_papers,
    {
        "process": "process",
        "end": "trend" #END
    }
)

graph.add_edge("process", "trend")
graph.add_edge("trend", "review")            # [F] was ("trend", END)

app = graph.compile(checkpointer=MemorySaver())   # [G] a checkpointer is required for interrupt()


def run():
    import uuid
    # [H] thread_id names this run. A paused run is stored under it, and resuming uses the same id.
    # Interactive: a fresh id each time. For the weekly job use one id per week (e.g. "week-2026-W45").
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    result = app.invoke({"new_papers": [], "found_new": False}, config)

    # [I] While the graph is paused, the result contains "__interrupt__". Show it, ask, resume.
    while "__interrupt__" in result:
        print(result["__interrupt__"][0].value["report"])
        choice = input("[c]ontinue or [r]epeat the trend step? ").strip().lower()
        result = app.invoke(Command(resume="repeat" if choice.startswith("r") else "continue"), config)

    return result


if __name__ == "__main__":
    print(run().get("report"))